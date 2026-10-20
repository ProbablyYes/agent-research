"""Deterministic Phase 2 inventory, one-shot sampling, evidence index. No models/tools executed."""
import json,pathlib,hashlib,random,collections,csv,re,sys
P=pathlib.Path(__file__).resolve().parents[1]; ROOT=P.parents[1]; plan=json.load(open(P/'sampling_plan.json'));source=pathlib.Path(sys.argv[1]);s=source.read_text();dec=json.JSONDecoder();pos=1;meta={}
while True:
 while s[pos].isspace() or s[pos]==',':pos+=1
 k,pos=dec.raw_decode(s,pos)
 while s[pos].isspace() or s[pos]==':':pos+=1
 if k=='simulations':break
 meta[k],pos=dec.raw_decode(s,pos)
pos+=1; records=[];bytepos=len(s[:pos].encode());last=pos
while True:
 while s[pos].isspace() or s[pos]==',':pos+=1
 if s[pos]==']':break
 v,end=dec.raw_decode(s,pos); startbyte=bytepos+len(s[last:pos].encode());endbyte=startbyte+len(s[pos:end].encode());records.append({'index':len(records),'start':pos,'end':end,'start_byte':startbyte,'end_byte_exclusive':endbyte,'v':v});bytepos=endbyte;last=end;pos=end
assert json.loads(s)['info']==meta['info']
assert meta['info']['agent_info']['llm']=='openai/responses/gpt-5.6-sol'
assert meta['info']['git_commit']=='fc0055dc4e0a316c3f83133267fbd6faaa770992'
(P/'raw/source_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2))
def information(n):return n.startswith(('KB_search','shell','get_','list_','find_','search_'))
def features(v):
 calls=[];errors=[];tool_returns=[]
 for i,m in enumerate(v['messages'],1):
  for c in m.get('tool_calls') or []:calls.append({'event':i,'actor':c.get('requestor') or m['role'],'name':c['name'],'id':c['id'],'effective_tool_name':(c.get('arguments') or {}).get('agent_tool_name',(c.get('arguments') or {}).get('discoverable_tool_name',c['name']))})
  if m['role']=='tool':
   tool_returns.append((i,m.get('id')))
   if m.get('error') or re.match(r'^\s*error\b',m.get('content') or '',re.I): errors.append({'event':i,'actor':m.get('requestor'),'error_field':m.get('error'),'text_prefix':(m.get('content') or '')[:180]})
 a=[x for x in calls if x['actor']=='assistant'];u=[x for x in calls if x['actor']=='user'];inf=[x for x in a if information(x['name'])];non=[x for x in a if not information(x['name'])];transfer=[x for x in a if 'transfer' in x['name']];disc=[x for x in a if 'unlock_discoverable' in x['name'] or 'call_discoverable' in x['name']]
 changes=[{'previous_event':x['event'],'event':y['event'],'from':x['name'],'to':y['name']} for x,y in zip(a,a[1:]) if x['name']!=y['name']]
 lookup={x['id']:x for x in calls};issues=[]
 if len(lookup)!=len(calls):issues.append('duplicate_call_id')
 for i,tid in tool_returns:
  if tid not in lookup or lookup[tid]['event']>=i:issues.append('unmatched_or_early_return_E'+str(i))
 for c in calls:
  if c['id'] not in [x[1] for x in tool_returns]:issues.append('missing_return_E'+str(c['event']))
 return {'calls':calls,'agent':a,'user':u,'information':inf,'noninformation':non,'transfer':transfer,'discovery':disc,'errors':errors,'changes':changes,'integrity_issues':issues}
def eligible(v):return bool(v.get('messages')) and isinstance((v.get('reward_info') or {}).get('reward'),(int,float)) and bool(v.get('termination_reason')) and v['termination_reason']!='infrastructure_error'
bytask=collections.defaultdict(list)
for r in records:
 if eligible(r['v']):bytask[r['v']['task_id']].append(r)
representatives={tid:sorted(rs,key=lambda r:(r['v']['trial'],r['index']))[0] for tid,rs in bytask.items() if tid not in plan['phase1_excluded_task_ids']}
base=random.Random(plan['seed']).sample(sorted(representatives),min(30,len(representatives))); selected=[(x,'random_base',None) for x in base]; used=set(base); stratum_log=[]
F={tid:features(r['v']) for tid,r in representatives.items()}
def belongs(f,cat):
 return {'execution_change':bool(f['transfer']) or len(set(x['name'] for x in f['noninformation']))>=2,'feedback_error':bool(f['errors']),'tool_discovery':bool(f['discovery']),'action_sequence':len(f['noninformation'])>=3,'information_sequence':len(f['information'])>=6}[cat]
for st in plan['target_strata']:
 cat=st['id'];pool=[tid for tid in sorted(representatives) if tid not in used and belongs(F[tid],cat)]; chosen=[]
 for outcome in [1,0]:
  cand=[tid for tid in pool if representatives[tid]['v']['reward_info']['reward']==outcome]
  cand.sort(key=lambda tid:hashlib.sha256(f'{plan["seed"]}|{cat}|{tid}'.encode()).hexdigest());chosen+=cand[:2]
 stratum_log.append({'stratum':cat,'available_task_ids':pool,'selected_task_ids':chosen,'available_by_reward':dict(collections.Counter(str(representatives[x]['v']['reward_info']['reward']) for x in pool))}); selected.extend((tid,'targeted',cat) for tid in chosen);used.update(chosen)
assert len(selected)<=50 and len(used)==len(selected)
inventory={'transport_bundle_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'total_simulations':len(records),'task_specifications':len(meta['tasks']),'distinct_observed_task_ids':len(set(r['v']['task_id'] for r in records)),'eligible_published_terminal_runs':sum(eligible(r['v']) for r in records),'eligible_independent_tasks_before_phase1_exclusion':len(bytask),'eligible_independent_tasks_after_phase1_exclusion':len(representatives),'reward_basis_counts':dict(collections.Counter('+'.join((r['v'].get('reward_info') or {}).get('reward_basis',[])) or 'unscored' for r in records)),'trial_counts':dict(collections.Counter(str(r['v']['trial']) for r in records)),'termination_counts':dict(collections.Counter(str(r['v']['termination_reason']) for r in records)),'reward_counts':dict(collections.Counter(str((r['v'].get('reward_info') or {}).get('reward')) for r in records)),'records':[{'source_index':r['index'],'id':r['v']['id'],'task_id':r['v']['task_id'],'trial':r['v']['trial'],'message_count':len(r['v']['messages']),'reward':(r['v'].get('reward_info') or {}).get('reward'),'termination':r['v']['termination_reason'],'eligible':eligible(r['v'])} for r in records]}
(P/'evidence/inventory.json').write_text(json.dumps(inventory,indent=2))
rows=[]; samples=[];fragments={};tasks={t['id']:t for t in meta['tasks']}
for tid,group,stratum in selected:
 r=representatives[tid];v=r['v'];f=F[tid];sid=tid+'_trial'+str(v['trial']);raw=s[r['start']:r['end']].encode(); (P/'raw'/f'{sid}.json').write_bytes(raw);score=v['reward_info'];task=tasks[tid]
 goal=next((m.get('content') for m in v['messages'] if m['role']=='user' and m.get('content')),None)
 text=f'# {sid}\n\nPhase 2 / {group}; published reward={score["reward"]}. E numbers preserve original messages order. Historical tool commands are text, never executed.\n\n## Analyst-only task specification (not presumed visible to agent)\n\n``````json\n'+json.dumps(task,ensure_ascii=False,indent=2)+'\n``````\n\n## Complete published messages\n'
 for i,msg in enumerate(v['messages'],1):
  text+=f'\n<a id="e{i}"></a>\n\n### E{i} — {msg["role"]}\n\n'
  if msg.get('content') is not None:text+='~~~~~~~~text\n'+str(msg['content'])+'\n~~~~~~~~\n\n'
  if msg.get('tool_calls'):text+='工具调用（正文；执行者见 requestor）：\n\n~~~~~~~~json\n'+json.dumps(msg['tool_calls'],ensure_ascii=False,indent=2)+'\n~~~~~~~~\n\n'
  text+='<details><summary>完整原始字段（含未假设对 Agent 可见的 raw_data）</summary>\n\n``````json\n'+json.dumps(msg,ensure_ascii=False,indent=2)+'\n``````\n\n</details>\n'

 text+='\n## Outcome and run metadata (hindsight)\n\n``````json\n'+json.dumps({k:x for k,x in v.items() if k!='messages'},ensure_ascii=False,indent=2)+'\n``````\n';(P/'readable'/f'{sid}.md').write_text(text)
 events=[]
 def routed_to_agent(msg):
  return msg['role']=='assistant' or (msg['role']=='tool' and msg.get('requestor')=='assistant') or (msg['role']=='user' and not msg.get('tool_calls'))
 routed=[j for j,msg in enumerate(v['messages'],1) if routed_to_agent(msg)]
 private_user=[j for j,msg in enumerate(v['messages'],1) if (msg['role']=='user' and msg.get('tool_calls')) or (msg['role']=='tool' and msg.get('requestor')=='user')]
 for key in ['information','noninformation','transfer','discovery','errors','changes']:
  for x in f[key]:events.append({'cue':key,**x,'recorded_chronological_prefix':f'E1..E{x["event"]-1}','agent_routed_history_events_before_event':[j for j in routed if j<x['event']],'user_private_events_before_event':[j for j in private_user if j<x['event']],'event_visibility':'user_private_log_not_direct_agent_input' if x['event'] in private_user else 'agent_or_shared_exchange_content_only','visibility_basis':'Static runtime-commit orchestrator.step routing; excludes raw_data private reasoning; not a reconstructed provider request','raw_pointer':f'/messages/{x["event"]-1}','link':f'readable/{sid}.md#e{x["event"]}','hindsight_not_online':'reward_info and task.evaluation_criteria are analyst-only','causal_claim':False})
 fragments[sid]={'candidate_events':events,'uncategorized_message_events':[i for i in range(1,len(v['messages'])+1) if i not in {e['event'] for e in events}],'agent_routed_event_ids':routed,'user_private_event_ids':private_user,'note':'Tool-name changes include parallel calls in the same message; not necessarily temporal replanning. Proxy categories are overlapping and incomplete.'}
 usage={actor:collections.Counter() for actor in ['assistant','user']};usage_counts=collections.Counter()
 for msg in v['messages']:
  actor=msg['role']
  if actor in usage and isinstance(msg.get('usage'),dict):
   usage_counts[actor]+=1
   for k,x in msg['usage'].items():
    if isinstance(x,(int,float)):usage[actor][k]+=x
 row={'sample_id':sid,'sample_group':group,'target_stratum':stratum or '', 'task_id':tid,'trial':v['trial'],'source_index':r['index'],'observed_user_goal':' '.join((goal or '').split())[:380],'reward':score['reward'],'hindsight_expected_action_names':json.dumps([a['name'] for a in task.get('evaluation_criteria',{}).get('actions',[])],ensure_ascii=False),'hindsight_task_spec_path':'raw/source_metadata.json#/tasks/'+str(meta['tasks'].index(task)),'agent_routed_event_ids':','.join('E'+str(j) for j in routed),'user_private_event_ids':','.join('E'+str(j) for j in private_user),'reward_basis':','.join(score['reward_basis']),'message_count':len(v['messages']),'agent_tool_calls':len(f['agent']),'user_tool_calls':len(f['user']),'agent_tool_types':json.dumps(dict(collections.Counter(x['name'] for x in f['agent'])),ensure_ascii=False),'agent_effective_tool_types':json.dumps(dict(collections.Counter(x['effective_tool_name'] for x in f['agent'])),ensure_ascii=False),'user_tool_types':json.dumps(dict(collections.Counter(x['name'] for x in f['user'])),ensure_ascii=False),'tool_error_events':json.dumps(f['errors'],ensure_ascii=False),'information_proxy_events':','.join('E'+str(x['event']) for x in f['information']),'other_action_events':','.join('E'+str(x['event']) for x in f['noninformation']),'tool_name_changes':json.dumps(f['changes'],ensure_ascii=False),'agent_cost_published':v.get('agent_cost'),'user_cost_published':v.get('user_cost'),'duration_published':v.get('duration'),'agent_usage_sum':json.dumps(usage['assistant']),'user_usage_sum':json.dumps(usage['user']),'usage_message_counts':json.dumps(usage_counts),'termination':v['termination_reason'],'integrity_issues':json.dumps(f['integrity_issues']),'raw_path':f'raw/{sid}.json','readable_path':f'readable/{sid}.md'};rows.append(row)
 samples.append({'sample_id':sid,'group':group,'target_stratum':stratum,'task_id':tid,'trial':v['trial'],'seed':v['seed'],'source_index':r['index'],'source_json_pointer':f'/simulations/{r["index"]}','source_bytes_inclusive':[r['start_byte'],r['end_byte_exclusive']-1],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'event_count':len(v['messages']),'reward':score['reward'],'reward_basis':score['reward_basis'],'integrity_issues':f['integrity_issues'],'raw_file':row['raw_path'],'readable_file':row['readable_path']})
manifest={'artifact_base_directory':str(P),'benchmark':'Sierra banking_knowledge v1.0.1','model':meta['info']['agent_info'],'user_model':meta['info']['user_info']['llm'],'runtime_commit':meta['info']['git_commit'],'global_seed':meta['info']['seed'],'sampling_plan':plan,'sampling_plan_sha256':hashlib.sha256((P/'sampling_plan.json').read_bytes()).hexdigest(),'sampling_freeze_commit':'0d01cf6','source':json.load(open(P/'evidence/acquisition.json')),'inventory_summary':{k:v for k,v in inventory.items() if k!='records'},'task_representatives':[{'task_id':tid,'source_index':r['index'],'trial':r['v']['trial']} for tid,r in sorted(representatives.items())],'stratum_sampling':stratum_log,'samples':samples,'license':'Source repository MIT; independent S3 redistribution license unverified; raw and readable retained locally','base_outcomes':dict(collections.Counter(str(x['reward']) for x in samples if x['group']=='random_base')),'target_outcomes':dict(collections.Counter(str(x['reward']) for x in samples if x['group']=='targeted')),'limitations':['Historical snapshot only; no causal alternatives','Earliest eligible trial bias','Mechanical candidate cues are not true root-cause or information-value labels','Full transport fetched for inventory; only selected records exported as research samples']}
(P/'PHASE2_SAMPLE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');(P/'evidence/decision_fragments.json').write_text(json.dumps(fragments,ensure_ascii=False,indent=2))
with (P/'PHASE2_TRAJECTORY_INDEX.csv').open('w',newline='') as out:
 w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps({'inventory':{k:v for k,v in inventory.items() if k!='records'},'samples':len(samples),'base':manifest['base_outcomes'],'target':manifest['target_outcomes'],'strata':[(x['stratum'],len(x['available_task_ids']),len(x['selected_task_ids'])) for x in stratum_log]},indent=2))
