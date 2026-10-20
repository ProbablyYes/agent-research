"""Offline extraction; never executes trajectory tools or calls a model.
Input: partial source bundle downloaded publicly; preserves exact UTF-8 object bytes.
"""
import json, hashlib, pathlib, sys
P=pathlib.Path(__file__).resolve().parents[1]
s=pathlib.Path(sys.argv[1]).read_text(); dec=json.JSONDecoder(); i=1; meta={}
while True:
 while s[i].isspace() or s[i]==',': i+=1
 key,i=dec.raw_decode(s,i)
 while s[i].isspace() or s[i]==':': i+=1
 if key=='simulations':break
 value,i=dec.raw_decode(s,i);meta[key]=value
(P/'raw'/'source_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
i+=1; selected=[]; scanned=[]; counts={0:0,1:0}; last=0
for idx in range(10):
 while s[i].isspace() or s[i]==',':i+=1
 v,end=dec.raw_decode(s,i); r=(v.get('reward_info') or {}).get('reward')
 scanned.append({'source_index':idx,'id':v['id'],'task_id':v['task_id'],'reward':r,'messages':len(v['messages']),'termination_reason':v['termination_reason']})
 if r in counts and counts[r]<2 and v['messages']:
  counts[r]+=1; name=v['task_id']+'_trial'+str(v['trial']); raw=s[i:end].encode(); f=P/'raw'/(name+'.json');f.write_bytes(raw)
  start_byte=len(s[:i].encode());end_byte=start_byte+len(raw)-1
  task=next(t for t in meta['tasks'] if t['id']==v['task_id'])
  text='# '+name+'\n\n公开 τ³-bench 原始记录；非本实验室 Agent 运行。E 编号为 messages 原始数组索引 + 1。工具内容仅作文本展示，不执行。\n\n## 任务规格（分析者可见；不得假设 Agent 预先可见）\n\n```json\n'+json.dumps(task,ensure_ascii=False,indent=2)+'\n```\n\n## 原始消息（完整字段、原顺序）\n'
  for n,m in enumerate(v['messages'],1):text+='\n### E'+str(n)+' — '+m['role']+'\n\n``````json\n'+json.dumps(m,ensure_ascii=False,indent=2)+'\n``````\n'
  rest={k:x for k,x in v.items() if k!='messages'};text+='\n## 原始运行元数据与评分\n\n``````json\n'+json.dumps(rest,ensure_ascii=False,indent=2)+'\n``````\n'
  (P/'readable'/(name+'.md')).write_text(text)
  selected.append({'sample_id':name,'source_array_index':idx,'source_json_pointer':'/simulations/'+str(idx),'source_byte_range_inclusive':[start_byte,end_byte],'id':v['id'],'task_id':v['task_id'],'trial':v['trial'],'reward':r,'reward_basis':v['reward_info']['reward_basis'],'event_count':len(v['messages']),'raw_file':str(f.relative_to(P)),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'readable_file':'readable/'+name+'.md','termination_reason':v['termination_reason']})
 i=end;last=end
prefix=s[:last].encode();(P/'raw'/'source_prefix.bin').write_bytes(prefix)
manifest={'artifact_base_directory':'/home/hly/agent-research/public_trajectory_research/phase1','research_head_before_extraction':'ae0425469341b381a2a69badc33d5e150078f09a','dataset_kind':'external_public_model_trajectories','not_own_alfworld_pilot':True,'source_url':'https://sierra-tau-bench-public.s3.amazonaws.com/submissions/gpt-5-6-sol_sierra_2026-08-04/trajectories/banking_knowledge_results.json','download_date':'2026-10-20','source_object_bytes':150287419,'source_etag':'aa82aa9efa074bbc843aaa04ef697d5f-18','source_prefix_bytes':len(prefix),'source_prefix_sha256':hashlib.sha256(prefix).hexdigest(),'full_bundle_sha256':None,'license':'Repository MIT; separate S3-specific license not found; local research copies, no raw redistribution this round','benchmark_declared_version':'1.0.1','runtime_git_commit':meta['info']['git_commit'],'catalog_git_commit':'989d3285ae669e49503324bdb9981bf14fccedeb','agent_info':meta['info']['agent_info'],'user_info':{k:v for k,v in meta['info']['user_info'].items() if k!='global_simulation_guidelines'},'sampling':'Inspect source positions 0..9, take first two reward=1 and first two reward=0 with nonempty messages; preserve order; outcome-balanced convenience sample, not prevalence estimate. Infrastructure failure at position8 retained in screening log, not silently replaced.','screening':scanned,'samples':selected,'limitations':['API alias not immutable backend checkpoint','Only published message completeness verified, not provider hidden reasoning or every actual prompt','No interventions or causal estimates','Raw source bundle partial transfer; prefix and selected object hashes only']}
(P/'TRAJECTORY_SAMPLE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'samples':selected,'prefix_bytes':len(prefix)},indent=2))
