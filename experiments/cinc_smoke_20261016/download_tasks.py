"""Official public ALFWorld task archives only; no weights."""
import urllib.request,zipfile,pathlib,json,hashlib
root=pathlib.Path('/home/hly/agent-research/data/alfworld-cinc-audit'); root.mkdir(exist_ok=True)
manifest=[]
for tag,name in [('0.2.2','json_2.1.1_json.zip'),('0.2.2','json_2.1.1_pddl.zip'),('0.4.0','json_2.1.2_tw-pddl.zip')]:
 url=f'https://github.com/alfworld/alfworld/releases/download/{tag}/{name}'
 path=root/name
 if not path.exists():
  urllib.request.urlretrieve(url,path)
 with zipfile.ZipFile(path) as z:
  total=sum(i.file_size for i in z.infolist())
  assert total<4_000_000_000, total
  for i in z.infolist():
   assert (root/i.filename).resolve().is_relative_to(root.resolve()), i.filename
   assert (i.external_attr >> 16) & 0o170000 != 0o120000
  z.extractall(root)
 manifest.append(dict(url=url,bytes=path.stat().st_size,unpacked_bytes=total,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 print(manifest[-1],flush=True)
(root/'download_manifest.json').write_text(json.dumps(manifest,indent=2))
