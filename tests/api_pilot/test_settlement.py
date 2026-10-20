import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from api_pilot.budget import Ledger,Halt,guarded_call,MODEL

C={'reliable_billing_bound':False,'user_accepted_nominal_accounting':True,'settle_completed_to_nominal_usage':True,
   'input_bound':128000,'input_nano_per_token':150,'output_nano_per_token':600}
P={'model':MODEL,'messages':[{'role':'user','content':'fixture'}],'temperature':0,'max_tokens':24,'stream':False}

class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.l=Ledger.create(Path(self.tmp.name)/'ledger',C);self.addCleanup(self.l.close)
    def test_settle_known_keep_unknown(self):
        self.l.reserve('s0','smoke',P)
        self.assertEqual(self.l.summary()['committed_nano_usd'],19214400)
        self.l.complete('s0',{'usage':{'prompt_tokens':100,'completion_tokens':4,'total_tokens':104}})
        self.assertEqual(self.l.summary()['committed_nano_usd'],17400)
        self.l.reserve('p0','pilot',P)
        self.assertEqual(self.l.summary()['committed_nano_usd'],19231800)
        self.assertEqual(self.l.summary()['reserved_nano_usd'],38428800)
    def test_budget_still_before_transmission(self):
        self.l.reserve('s0','smoke',P)
        self.l.complete('s0',{'usage':{'prompt_tokens':128000,'completion_tokens':24,'total_tokens':128024}})
        # Seed other completed nominal costs to test the exact admission boundary, no HTTP.
        with self.l.db:
            for i in range(155):
                self.l.db.execute("INSERT INTO requests VALUES (?,?,?,?,?,'completed',NULL,?)",(f'fixture{i}','smoke','fixture',19214400,24,19214400))
        self.assertEqual(self.l.summary()['committed_nano_usd'],2997446400)
        t=Mock()
        with self.assertRaises(Halt):guarded_call(self.l,'overflow','pilot',P,transport=t)
        t.post.assert_not_called()
    def test_unknown_usage_never_settled(self):
        self.l.reserve('s0','smoke',P)
        with self.assertRaises(Halt):self.l.complete('s0',{'usage':{}})
        self.assertEqual(self.l.summary()['committed_nano_usd'],19214400)
    def test_length_output_preserved_no_retry(self):
        t=Mock();r=Mock(status_code=200)
        r.json.return_value={'model':MODEL,'object':'chat.completion','choices':[{'message':{'content':'ACTION: go to'},'finish_reason':'length'}],
                            'usage':{'prompt_tokens':100,'completion_tokens':24,'total_tokens':124}}
        t.post.return_value=r
        with self.assertRaises(Halt):guarded_call(self.l,'s0','smoke',P,transport=t,credential_reader=lambda:'synthetic_credential')
        e=json.loads(self.l.db.execute('SELECT evidence FROM observations').fetchone()[0])
        self.assertEqual(e['text'],'ACTION: go to');self.assertEqual(e['usage']['completion_tokens'],24)
        self.assertEqual(t.post.call_count,1)
        self.assertEqual(self.l.summary()['committed_nano_usd'],19214400)

if __name__=='__main__':unittest.main()
