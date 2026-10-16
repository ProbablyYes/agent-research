"""Freeze a six-task plan, or execute it with instrumentation (HTTP is opt-in)."""
import argparse
import importlib.metadata
import importlib.util
import inspect
import json
import os
import cloudpickle
import random
import subprocess
import sys
import traceback
from pathlib import Path

from .core import (ROOT, UPSTREAM, UPSTREAM_COMMIT, AuditSession, original, policy,
                   sha, digest, dump, freeze_baselines, evaluate_frozen, valid_rows,
                   independent_metrics)
from oversight_branching import alfworld_text as textenv
from oversight_branching.local_llm import GenerationOutput, LocalChatModel

CONFIG = dict(seed=13, train_games=2, val_games=2, test_games=2, prefixes_per_game=1,
              max_episode_steps=20, action_max_tokens=24, confidence_max_tokens=8,
              verify_max_tokens=24, batch_size=1, verify_cost=.05, wrong_penalty=1., step_cost=.01,
              intervention_mode='expert_defer', verify_mode='no_preview', repair_horizon=3,
              expert_max_policy_steps=-1, expert_noise_rate=0.)
MODEL = dict(name='Qwen/Qwen2.5-7B-Instruct', revision='a09a35458c702b33eeacc393d103063234e8bc28',
             tokenizer_revision='a09a35458c702b33eeacc393d103063234e8bc28',
             api_base='http://127.0.0.1:18080', interface='chat_completions', temperature=0.,
             api_timeout=60., request_seed=None, server_seed=13, dtype='half', max_model_len=8192,
             vllm='0.6.6', transformers='4.46.3', gpu_memory_utilization=.60, max_num_seqs=1,
             enforce_eager=True, runtime_verified=False)


def check_upstream():
    commit = subprocess.check_output(['git', '-C', str(UPSTREAM), 'rev-parse', 'HEAD'], text=True).strip()
    status = subprocess.check_output(['git', '-C', str(UPSTREAM), 'status', '--porcelain'], text=True)
    if commit != UPSTREAM_COMMIT or status:
        raise RuntimeError('Upstream commit/worktree does not match the audited original')


def fingerprints():
    paths = list((UPSTREAM / 'src').rglob('*.py')) + list((UPSTREAM / 'scripts').glob('*.py'))
    paths += [UPSTREAM / 'requirements.txt'] + list((ROOT / 'pilot_validity').glob('*.py'))
    # Capture the version-specific internal state access implementation too.
    for mod in ['textworld.envs.pddl.pddl', 'textworld.envs.wrappers.limit',
                'textworld.envs.batch.batch_env', 'textworld.gym.envs.textworld_batch']:
        paths.append(Path(importlib.import_module(mod).__file__))
    return {str(p): sha(p) for p in sorted(paths)}


def prepare(output, synthetic=False):
    check_upstream()
    output.mkdir(parents=True, exist_ok=False)
    old = json.loads((ROOT / 'experiments/cinc_smoke_20261016/task_manifest.json').read_text())
    tasks = []
    for split, source in [('train', 'train'), ('val', 'valid_seen'), ('test', 'valid_unseen')]:
        for game in old[source][:2]:
            path = Path(game)
            files = {str(p): sha(p) for p in sorted(path.parent.iterdir()) if p.is_file()}
            tasks.append(dict(split=split, gamefile=game, task_id=path.parent.name,
                              task_type=textenv.load_task_type(game), file_sha256=files, checkpoint_index=0))
    assert len(tasks) == 6 and len({t['task_id'] for t in tasks}) == 6
    config = dict(CONFIG)
    if synthetic:
        config['max_episode_steps'] = 3
    versions = {k: importlib.metadata.version(k) for k in ['numpy', 'scikit-learn', 'alfworld', 'textworld', 'requests', 'cloudpickle']}
    prompts = {name: inspect.getsource(getattr(textenv, name)) for name in dir(textenv) if name.startswith('build_')}
    plan = {'schema': 1, 'label': 'SYNTHETIC_POLICY_REAL_ENV' if synthetic else 'REAL_MODEL_NOT_YET_RUN',
            'upstream_commit': UPSTREAM_COMMIT, 'research_parent_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'tasks': tasks, 'config': config, 'model': MODEL, 'package_versions': versions,
            'source_sha256': fingerprints(), 'prompt_templates': prompts,
            'environment': {'PYTHONHASHSEED': '13', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'},
            'environment_seed': 1234, 'environment_seed_scope': 'upstream TextworldBatchGymEnv default single-game shuffle; native planner RNG state is not exported',
            'task_selection': 'first two of each split in the previously saved seed13/14/15 manifest; no fresh os.walk/shuffle',
            'interpretation': 'six initial checkpoints only, engineering pilot; not mid-episode timing research',
            'native_state_equivalence_proven': False}
    dump(output / 'plan.json', plan)
    dump(output / 'plan.sha256.json', {'sha256': sha(output / 'plan.json')})
    print(json.dumps({'plan': str(output / 'plan.json'), 'sha256': sha(output / 'plan.json'), 'tasks': len(tasks)}))


def validate_plan(path):
    plan = json.loads(path.read_text())
    if sha(path) != json.loads(path.with_name('plan.sha256.json').read_text())['sha256']:
        raise ValueError('Plan checksum mismatch')
    check_upstream()
    for p, expected in plan['source_sha256'].items():
        if sha(p) != expected:
            raise ValueError('Source changed after freeze: ' + p)
    for task in plan['tasks']:
        for p, expected in task['file_sha256'].items():
            if sha(p) != expected:
                raise ValueError('Task changed after freeze: ' + p)
    for package, version in plan['package_versions'].items():
        if importlib.metadata.version(package) != version:
            raise ValueError('Dependency changed: ' + package)
    for key, value in plan['environment'].items():
        if os.environ.get(key) != value:
            raise ValueError(f'Run with {key}={value}')
    return plan


class SyntheticModel:
    def generate_batch(self, prompts, **kwargs):
        return [GenerationOutput(p, 'CONFIDENCE: 50' if 'CONFIDENCE:' in p else 'ACTION: look') for p in prompts]


class LoggedModel:
    def __init__(self, model, sink):
        self.model, self.sink = model, sink

    def generate_batch(self, prompts, **kwargs):
        self.sink({'kind': 'generation_request', 'prompts': prompts, 'kwargs': kwargs})
        outputs = self.model.generate_batch(prompts, **kwargs)
        self.sink({'kind': 'generation_response', 'texts': [o.text for o in outputs]})
        return outputs


def real_model(plan, attestation, sink):
    """No implicit downloads; only an explicitly prepared local service is allowed."""
    if importlib.util.find_spec('transformers') is not None:
        raise RuntimeError('Client environment changed: tokenizer path would alter original request format')
    if os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('Unset OPENAI_API_KEY for this local-only pilot')
    if not attestation:
        raise RuntimeError('Real model blocked until service provenance is recorded')
    proof = json.loads(attestation.read_text())
    for key in ['name', 'revision', 'tokenizer_revision', 'server_seed', 'vllm', 'transformers', 'dtype',
                'max_model_len', 'gpu_memory_utilization', 'max_num_seqs', 'enforce_eager']:
        if proof.get(key) != plan['model'][key]:
            raise ValueError('Service attestation mismatch: ' + key)
    # Require retained local startup evidence and a full model-file digest inventory.
    for field in ['startup_log', 'server_freeze']:
        entry = proof[field]
        if sha(entry['path']) != entry['sha256']:
            raise ValueError('Missing/changed service evidence: ' + field)
    weights = proof['model_files']
    if not weights or not any(p.endswith('.safetensors') for p in weights):
        raise ValueError('No weight file fingerprints in service attestation')
    for p, expected in weights.items():
        if sha(p) != expected:
            raise ValueError('Model file mismatch: ' + p)
    sink({'kind': 'service_attestation', 'attestation': proof,
          'limitation': 'operator evidence; server API alone cannot prove loaded tensor identity'})
    m = plan['model']
    client = LocalChatModel(m['name'], api_base=m['api_base'], api_model=m['name'], api_timeout=m['api_timeout'])
    assert client.remote_mode == 'chat_completions'
    post = client.session.post
    def logged_post(url, **kwargs):
        if url != m['api_base'] + '/v1/chat/completions':
            raise RuntimeError('Unexpected endpoint')
        sink({'kind': 'http_payload', 'url': url, 'payload': kwargs['json']})
        response = post(url, **kwargs)
        sink({'kind': 'http_response', 'status': response.status_code, 'body': response.text})
        return response
    client.session.post = logged_post
    return client


def execute(plan_path, output, backend, attestation=None):
    plan = validate_plan(plan_path)
    if (backend == 'synthetic') != (plan['label'] == 'SYNTHETIC_POLICY_REAL_ENV'):
        raise ValueError('Backend/plan label mismatch')
    output.mkdir(parents=True, exist_ok=False)
    dump(output / 'plan.json', plan)
    event_file = (output / 'events.jsonl').open('x')
    def sink(event):
        event_file.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
        event_file.flush()
    records = {s: [] for s in ['train', 'val', 'test']}
    config = plan['config']
    random.seed(config['seed'])
    import numpy as np
    np.random.seed(config['seed'])
    models, controls, eu_models = {}, {}, {}
    try:
        client = SyntheticModel() if backend == 'synthetic' else real_model(plan, attestation, sink)
        model = LoggedModel(client, sink)
        with AuditSession(sink).install() as audit:
            for split in records:
                for task in [t for t in plan['tasks'] if t['split'] == split]:
                    pair_id = split + ':' + task['task_id'] + ':0'
                    audit.pair_id, audit.phase = pair_id, 'base'
                    try:
                        candidates = original.rollout_base_prefix_candidates(model, [task['gamefile']], split,
                            config['prefixes_per_game'], config['max_episode_steps'], config['action_max_tokens'])
                        if len(candidates) != 1 or candidates[0]['prefix'].step_index != 0:
                            raise RuntimeError('Frozen initial checkpoint missing; no replacement allowed')
                        audit.phase = 'branches'
                        kwargs = {key: config[key] for key in ['batch_size', 'confidence_max_tokens', 'verify_max_tokens',
                                  'action_max_tokens', 'verify_cost', 'wrong_penalty', 'step_cost', 'max_episode_steps',
                                  'intervention_mode', 'repair_horizon', 'expert_max_policy_steps', 'expert_noise_rate']}
                        kwargs['seed'] = config['seed'] + {'train': 0, 'val': 1000, 'test': 2000}[split]
                        rows, _ = original.build_rows(model, candidates, **kwargs)
                        record = audit.paired_record(rows[0], config)
                    except Exception:
                        record = {'pair_id': pair_id, 'valid_pair': False, 'row': None,
                                  'invalid_reasons': [{'execution_error': traceback.format_exc()}]}
                    records[split].append(record)
                    dump(output / (pair_id.replace(':', '_') + '.json'), record)
                    sink({'kind': 'pair_complete', 'pair_id': pair_id, 'valid': record['valid_pair']})
                    print(pair_id, 'valid=' + str(record['valid_pair']), flush=True)
                raw_rows = [r['row'] for r in records[split] if r['row'] is not None]
                if raw_rows:
                    original.save_rows(raw_rows, output / 'original_raw' / f'{split}_rows.csv')
                dump(output / f'{split}_records.json', records[split])
                if split == 'val':
                    # Freeze before any test-task generation, features or outcomes are read.
                    for scope in ('valid_pairs', 'original_raw'):
                        train, val = records['train'], records['val']
                        if scope == 'original_raw':
                            train = [dict(r, valid_pair=True) for r in train if r['row'] is not None]
                            val = [dict(r, valid_pair=True) for r in val if r['row'] is not None]
                        try:
                            models[scope], controls[scope] = freeze_baselines(train, val)
                            eu_models[scope] = policy.fit_correctness_models(valid_rows(train), verify_mode='no_preview')
                        except ValueError as exc:
                            controls[scope] = {'blocked': str(exc)}
                    dump(output / 'frozen_controls_before_test.json', controls)
                    with (output / 'frozen_models_before_test.pkl').open('xb') as f:
                        cloudpickle.dump({'failure': models, 'eu': eu_models}, f)
                    sink({'kind': 'freeze_before_test', 'controls_hash': digest(controls)})
            summaries = {}
            for scope in models:
                if 'blocked' in controls[scope]:
                    continue
                test = records['test'] if scope == 'valid_pairs' else [dict(r, valid_pair=True) for r in records['test'] if r['row'] is not None]
                result = evaluate_frozen(models[scope], controls[scope], test)
                rows = valid_rows(test)
                if rows:
                    x = policy.feature_matrix(rows)
                    probs = [m.predict_proba(x)[:, 1] for m in eu_models[scope]]
                    eu = [policy.expected_utility_from_probability(v, verify=bool(i), verify_cost=config['verify_cost'],
                           wrong_penalty=config['wrong_penalty']) for i, v in enumerate(probs)]
                    actions = policy.choose_expected_utility_actions(*eu)
                    result['original_explicit_eu'] = {'actions': actions, 'metrics': independent_metrics(rows, actions),
                        'future_step_cost_omitted': True, 'realized_steps_used_for_decisions': False}
                summaries[scope] = result
            summary = {'label': plan['label'], 'by_split': {s: {'attempted': len(rs), 'valid': sum(r['valid_pair'] for r in rs),
                       'invalid': sum(not r['valid_pair'] for r in rs)} for s, rs in records.items()},
                       'evaluation': summaries, 'controls': controls,
                       'native_state_equivalence_proven': False,
                       'no_resampling': True, 'cost_predictor_added': False}
            dump(output / 'summary.json', summary)
            print(json.dumps(summary, indent=2))
    finally:
        event_file.close()
        check_upstream()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--synthetic', action='store_true')
    run = sub.add_parser('run')
    run.add_argument('--plan', type=Path, required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--backend', choices=['synthetic', 'http'], required=True)
    run.add_argument('--server-attestation', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output, args.synthetic)
    else:
        execute(args.plan, args.output, args.backend, args.server_attestation)


if __name__ == '__main__':
    main()
