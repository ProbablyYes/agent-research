"""Check the accepted published supplementary history, without executing it."""
import pathlib,json,hashlib,re
P=pathlib.Path(__file__).resolve().parents[1]/'supplement';m=json.load(open(P/'SUPPLEMENT_MANIFEST.json'));response=(P/'swesmith_row.json').read_bytes();assert hashlib.sha256(response).hexdigest()==m['raw_response_sha256'];entry=json.loads(response)['rows'][0];assert entry['truncated_cells']==[];row=entry['row'];messages=json.loads(row['messages']);assert len(messages)==49
assert row==json.load(open(P/'swesmith_sample.json'));assert hashlib.sha256((P/'swesmith_sample.json').read_bytes()).hexdigest()==m['sample_sha256']
render=[json.loads(x) for x in re.findall(r'``````json\n(.*?)\n``````',(P/'SWESMITH_READABLE.md').read_text(),re.S)];assert render==messages
calls={};returns=[]
for n,msg in enumerate(messages,1):
 for c in msg.get('tool_calls') or []:calls[c['id']]=(n,c['function']['name'])
 if msg['role']=='tool':
  for tid in msg.get('tool_call_ids') or []:assert tid in calls and calls[tid][0]<n;returns.append(tid)
missing=[(tid,v) for tid,v in calls.items() if tid not in returns];assert len(missing)==1 and missing[0][1]==(49,'submit')
out={'status':'PASS_with_published_format_limits','messages':len(messages),'tool_calls':len(calls),'tool_returns':len(returns),'unreturned_terminal_action':{'event':49,'name':'submit'},'render_roundtrip':True,'response_sha256':m['raw_response_sha256'],'not_provider_raw_log':True,'no_environment_reexecution':True};(P/'verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
