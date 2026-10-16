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

    def test_symlinked_weights_preserve_filename_and_hash(self):
        from pilot_validity.core import sha
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);model=root/'snapshot';model.mkdir()
            for name in ['config.json','tokenizer_config.json','tokenizer.json']:(model/name).write_text('{}')
            blob=root/'blob';blob.write_bytes(b'SYNTHETIC NOT REAL WEIGHTS')
            (model/'model.safetensors').symlink_to(blob)
            plan=root/'plan.json';plan.write_text(json.dumps({'model':MODEL}))
            freeze=root/'freeze.txt';freeze.write_text('vllm==0.6.6\ntransformers==4.46.3\n')
            log=root/'server.log';log.write_text('SYNTHETIC SERVICE LOG')
            output=root/'proof.json';create(plan,model,log,freeze,output)
            proof=json.loads(output.read_text());key=str((model/'model.safetensors').absolute())
            self.assertEqual(proof['model_files'][key],sha(blob))
