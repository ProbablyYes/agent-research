import json
import tempfile
import unittest
from pathlib import Path
from pilot_validity.attest import create
from pilot_validity.run import MODEL

class ProvenanceTests(unittest.TestCase):
    def test_missing_weights_fail_without_downloading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan=root/'plan.json';plan.write_text(json.dumps({'model':MODEL}))
            freeze=root/'freeze.txt';freeze.write_text('vllm==0.6.6\ntransformers==4.46.3\n')
            log=root/'server.log';log.write_text('SYNTHETIC SERVICE LOG')
            with self.assertRaises(ValueError):create(plan,root,log,freeze,root/'proof.json')
            self.assertFalse((root/'proof.json').exists())

    def test_wrong_server_version_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan=root/'plan.json';plan.write_text(json.dumps({'model':MODEL}))
            freeze=root/'freeze.txt';freeze.write_text('vllm==0.0.0\n')
            with self.assertRaisesRegex(ValueError,'freeze mismatch'):
                create(plan,root,root/'missing.log',freeze,root/'proof.json')
