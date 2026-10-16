import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from api_pilot.probe import probe, read_key, ENDPOINT

class ProbeTests(unittest.TestCase):
    def call(self, response=None, error=None):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        state = Path(self.tmp.name) / 'attempt.json'
        transport = Mock()
        if error: transport.post.side_effect = error
        else: transport.post.return_value = response
        result = probe('synthetic_secret_fixture', transport, state)
        return result, transport, state

    def response(self, status=200, **override):
        r=Mock(status_code=status)
        data={'model':'gpt-4o-mini-2024-07-18','object':'chat.completion',
              'choices':[{'message':{'content':'OK'},'finish_reason':'stop'}],
              'usage':{'prompt_tokens':13,'completion_tokens':1,'total_tokens':14}}
        data.update(override);r.json.return_value=data
        return r

    def test_success_and_estimate(self):
        result,t,s=self.call(self.response())
        self.assertTrue(result['normal_return']); self.assertAlmostEqual(result['estimated_usd'],.00000255)
        self.assertNotIn('synthetic_secret_fixture',json.dumps(result))
        args,kw=t.post.call_args
        self.assertEqual(args,(ENDPOINT,));self.assertFalse(kw['allow_redirects']);self.assertTrue(kw['verify'])
        self.assertEqual(kw['json']['max_tokens'],16)

    def test_reservation_blocks_second_call(self):
        result,t,s=self.call(self.response())
        with self.assertRaises(FileExistsError):probe('fixture',t,s)
        self.assertEqual(t.post.call_count,1)

    def test_timeout_no_retry_no_secret(self):
        result,t,s=self.call(error=TimeoutError('synthetic_secret_fixture'))
        self.assertEqual(t.post.call_count,1);self.assertNotIn('synthetic_secret_fixture',json.dumps(result))
        self.assertTrue(s.exists())

    def test_redirect_no_follow(self):
        result,t,s=self.call(self.response(302))
        self.assertFalse(result['normal_return']);t.post.assert_called_once()

    def test_server_error_no_retry(self):
        result,t,s=self.call(self.response(500))
        self.assertEqual(result['http_status'],500);t.post.assert_called_once()

    def test_missing_usage_not_zero_cost(self):
        result,t,s=self.call(self.response(usage=None))
        self.assertIsNone(result['estimated_usd'])

    def test_unexpected_model_redacted(self):
        result,t,s=self.call(self.response(model='synthetic_secret_fixture'))
        self.assertFalse(result['normal_return']);self.assertNotIn('synthetic_secret_fixture',json.dumps(result))

    def test_bad_json_no_retry(self):
        r=self.response();r.json.side_effect=ValueError('synthetic_secret_fixture')
        result,t,s=self.call(r);t.post.assert_called_once();self.assertFalse(result['normal_return'])

    def test_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'key';p.write_text('fixture');p.chmod(0o600)
            self.assertEqual(read_key(p),'fixture')
            p.chmod(0o644)
            with self.assertRaises(ValueError):read_key(p)
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):read_key(link)

if __name__=='__main__':unittest.main()
