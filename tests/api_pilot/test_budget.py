import copy
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock

from api_pilot.budget import (Ledger,Halt,Deadline,BUDGET_NANO,MAX_REQUESTS,
                             guarded_call,guarded_action,strict_action,MODEL,deadline)

CONTRACT={'reliable_billing_bound':True,'input_bound':128000,
          'input_nano_per_token':150,'output_nano_per_token':600,
          'evidence':'MOCK ONLY, not a provider billing attestation'}
PAYLOAD={'model':MODEL,'messages':[{'role':'user','content':'Synthetic prompt'}],
         'temperature':0,'max_tokens':24,'stream':False}

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'ledger.sqlite3'
        self.l=Ledger.create(self.path,CONTRACT);self.addCleanup(self.l.close)

    def result(self):
        return {'usage':{'prompt_tokens':12,'completion_tokens':4,'total_tokens':16},'text':'ACTION: look'}

    def transport(self,text='ACTION: look',usage=None,status=200):
        t=Mock();r=Mock(status_code=status)
        r.json.return_value={'model':MODEL,'object':'chat.completion','choices':[{'message':{'content':text},'finish_reason':'stop'}],
                             'usage':usage if usage is not None else self.result()['usage']}
        t.post.return_value=r
        return t

    def call(self,t=None,rid='smoke:0'):
        return guarded_call(self.l,rid,'smoke',PAYLOAD,transport=t or self.transport(),credential_reader=lambda:'synthetic-fixture-secret')

    def test_reserve_before_send(self):
        t=self.transport()
        def post(*a,**kw):
            other=Ledger(self.path)
            try:self.assertEqual(other.summary()['unresolved_requests'],1)
            finally:other.close()
            self.assertFalse(kw['allow_redirects']);self.assertTrue(kw['verify']);self.assertEqual(kw['timeout'],(10,50))
            return self.transport().post.return_value
        t.post.side_effect=post
        self.call(t);self.assertEqual(t.post.call_count,1)

    def test_success_reservation_not_refunded(self):
        self.call();s=self.l.summary()
        self.assertEqual(s['reserved_nano_usd'],19214400)
        self.assertEqual(s['estimated_nano_usd'],4200)
        self.assertEqual(s['unresolved_requests'],0)

    def test_budget_exceeded_before_send(self):
        for i in range(157):
            if i==156:
                with self.assertRaises(Halt):self.l.reserve(str(i),'pilot',PAYLOAD)
            else:
                self.l.reserve(str(i),'pilot',PAYLOAD);self.l.complete(str(i),self.result())
        self.assertLessEqual(self.l.summary()['reserved_nano_usd'],BUDGET_NANO)
        self.assertEqual(self.l.summary()['halted'],'budget_limit')

    def test_duplicate_completed(self):
        self.call();t=self.transport()
        with self.assertRaises(Halt):self.call(t)
        t.post.assert_not_called()

    def test_interrupted_reservation_survives_reopen(self):
        self.l.reserve('first','smoke',PAYLOAD)
        other=Ledger(self.path)
        try:
            t=self.transport()
            with self.assertRaises(Halt):guarded_call(other,'second','pilot',PAYLOAD,transport=t)
            t.post.assert_not_called();self.assertEqual(other.summary()['request_reservations'],1)
            self.assertEqual(other.summary()['reserved_nano_usd'],19214400)
        finally:other.close()

    def test_create_existing_refused(self):
        with self.assertRaises(FileExistsError):Ledger.create(self.path,CONTRACT)

    def test_missing_ledger_not_recreated(self):
        with self.assertRaises(Halt):Ledger(Path(self.tmp.name)/'missing')

    def test_unknown_billing_blocks_key_read_and_network(self):
        p=Path(self.tmp.name)/'unknown';c=dict(CONTRACT,reliable_billing_bound=False)
        l=Ledger.create(p,c);t=self.transport();reader=Mock()
        try:
            with self.assertRaises(Halt):guarded_call(l,'first','smoke',PAYLOAD,transport=t,credential_reader=reader)
            t.post.assert_not_called();reader.assert_not_called()
            self.assertEqual(l.summary()['request_reservations'],0)
        finally:l.close()

    def test_smoke_pilot_share_totals(self):
        self.call()
        self.l.reserve('pilot:0','pilot',PAYLOAD);self.l.complete('pilot:0',self.result())
        self.assertEqual(self.l.summary()['request_reservations'],2)
        self.assertEqual(self.l.summary()['reserved_nano_usd'],38428800)

    def test_request_limit(self):
        l=Ledger.create(Path(self.tmp.name)/'small',dict(CONTRACT,input_bound=1,input_nano_per_token=1,output_nano_per_token=1))
        try:
            for i in range(MAX_REQUESTS):
                l.reserve(str(i),'smoke',PAYLOAD);l.complete(str(i),{'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}})
            with self.assertRaises(Halt):l.reserve('overflow','pilot',PAYLOAD)
            self.assertEqual(l.summary()['halted'],'request_limit')
        finally:l.close()

    def test_output_limit_before_send(self):
        p=dict(PAYLOAD,max_tokens=65);t=self.transport()
        with self.assertRaises(Halt):guarded_call(self.l,'bad','smoke',p,transport=t)
        t.post.assert_not_called()

    def test_timeout_unknown_bill_preserved(self):
        t=self.transport();t.post.side_effect=TimeoutError('synthetic-fixture-secret')
        with self.assertRaises(Halt) as e:self.call(t)
        self.assertNotIn('synthetic-fixture-secret',str(e.exception))
        self.assertEqual(t.post.call_count,1)
        self.assertEqual(self.l.summary()['unresolved_requests'],1)
        self.assertGreater(self.l.summary()['reserved_nano_usd'],0)

    def test_deadline_no_retry(self):
        t=self.transport();t.post.side_effect=Deadline()
        with self.assertRaises(Halt):self.call(t)
        self.assertEqual(t.post.call_count,1);self.assertTrue(self.l.summary()['halted'])

    def test_http_error_round_stops(self):
        t=self.transport(status=503)
        with self.assertRaises(Halt):self.call(t)
        with self.assertRaises(Halt):self.call(t,'pilot:0')
        self.assertEqual(t.post.call_count,1)

    def test_redirect_rejected(self):
        t=self.transport(status=302)
        with self.assertRaises(Halt):self.call(t)
        self.assertEqual(t.post.call_count,1)

    def test_missing_usage(self):
        t=self.transport(usage={})
        with self.assertRaises(Halt):self.call(t)
        self.assertEqual(self.l.summary()['unresolved_requests'],1)

    def test_unknown_billing_field(self):
        t=self.transport(usage=dict(self.result()['usage'],additional_charge=3))
        with self.assertRaises(Halt):self.call(t)
        self.assertTrue(self.l.summary()['halted'])

    def test_invalid_total(self):
        t=self.transport(usage={'prompt_tokens':12,'completion_tokens':4,'total_tokens':18})
        with self.assertRaises(Halt):self.call(t)

    def test_model_change(self):
        t=self.transport();t.post.return_value.json.return_value['model']='other'
        with self.assertRaises(Halt):self.call(t)

    def test_secret_response_not_saved(self):
        with self.assertRaises(Halt):self.call(self.transport('synthetic-fixture-secret'))
        self.assertNotIn(b'synthetic-fixture-secret',self.path.read_bytes())

    def test_parse_failure_stops_preserves_output(self):
        t=self.transport('ACTION: not an admissible action')
        with self.assertRaises(Halt):guarded_action(self.l,'s','smoke',PAYLOAD,['look'],transport=t,credential_reader=lambda:'fixture')
        self.assertEqual(self.l.summary()['halted'],'action_parse_failure')
        result=json.loads(self.l.db.execute('SELECT result FROM requests').fetchone()[0])
        self.assertEqual(result['text'],'ACTION: not an admissible action')
        with self.assertRaises(Halt):self.call(t,'next')
        self.assertEqual(t.post.call_count,1)

    def test_process_exit_after_reserve(self):
        script="from api_pilot.budget import Ledger; import os,sys,json; l=Ledger(sys.argv[1]); l.reserve('crash','smoke',json.loads(sys.argv[2])); os._exit(23)"
        r=subprocess.run([sys.executable,'-c',script,str(self.path),json.dumps(PAYLOAD)],capture_output=True)
        self.assertEqual(r.returncode,23)
        other=Ledger(self.path)
        try:
            self.assertEqual(other.summary()['unresolved_requests'],1)
            with self.assertRaises(Halt):other.reserve('after_crash','pilot',PAYLOAD)
            self.assertEqual(other.summary()['reserved_nano_usd'],19214400)
        finally:other.close()

    def test_wall_clock_deadline(self):
        start=time.monotonic()
        with self.assertRaises(Deadline):
            with deadline(.02): time.sleep(1)
        self.assertLess(time.monotonic()-start,.5)

    def test_strict_no_fuzzy_fallback(self):
        self.assertEqual(strict_action('ACTION: Look',['look']),'look')
        for text in ['','lok','ACTION: lok','ACTION: look\nACTION: go to kitchen']:
            with self.assertRaises(Halt):strict_action(text,['look'])

if __name__=='__main__':unittest.main()
