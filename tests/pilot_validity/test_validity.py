import copy
import dataclasses
import json
import math
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from pilot_validity.core import (ROOT, AuditSession, original, policy, validate_replay,
    differences, corrected_thresholds, route, independent_metrics, freeze_baselines,
    evaluate_frozen, sha)
from pilot_validity.run import SyntheticModel, CONFIG, check_upstream, real_model, MODEL
from oversight_branching import alfworld_text as a


def rows():
    return [dict(example_id=f'SYNTHETIC:{i}', features=[float(i)] * 25, confidence=50., verify_features=[0.] * 21,
                 continue_correct=True, verify_correct=False, u_continue=.95, u_verify=-1.08, u_quit=0.,
                 continue_branch_steps=5, verify_branch_steps=3) for i in range(8)]


def records(values):
    return [dict(pair_id=r['example_id'], row=r, valid_pair=True, invalid_reasons=[]) for r in values]


def fake_state():
    return dict(observation='room', admissible_commands=['look'], done=False, won=False,
                executed_actions=0, remaining_budget=20,
                accessible_state=dict(facts=['at(agent, room)'], moves=0, limit_steps=0, limit_max_steps=20,
                                      backend_won=False, backend_lost=False), missing_required_fields=[], wrapper_stack=['PddlEnv'])


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.s = fake_state()
        self.prefix = a.AlfworldPrefix('x','train','game','task','type',[],[],'room',['look'],0)

    def test_observation_mismatch(self):
        changed = copy.deepcopy(self.s); changed['observation']='wrong'
        self.assertFalse(validate_replay([self.s],[changed],self.prefix)['passed'])

    def test_commands_order_mismatch(self):
        changed = copy.deepcopy(self.s); changed['admissible_commands']=['go','look']
        self.assertFalse(validate_replay([self.s],[changed],self.prefix)['passed'])

    def test_done_won_and_budget_mismatch(self):
        for key,value in [('done',True),('won',True),('executed_actions',1),('remaining_budget',19)]:
            changed=copy.deepcopy(self.s);changed[key]=value
            with self.subTest(key=key):self.assertFalse(validate_replay([self.s],[changed],self.prefix)['passed'])

    def test_hidden_fact_mismatch(self):
        changed=copy.deepcopy(self.s);changed['accessible_state']['facts']=['at(agent, kitchen)']
        self.assertFalse(validate_replay([self.s],[changed],self.prefix)['passed'])

    def test_missing_fields_fail_closed(self):
        self.s['missing_required_fields']=['facts']
        self.assertFalse(validate_replay([self.s],[copy.deepcopy(self.s)],self.prefix)['passed'])

    def test_intermediate_mismatch_not_just_endpoint(self):
        ref=[copy.deepcopy(self.s),copy.deepcopy(self.s)]
        ref[1].update(executed_actions=1,remaining_budget=19)
        ref[1]['accessible_state']['limit_steps']=1
        replay=copy.deepcopy(ref);replay[0]['observation']='wrong earlier state'
        prefix=dataclasses.replace(self.prefix,step_index=1,history_actions=['look'],history_observations=['room'])
        self.assertFalse(validate_replay(ref,replay,prefix)['passed'])

    def test_constant_model_serialization(self):
        import cloudpickle
        model,controls=freeze_baselines(records(rows()),records(rows()))
        restored=cloudpickle.loads(cloudpickle.dumps(model))
        np.testing.assert_array_equal(model.predict_proba(policy.feature_matrix(rows())),
                                      restored.predict_proba(policy.feature_matrix(rows())))

    def test_constant_risk_counterexample(self):
        rs=rows();scores=np.zeros(len(rs))
        orig=policy.threshold_search_failure_scores(scores,rs)
        fixed=corrected_thresholds(rs,scores)
        self.assertEqual(orig['utility'],0)
        self.assertAlmostEqual(fixed['utility'],.95)
        self.assertEqual(route(scores,fixed['verify_threshold'],fixed['quit_threshold']),['continue']*len(rs))

    def test_all_simple_policies_are_representable(self):
        scores=[0,.5,1]
        self.assertEqual(route(scores,2,2),['continue']*3)
        self.assertEqual(route(scores,-1,2),['verify']*3)
        self.assertEqual(route(scores,-1,-1),['quit']*3)

    def test_test_label_mutation_cannot_select_policy(self):
        train,val=records(rows()),records(rows())
        model,controls=freeze_baselines(train,val)
        before=copy.deepcopy(controls)
        test=records(rows());a1=evaluate_frozen(model,controls,test)
        for item in test:
            item['row'].update(u_continue=-100.,u_verify=100.,continue_correct=False,verify_correct=True)
        a2=evaluate_frozen(model,controls,test)
        self.assertEqual(before,controls)
        for name in a1['policies']:
            self.assertEqual(a1['policies'][name]['actions'],a2['policies'][name]['actions'])
        self.assertIsNone(a2['test_selected_policy'])

    def test_future_lengths_do_not_enter_features(self):
        rs=rows();expected=policy.feature_matrix(rs)
        for row in rs:row.update(continue_branch_steps=10000,verify_branch_steps=9999,u_continue=100.)
        np.testing.assert_array_equal(expected,policy.feature_matrix(rs))
        self.assertEqual(float(policy.expected_utility_from_probability([1.],False,.05,1.)[0]),1.)

    def test_invalid_pair_denominator(self):
        model,controls=freeze_baselines(records(rows()),records(rows()))
        test=records(rows()[:2]);test[0]['valid_pair']=False
        result=evaluate_frozen(model,controls,test)
        self.assertEqual(result['denominators'],dict(attempted=2,valid=1,invalid=1,coverage=.5,invalid_ids=['SYNTHETIC:0']))
        self.assertEqual(result['policies']['always_continue']['metrics']['n'],1)
        test[1]['valid_pair']=False
        empty=evaluate_frozen(model,controls,test)
        self.assertIsNone(empty['policies']['original']['metrics']['utility'])
        self.assertEqual(empty['denominators']['invalid'],2)

    def test_no_valid_training_or_validation_blocks(self):
        with self.assertRaises(ValueError):freeze_baselines([],records(rows()))
        with self.assertRaises(ValueError):freeze_baselines(records(rows()),[])

    def test_metric_length_and_invalid_actions_rejected(self):
        with self.assertRaises(ValueError):independent_metrics(rows(),['continue'])
        with self.assertRaises(ValueError):independent_metrics(rows(),['nonsense']*8)

    def test_metrics_match_original(self):
        rs=rows();actions=['continue','verify','quit','continue']*2
        ours=independent_metrics(rs,actions);orig=policy.evaluate_actions(rs,actions)
        for key in ['utility','success_rate','control_regret','verify_rate','quit_rate']:
            self.assertAlmostEqual(ours[key],orig[key])

    def test_original_context_restored_on_error(self):
        factory,replay=original.make_single_game_env,original.replay_to_prefix
        with self.assertRaises(RuntimeError):
            with AuditSession().install():raise RuntimeError('injected')
        self.assertIs(original.make_single_game_env,factory)
        self.assertIs(original.replay_to_prefix,replay)
        check_upstream()

    def test_http_requires_evidence_before_client_creation(self):
        with patch('pilot_validity.run.importlib.util.find_spec',return_value=None),patch.dict(os.environ,{'OPENAI_API_KEY':''}):
            with self.assertRaisesRegex(RuntimeError,'provenance'):
                real_model({'model':MODEL},None,lambda _:None)


class RealEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events=[]
        manifest=json.loads((ROOT/'experiments/cinc_smoke_20261016/task_manifest.json').read_text())
        game=manifest['train'][0]
        config=dict(CONFIG,max_episode_steps=4)
        cls.config=config
        cls.session=AuditSession(cls.events.append)
        model=SyntheticModel()
        with cls.session.install() as audit:
            candidates=original.rollout_base_prefix_candidates(model,[game],'train',3,4,24)
            candidate=next(c for c in candidates if c['prefix'].step_index==2)
            cls.candidate=candidate
            for label,bad in [('valid',False),('injected_mismatch',True)]:
                audit.phase='branches';audit.pair_id=label
                chosen=copy.deepcopy(candidate)
                if bad:chosen['prefix'].observation='INTENTIONALLY WRONG'
                kwargs={key:config[key] for key in ['batch_size','confidence_max_tokens','verify_max_tokens','action_max_tokens',
                     'verify_cost','wrong_penalty','step_cost','max_episode_steps','intervention_mode','repair_horizon',
                     'expert_max_policy_steps','expert_noise_rate','seed']}
                result,_=original.build_rows(model,[chosen],**kwargs)
                record=audit.paired_record(result[0],config)
                setattr(cls,label,record)
            audit.pair_id='valid'
            tampered=copy.deepcopy(cls.valid['row']);tampered['u_continue']+=.5
            cls.cost_mismatch=audit.paired_record(tampered,config)
        # Compare exact raw outputs with the uninstrumented original on the same candidate.
        cls.uninstrumented_rows,_=original.build_rows(model,[copy.deepcopy(candidate)],**kwargs)
        out=Path(os.environ['CINC_TEST_OUTPUT'])
        out.mkdir(parents=True,exist_ok=True)
        (out/'real_checkpoint_records.json').write_text(json.dumps({'valid':cls.valid,'injected_mismatch':cls.injected_mismatch,
                         'cost_mismatch':cls.cost_mismatch},indent=2))
        (out/'real_checkpoint_events.json').write_text(json.dumps(cls.events,indent=2))

    def test_noninitial_checkpoint_both_branches(self):
        self.assertTrue(self.valid['valid_pair'],self.valid['invalid_reasons'])
        for role in ['continue','verify']:
            audit=self.valid['branches'][role]['audit']
            self.assertTrue(audit['passed'])
            self.assertEqual(len(audit['replay_states']),3)
            self.assertEqual(audit['replay_states'][-1]['remaining_budget'],2)
            self.assertTrue(audit['replay_states'][-1]['accessible_state']['facts'])

    def test_real_mismatch_persisted_both_branches(self):
        self.assertFalse(self.injected_mismatch['valid_pair'])
        self.assertIsNotNone(self.injected_mismatch['row'])
        for role in ['continue','verify']:
            self.assertFalse(self.injected_mismatch['branches'][role]['audit']['passed'])
            self.assertTrue(self.injected_mismatch['branches'][role]['audit']['differences'])

    def test_recompute_real_costs(self):
        for role in ['continue','verify']:
            branch=self.valid['recomputed'][role]
            self.assertEqual(branch['suffix_steps'],len(self.valid['branches'][role]['suffix_actions']))
            self.assertAlmostEqual(branch['realized_utility'],self.valid['row']['u_'+role])
        self.assertFalse(self.cost_mismatch['valid_pair'])
        self.assertTrue(any(x['field']=='u_continue' for x in self.cost_mismatch['invalid_reasons']))

    def test_original_upstream_still_clean(self):
        check_upstream()

    def test_raw_outputs_match_uninstrumented_original(self):
        self.assertEqual(self.valid['row'],self.uninstrumented_rows[0])


if __name__=='__main__':unittest.main(verbosity=2)
