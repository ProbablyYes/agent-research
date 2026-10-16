import hashlib
import json
from pathlib import Path
import unittest

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[2]
        self.path=self.root/'api_pilot/plans/ofox_gpt4o_mini_draft/plan.json'
        self.plan=json.loads(self.path.read_text())
        self.old=json.loads((self.root/'pilot_validity/plans/real_pilot_final/plan.json').read_text())
    def test_exact_tasks_and_parameters(self):
        self.assertEqual(self.plan['tasks'],self.old['tasks'])
        self.assertEqual(self.plan['config'],self.old['config'])
        self.assertEqual([t['split'] for t in self.plan['tasks']],['train','train','val','val','test','test'])
    def test_no_collection_authorization(self):
        self.assertFalse(self.plan['execution']['enabled'])
        self.assertEqual(self.plan['execution']['authorized_collection_requests'],0)
        self.assertIsNone(self.plan['execution']['runner'])
    def test_separate_model_identity(self):
        self.assertNotEqual(self.plan['model']['name'],self.old['model']['name'])
        self.assertFalse(self.plan['model']['revision_verified'])
        self.assertFalse(self.plan['native_state_equivalence_proven'])
    def test_digest_and_request_bound(self):
        expected=json.loads(self.path.with_name('plan.sha256.json').read_text())['sha256']
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),expected)
        c=self.plan['config']; n=len(self.plan['tasks']); h=c['max_episode_steps']
        self.assertEqual(n*(h+(h-1)+1),self.plan['cost_estimates']['max_requests'])
        self.assertEqual(n*((2*h-1)*c['action_max_tokens']+c['confidence_max_tokens']),5664)

if __name__=='__main__':unittest.main()
