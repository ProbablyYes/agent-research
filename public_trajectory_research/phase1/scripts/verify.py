"""Offline integrity and published-schema verification, no model calls."""
import json,hashlib,pathlib,re
P=pathlib.Path(__file__).resolve().parents[1];m=json.load(open(P/'TRAJECTORY_SAMPLE_MANIFEST.json'));prefix=(P/'raw/source_prefix.bin').read_bytes();results=[];schemas={}
assert hashlib.sha256(prefix).hexdigest()==m['source_prefix_sha256']
for row in m['samples']:
 b=(P/row['raw_file']).read_bytes();v=json.loads(b);a,z=row['source_byte_range_inclusive'];assert b==prefix[a:z+1];assert hashlib.sha256(b).hexdigest()==row['sha256'];assert len(v['messages'])==row['event_count']
 rendered=(P/row['readable_file']).read_text();blocks=re.findall(r'``````json\n(.*?)\n``````',rendered,re.S);assert [json.loads(x) for x in blocks[:-1]]==v['messages'];assert json.loads(blocks[-1])=={k:x for k,x in v.items() if k!='messages'}
 calls={};returns=[]
 for n,msg in enumerate(v['messages'],1):
  role=msg['role'];schemas.setdefault(role,{})
  for k,x in msg.items():schemas[role].setdefault(k,set()).add(type(x).__name__)
  for c in msg.get('tool_calls') or []:assert c['id'] not in calls;calls[c['id']]=n
  if role=='tool':assert msg['id'] in calls and calls[msg['id']]<n;returns.append(msg['id'])
 assert set(returns)==set(calls) and len(returns)==len(calls)
 ri=v['reward_info'];basis=ri['reward_basis'];assert len(basis)==1;expected=ri['db_check']['db_reward'] if basis==['DB'] else min(x['action_reward'] for x in ri['action_checks']);assert expected==ri['reward']
 results.append({'sample_id':row['sample_id'],'messages':len(v['messages']),'tool_calls':len(calls),'tool_returns':len(returns),'byte_hash_and_render_roundtrip':True,'published_reward_fields_consistent':True,'reward_reexecuted':False})
summary={'samples':len(results),'messages':sum(r['messages'] for r in results),'checks':['prefix_sha256','exact_source_bytes_per_sample','sample_sha256','message_count','lossless_readable_roundtrip','tool_id_linkage_and_order','published_reward_field_consistency'],'results':results,'simulation_schema':{k:type(x).__name__ for k,x in v.items()},'schema':{role:{k:sorted(v) for k,v in fields.items()} for role,fields in schemas.items()}}
(P/'evidence/verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='schema'},indent=2))
