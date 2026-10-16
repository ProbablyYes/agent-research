"""Record local service provenance after an operator prepares it; never start a service."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


def create(plan_path,model_dir,startup_log,server_freeze,output):
    plan=json.loads(plan_path.read_text())
    model=plan['model']
    freeze=server_freeze.read_text().lower().splitlines()
    for package in ['vllm','transformers']:
        if f'{package}=={model[package]}' not in freeze:
            raise ValueError('Server freeze mismatch: '+package)
    for required in ['config.json','tokenizer_config.json','tokenizer.json']:
        if not (model_dir/required).is_file():raise ValueError('Missing '+required)
    paths=sorted(p for p in model_dir.rglob('*') if p.is_file() and p.suffix in ('.json','.safetensors','.txt','.model'))
    if not any(p.suffix=='.safetensors' for p in paths):raise ValueError('No local model weights; do not download implicitly')
    keys=['name','revision','tokenizer_revision','server_seed','vllm','transformers','dtype',
          'max_model_len','gpu_memory_utilization','max_num_seqs','enforce_eager']
    proof={k:model[k] for k in keys}
    proof.update(model_files={str(p.resolve()):sha(p) for p in paths},
                 startup_log={'path':str(startup_log.resolve()),'sha256':sha(startup_log)},
                 server_freeze={'path':str(server_freeze.resolve()),'sha256':sha(server_freeze)},
                 provenance='Operator-declared requested config plus observed file hashes and package freeze; not proof of loaded tensors',
                 plan_sha256=sha(plan_path))
    with output.open('x') as f:json.dump(proof,f,indent=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['plan','model-dir','startup-log','server-freeze','output']:
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args();create(a.plan,a.model_dir,a.startup_log,a.server_freeze,a.output)


if __name__=='__main__':main()
