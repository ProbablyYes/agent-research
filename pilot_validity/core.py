"""Audited replay and frozen baseline evaluation. No LLM/GPU operations."""
import contextlib
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / 'calibration-is-not-control'
sys.path[:0] = [str(UPSTREAM / 'src'), str(UPSTREAM / 'scripts')]
import numpy as np
import collect_alfworld_branches as original
import oversight_branching.policy_learning as policy

UPSTREAM_COMMIT = '9e3825b7eea89ee9dc88f1ccd11f277f8e10beb3'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def dump(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)


def nodes(env):
    """Read explicitly known wrapper fields; never use forwarding getattr."""
    seen, queue = set(), [env]
    while queue:
        node = queue.pop(0)
        if id(node) in seen:
            continue
        seen.add(id(node))
        yield node
        attrs = vars(node)
        for key in ('batch_env', '_wrapped_env'):
            if attrs.get(key) is not None:
                queue.append(attrs[key])
        queue.extend(attrs.get('envs', []))


def snapshot(env, output, steps, budget, reset=False):
    if reset:
        obs, commands, won, _ = original.unwrap_reset(output)
        done = False  # Gym reset has no done output; checked against backend won/lost below.
    else:
        obs, _, done, won, commands, _ = original.unwrap_step(output)
    hidden, stack = {}, []
    for node in nodes(env):
        attrs = vars(node)
        stack.append(type(node).__module__ + '.' + type(node).__name__)
        if type(node).__name__ == 'Limit':
            hidden['limit_steps'] = attrs['nb_steps']
            hidden['limit_max_steps'] = attrs['max_episode_steps']
        if type(node).__name__ == 'PddlEnv':
            state = attrs['state']
            hidden['facts'] = sorted(str(f) for f in attrs['_pddl_state'].facts)
            hidden['moves'] = attrs['_moves']
            hidden['backend_won'] = bool(state.get('won', False))
            hidden['backend_lost'] = bool(state.get('lost', False))
            hidden['last_command'] = state.get('last_command')
            hidden['entity_names'] = {k: v.name for k, v in sorted(attrs['_entity_infos'].items())}
    required = ['facts', 'moves', 'limit_steps', 'limit_max_steps', 'backend_won', 'backend_lost']
    missing = [k for k in required if k not in hidden]
    return {'observation': obs, 'admissible_commands': list(commands), 'done': bool(done),
            'won': bool(won), 'executed_actions': steps, 'remaining_budget': budget - steps,
            'accessible_state': hidden, 'missing_required_fields': missing, 'wrapper_stack': stack}


def differences(expected, actual, path=''):
    result = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            loc = f'{path}.{key}' if path else key
            if key not in expected or key not in actual:
                result.append({'field': loc, 'expected': expected.get(key), 'actual': actual.get(key), 'missing': True})
            else:
                result.extend(differences(expected[key], actual[key], loc))
    elif expected != actual:
        result.append({'field': path, 'expected': expected, 'actual': actual})
    return result


def validate_replay(reference, replay, prefix):
    k = prefix.step_index
    diffs = []
    if len(prefix.history_actions) != k or len(prefix.history_observations) != k:
        diffs.append({'field': 'prefix_history_lengths', 'expected': k,
                      'actual': [len(prefix.history_actions), len(prefix.history_observations)]})
    if len(replay) != k + 1 or len(reference) < k + 1:
        diffs.append({'field': 'replay_state_count', 'expected': k + 1, 'actual': len(replay)})
    for index, (ref, got) in enumerate(zip(reference[:k + 1], replay)):
        diffs.extend(differences(ref, got, f'state[{index}]'))
        for label, state in [('reference', ref), ('replay', got)]:
            hidden = state['accessible_state']
            if state['missing_required_fields']:
                diffs.append({'field': f'{label}[{index}].missing_required_fields', 'actual': state['missing_required_fields']})
            if hidden.get('limit_steps') != state['executed_actions']:
                diffs.append({'field': f'{label}[{index}].counter_inconsistent', 'actual': state})
            if hidden.get('limit_max_steps') != state['executed_actions'] + state['remaining_budget']:
                diffs.append({'field': f'{label}[{index}].budget_inconsistent', 'actual': state})
            if hidden.get('backend_won') != state['won']:
                diffs.append({'field': f'{label}[{index}].won_inconsistent', 'actual': state})
            expected_done = bool(hidden.get('backend_won') or hidden.get('backend_lost') or state['remaining_budget'] <= 0)
            if state['done'] != expected_done:
                diffs.append({'field': f'{label}[{index}].done_inconsistent', 'actual': state})
    if reference and k < len(reference):
        ref = reference[k]
        diffs.extend(differences(ref['observation'], prefix.observation, 'prefix.observation'))
        diffs.extend(differences(ref['admissible_commands'], prefix.admissible_commands, 'prefix.admissible_commands'))
        for i in range(min(k, len(prefix.history_observations))):
            diffs.extend(differences(reference[i + 1]['observation'], prefix.history_observations[i], f'prefix.history_observations[{i}]'))
    return {'passed': not diffs, 'checkpoint': k, 'differences': diffs,
            'reference_states': copy.deepcopy(reference[:k + 1]), 'replay_states': copy.deepcopy(replay),
            'scope': 'observable outputs + accessible PDDL facts/counters; not a complete native-state proof'}


class Recorder:
    def __init__(self, env, gamefile, budget, role, sink):
        self.env, self.gamefile, self.budget, self.role, self.sink = env, gamefile, budget, role, sink
        self.states, self.actions, self.rewards = [], [], []

    def reset(self):
        output = self.env.reset()
        self.states = [snapshot(self.env, output, 0, self.budget, reset=True)]
        self.sink({'kind': 'reset', 'role': self.role, 'gamefile': self.gamefile, 'state': self.states[-1]})
        return output

    def step(self, commands):
        before = self.states[-1]
        if before['done'] or before['remaining_budget'] <= 0:
            raise RuntimeError('Attempt to step terminated/budget-exhausted environment')
        output = self.env.step(commands)
        self.actions.append(commands[0])
        self.rewards.append(float(output[1][0]))
        self.states.append(snapshot(self.env, output, len(self.actions), self.budget))
        self.sink({'kind': 'step', 'role': self.role, 'gamefile': self.gamefile,
                   'action': commands[0], 'reward': self.rewards[-1], 'state': self.states[-1]})
        return output

    def close(self):
        self.env.close()


class AuditSession:
    """Process-local, temporary instrumentation of unmodified upstream functions."""
    def __init__(self, sink=lambda event: None):
        self.sink = sink
        self.phase = 'base'
        self.envs, self.reference, self.audits, self.branches = [], {}, {}, {}
        self.pair_id = None

    @contextlib.contextmanager
    def install(self):
        factory, replay = original.make_single_game_env, original.replay_to_prefix
        def wrapped_factory(gamefile, max_episode_steps=30, include_policy_commands=False):
            role = 'base' if self.phase == 'base' else ('verify' if include_policy_commands else 'continue')
            wrapped = Recorder(factory(gamefile, max_episode_steps, include_policy_commands), gamefile,
                               max_episode_steps, role, self.sink)
            self.envs.append(wrapped)
            if role == 'base':
                self.reference[gamefile] = wrapped
            return wrapped
        def wrapped_replay(prefix, max_episode_steps, include_policy_commands=False):
            result = replay(prefix, max_episode_steps, include_policy_commands)
            env = result[0]
            role = 'verify' if include_policy_commands else 'continue'
            audit = validate_replay(self.reference[prefix.gamefile].states, env.states, prefix)
            expected_actions = self.reference[prefix.gamefile].actions[:prefix.step_index]
            audit['differences'].extend(differences(expected_actions, env.actions, 'replayed_actions'))
            audit['differences'].extend(differences(expected_actions, prefix.history_actions, 'prefix.history_actions'))
            audit['passed'] = not audit['differences']
            key = (self.pair_id, role)
            if key in self.audits:
                raise RuntimeError('Duplicate branch: no automatic replacement allowed')
            self.audits[key], self.branches[key] = audit, env
            self.sink({'kind': 'pre_action_replay_audit', 'pair_id': self.pair_id, 'role': role, **audit})
            # Keep author's raw branch behavior even when audit fails. Eligibility is separate.
            return result
        original.make_single_game_env, original.replay_to_prefix = wrapped_factory, wrapped_replay
        try:
            yield self
        finally:
            original.make_single_game_env, original.replay_to_prefix = factory, replay
            for env in self.envs:
                env.close()

    def paired_record(self, row, config):
        k, reasons, recomputed = row['step_index'], [], {}
        branches = {}
        for role in ('continue', 'verify'):
            key = (self.pair_id, role)
            if key not in self.audits:
                reasons.append({'field': role, 'reason': 'missing branch audit'})
                continue
            audit, env = self.audits[key], self.branches[key]
            if not audit['passed']:
                reasons.append({'field': role, 'reason': 'replay_mismatch', 'differences': audit['differences']})
            suffix = env.actions[k:]
            won = env.states[-1]['won']
            steps = len(suffix)
            cost = config['step_cost'] * steps + (config['verify_cost'] if role == 'verify' else 0)
            utility = (1.0 if won else -config['wrong_penalty']) - cost
            recomputed[role] = {'won': won, 'suffix_steps': steps, 'observed_step_cost': steps * config['step_cost'],
                                'intervention_cost': config['verify_cost'] if role == 'verify' else 0.,
                                'realized_utility': utility,
                                'terminal_done': env.states[-1]['done'],
                                'termination_reason': 'won' if won else 'budget_exhausted' if env.states[-1]['remaining_budget'] <= 0 else 'stopped_without_success'}
            for field, value in [(f'{role}_correct', won), (f'{role}_branch_steps', steps), (f'u_{role}', utility)]:
                if isinstance(value, bool):
                    equal = row[field] == value
                else:
                    equal = math.isclose(float(row[field]), value, abs_tol=1e-12)
                if not equal:
                    reasons.append({'field': field, 'stored': row[field], 'recomputed': value})
            branches[role] = {'audit': audit, 'states': copy.deepcopy(env.states), 'actions': list(env.actions),
                              'suffix_actions': suffix, 'rewards': list(env.rewards)}
        if row['u_quit'] != 0:
            reasons.append({'field': 'u_quit', 'stored': row['u_quit'], 'recomputed': 0.})
        return {'pair_id': self.pair_id, 'row': copy.deepcopy(row), 'valid_pair': not reasons,
                'invalid_reasons': reasons, 'recomputed': recomputed, 'branches': branches,
                'llm_cost_in_utility': False, 'predicted_cost': None,
                'observed_prefix_steps': k, 'observed_prefix_sunk_cost': k * config['step_cost']}


def route(scores, verify_threshold, quit_threshold):
    return ['quit' if s >= quit_threshold else 'verify' if s >= verify_threshold else 'continue' for s in scores]


def corrected_thresholds(rows, scores):
    """All empirical validation boundaries, including both extremes. Fixed order C/I/Q."""
    scores = np.asarray(scores, dtype=float)
    if len(rows) != len(scores) or not len(rows) or not np.isfinite(scores).all():
        raise ValueError('Nonempty, finite, aligned validation rows/scores required')
    # Probability scores in [0,1]; -1/2 encode -infinity/+infinity without JSON infinities.
    if np.any((scores < 0) | (scores > 1)):
        raise ValueError('Risk probabilities outside [0,1]')
    boundaries = sorted(set([-1., 2., *scores.tolist()]))
    best = None
    for tv in boundaries:
        for tq in boundaries:
            if tq < tv:
                continue
            metrics = independent_metrics(rows, route(scores, tv, tq))
            candidate = {'verify_threshold': tv, 'quit_threshold': tq, **metrics}
            if best is None or candidate['utility'] > best['utility']:
                best = candidate
    return best


def independent_metrics(rows, actions):
    if len(rows) != len(actions) or any(a not in ('continue', 'verify', 'quit') for a in actions):
        raise ValueError('Action count or action name mismatch')
    if not rows:
        return {'n': 0, 'utility': None, 'success_rate': None, 'control_regret': None,
                'verify_rate': None, 'quit_rate': None}
    values = [r['u_' + a] for r, a in zip(rows, actions)]
    if not all(math.isfinite(v) for r in rows for v in (r['u_continue'], r['u_verify'], r['u_quit'])):
        raise ValueError('Nonfinite utility')
    return {'n': len(rows), 'utility': sum(values) / len(rows),
            'success_rate': sum(a != 'quit' and r[a + '_correct'] for r, a in zip(rows, actions)) / len(rows),
            'control_regret': sum(max(r['u_continue'], r['u_verify'], r['u_quit']) - v for r, v in zip(rows, values)) / len(rows),
            'verify_rate': actions.count('verify') / len(rows), 'quit_rate': actions.count('quit') / len(rows)}


def valid_rows(records):
    return [r['row'] for r in records if r['valid_pair']]


def freeze_baselines(train_records, val_records):
    """Deliberately no test argument. Both originals and corrected use same valid subsets."""
    train, val = valid_rows(train_records), valid_rows(val_records)
    if not train or not val:
        raise ValueError('No valid training/validation pairs: freeze blocked, no replacement')
    model = policy.fit_failure_baseline(train)
    scores = model.predict_proba(policy.feature_matrix(val))[:, 1]
    original_controls = policy.threshold_search_failure_scores(scores, val)
    corrected_controls = corrected_thresholds(val, scores)
    controls = {'original': original_controls, 'corrected': corrected_controls,
                'selection_split': 'val', 'train_ids': [r['example_id'] for r in train],
                'val_ids': [r['example_id'] for r in val]}
    return model, controls


def evaluate_frozen(model, controls, records):
    rows = valid_rows(records)
    counts = {'attempted': len(records), 'valid': len(rows), 'invalid': len(records) - len(rows),
              'coverage': len(rows) / len(records) if records else None,
              'invalid_ids': [r['pair_id'] for r in records if not r['valid_pair']]}
    policies = {}
    scores = model.predict_proba(policy.feature_matrix(rows))[:, 1] if rows else []
    for name in ('original', 'corrected'):
        c = controls[name]
        actions = route(scores, c['verify_threshold'], c['quit_threshold'])
        policies[name] = {'actions': actions, 'metrics': independent_metrics(rows, actions)}
    for action in ('continue', 'verify', 'quit'):
        actions = [action] * len(rows)
        policies['always_' + action] = {'actions': actions, 'metrics': independent_metrics(rows, actions)}
    return {'denominators': counts, 'policies': policies, 'test_selected_policy': None,
            'scope': 'valid pairs only; not an unbiased full-task estimate when coverage < 1'}
