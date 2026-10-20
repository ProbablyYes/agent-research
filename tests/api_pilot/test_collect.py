import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from api_pilot.budget import Ledger,Halt,MODEL
from api_pilot.collect import CloudModel,EventLog,strict_parser,smoke,pilot,original,ROOT
from api_pilot.export import export

CONTRACT={'reliable_billing_bound':False,'user_accepted_nominal_accounting':True,
          'input_bound':128000,'input_nano_per_token':150,'output_nano_per_token':600}

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.l=Ledger.create(self.root/'ledger',CONTRACT);self.addCleanup(self.l.close)
        self.log=EventLog(self.root);self.addCleanup(self.log.close)
        plan=json.loads((ROOT/'pilot_validity/plans/real_pilot_final/plan.json').read_text())
        self.tasks=plan['tasks'];self.config=dict(plan['config'],max_episode_steps=2)
        self.t=Mock();self.t.post.side_effect=self.post
        self.m=CloudModel(self.l,self.log,'smoke',self.t,lambda:'fixture_credential_only')
    def post(self,url,**kwargs):
        prompt=kwargs['json']['messages'][0]['content']
        if 'Respond starting with: CONFIDENCE:' in prompt:text='CONFIDENCE: 50'
        else:text='ACTION: '+prompt.split('Admissible commands:\n')[-1].splitlines()[0].removeprefix('- ')
        r=Mock(status_code=200);r.json.return_value={'model':MODEL,'object':'chat.completion',
            'choices':[{'message':{'content':text},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':100,'completion_tokens':4,'total_tokens':104}}
        return r
    def test_nominal_amendment_not_false_attestation(self):
        c=dict(CONTRACT,user_accepted_nominal_accounting=False)
        l=Ledger.create(self.root/'blocked',c)
        try:
            l.halt('unverified_billing_bound')
            l.accept_nominal_accounting({'round_id':'api-agent-20261020','user_authorized':True})
            self.assertFalse(l.contract['reliable_billing_bound'])
            self.assertTrue(l.contract['user_accepted_nominal_accounting'])
            self.assertEqual(l.summary()['request_reservations'],0)
            with self.assertRaises(Halt):l.accept_nominal_accounting({'round_id':'api-agent-20261020','user_authorized':True})
        finally:l.close()
    def test_smoke_real_env_mock_api(self):
        self.log.context={'phase':'smoke','task_id':self.tasks[0]['task_id'],'split':'train'}
        prev=original.extract_action
        with strict_parser(self.m,self.log):result=smoke(self.m,self.tasks[0],self.config,self.log)
        self.assertIs(prev,original.extract_action)
        self.assertTrue(result['protocol_passed']);self.assertEqual(result['steps'],2)
        self.assertEqual(self.t.post.call_count,2)
        (self.root/'summary.json').write_text(json.dumps(result))
        stats=export(self.root);self.assertEqual(stats['steps'],2)
        rows=[json.loads(x) for x in (self.root/'trajectories.jsonl').read_text().splitlines()]
        self.assertEqual(rows[1]['history_prefix'][0]['action'],rows[0]['action'])
        self.assertTrue(all(r['new_request_for_step'] for r in rows))
    def test_invalid_action_no_step(self):
        r=self.post('',json={'messages':[{'content':'Admissible commands:\n- look'}]})
        r.json.return_value['choices'][0]['message']['content']='ACTION: illegal'
        self.t.post.side_effect=None;self.t.post.return_value=r
        with strict_parser(self.m,self.log):
            with self.assertRaises(Halt):smoke(self.m,self.tasks[0],self.config,self.log)
        self.assertEqual(self.t.post.call_count,1)
        self.assertNotIn('"kind": "step"',(self.root/'events.jsonl').read_text())
    def test_environment_exception_no_second_request(self):
        with strict_parser(self.m,self.log),patch('api_pilot.collect.Recorder.step',side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):smoke(self.m,self.tasks[0],self.config,self.log)
        self.assertEqual(self.t.post.call_count,1)
    def test_six_tasks_audits_freeze_before_test(self):
        self.m.phase='pilot'
        with strict_parser(self.m,self.log):result=pilot(self.m,self.tasks,self.config,self.root,self.log)
        self.assertEqual(sum(v['valid'] for v in result['by_split'].values()),6)
        events=[json.loads(x) for x in (self.root/'events.jsonl').read_text().splitlines()]
        freeze=next(i for i,e in enumerate(events) if e['kind']=='freeze_before_test')
        first_test=next(i for i,e in enumerate(events) if e['kind']=='task_start' and e['split']=='test')
        self.assertLess(freeze,first_test)
        self.assertEqual(sum(e['kind']=='pre_action_replay_audit' and e['passed'] for e in events),12)
        self.assertEqual(self.t.post.call_count,24)
        (self.root/'summary.json').write_text(json.dumps(result))
        stats=export(self.root)
        rows=[json.loads(x) for x in (self.root/'trajectories.jsonl').read_text().splitlines()]
        reused=[r for r in rows if r['action_origin']=='reused_base_proposal']
        self.assertEqual(len(reused),6)
        self.assertTrue(all(r['request_id'] and r['usage'] is None for r in reused))

if __name__=='__main__':unittest.main()
