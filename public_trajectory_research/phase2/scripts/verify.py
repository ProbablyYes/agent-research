import pathlib,json,hashlib,csv,re,random,collections,math
P=pathlib.Path(__file__).resolve().parents[1];m=json.load(open(P/'PHASE2_SAMPLE_MANIFEST.json'));inv=json.load(open(P/'evidence/inventory.json'));plan=json.load(open(P/'sampling_plan.json'));summary={};failures=[]
assert hashlib.sha256((P/'sampling_plan.json').read_bytes()).hexdigest()==m['sampling_plan_sha256']=='bcc977681dea4dc83cefb2ec7289750e6200cd19073e68761bcac588a38f6558'
assert hashlib.sha256((P/'raw/source_bundle.json').read_bytes()).hexdigest()==m['source']['bundle_sha256']
reps={}
for r in inv['records']:
 if r['eligible'] and r['task_id'] not in plan['phase1_excluded_task_ids']:
  k=r['task_id']; key=(r['trial'],r['source_index'])
  if k not in reps or key<(reps[k]['trial'],reps[k]['source_index']):reps[k]=r
expected=random.Random(plan['seed']).sample(sorted(reps),30);assert expected==[s['task_id'] for s in m['samples'] if s['group']=='random_base']
assert len(m['samples'])<=50 and len(set(s['task_id'] for s in m['samples']))==len(m['samples']);assert not set(s['task_id'] for s in m['samples'])&set(plan['phase1_excluded_task_ids'])
index={r['sample_id']:r for r in csv.DictReader(open(P/'PHASE2_TRAJECTORY_INDEX.csv'))};agentcalls=usercalls=messagecount=0
with (P/'raw/source_bundle.json').open('rb') as source:
 for row in m['samples']:
  b=(P/row['raw_file']).read_bytes();a,z=row['source_bytes_inclusive'];source.seek(a);assert source.read(z-a+1)==b;assert hashlib.sha256(b).hexdigest()==row['sha256'];v=json.loads(b)
  text=(P/row['readable_file']).read_text();blocks=[json.loads(x) for x in re.findall(r'``````json\n(.*?)\n``````',text,re.S)];assert blocks[1:-1]==v['messages'];assert blocks[-1]=={k:x for k,x in v.items() if k!='messages'}
  assert len(v['messages'])==row['event_count']==int(index[row['sample_id']]['message_count']);assert not row['integrity_issues'];messagecount+=len(v['messages'])
  for msg in v['messages']:
   for c in msg.get('tool_calls') or []:
    actor=c.get('requestor') or msg['role'];assert actor in ['assistant','user'];agentcalls+=actor=='assistant';usercalls+=actor=='user'
  ri=v['reward_info'];basis=ri['reward_basis'];assert ri['reward']==math.prod(ri['reward_breakdown'][b] for b in basis),basis
  for e in json.load(open(P/'evidence/decision_fragments.json'))[row['sample_id']]['candidate_events']:assert 1<=e['event']<=len(v['messages'])
# Count integrity across all published terminal runs separately from research samples.
data=json.load(open(P/'raw/source_bundle.json'));global_bad=[]
for i,v in enumerate(data['simulations']):
 if not inv['records'][i]['eligible']:continue
 calls={c['id']:n for n,msg in enumerate(v['messages']) for c in msg.get('tool_calls') or []};returns=[(n,msg['id']) for n,msg in enumerate(v['messages']) if msg['role']=='tool'];bad=any(tid not in calls or calls[tid]>=n for n,tid in returns) or set(calls)!=set(tid for n,tid in returns)
 if bad:global_bad.append(i)
# Independent targeted draw from frozen task representatives and predicates.
used=set(expected);target_expected=[]
for st in plan['target_strata']:
 cat=st['id'];pool=[]
 for tid,r in sorted(reps.items()):
  if tid in used:continue
  vv=data['simulations'][r['source_index']];names=[c['name'] for msg in vv['messages'] for c in msg.get('tool_calls') or [] if (c.get('requestor') or msg['role'])=='assistant']
  info=lambda n:n.startswith(('KB_search','shell','get_','list_','find_','search_'))
  non=[n for n in names if not info(n)]
  error=any(msg['role']=='tool' and (msg.get('error') or re.match(r'^\s*error\b',msg.get('content') or '',re.I)) for msg in vv['messages'])
  hit={'execution_change':any('transfer' in n for n in names) or len(set(non))>=2,'feedback_error':error,'tool_discovery':any('unlock_discoverable' in n or 'call_discoverable' in n for n in names),'action_sequence':len(non)>=3,'information_sequence':sum(info(n) for n in names)>=6}[cat]
  if hit:pool.append(tid)
 chosen=[]
 for outcome in [1,0]:
  candidates=[tid for tid in pool if data['simulations'][reps[tid]['source_index']]['reward_info']['reward']==outcome]
  chosen+=sorted(candidates,key=lambda tid:hashlib.sha256(f'{plan["seed"]}|{cat}|{tid}'.encode()).hexdigest())[:2]
 target_expected.extend(chosen);used.update(chosen)
 recorded=next(x for x in m['stratum_sampling'] if x['stratum']==cat);assert pool==recorded['available_task_ids'] and chosen==recorded['selected_task_ids']
assert target_expected==[x['task_id'] for x in m['samples'] if x['group']=='targeted']
for sid,entry in json.load(open(P/'evidence/decision_fragments.json')).items():
 assert not set(entry['agent_routed_event_ids'])&set(entry['user_private_event_ids'])
 for e in entry['candidate_events']:
  assert all(x<e['event'] for x in e['agent_routed_history_events_before_event'])
  assert not set(e['agent_routed_history_events_before_event'])&set(e['user_private_events_before_event'])

phase1=pathlib.Path('public_trajectory_research/phase1');old=json.load(open(phase1/'TRAJECTORY_SAMPLE_MANIFEST.json'));assert all(hashlib.sha256((phase1/s['raw_file']).read_bytes()).hexdigest()==s['sha256'] for s in old['samples'])
summary={'status':'PASS','samples':len(m['samples']),'random_base':30,'targeted':len(m['samples'])-30,'messages':messagecount,'agent_tool_calls':agentcalls,'user_tool_calls':usercalls,'whole_bundle_terminal_tool_link_issues':global_bad,'phase1_sample_hashes_unchanged':True,'checks':['frozen_plan_sha256','whole_bundle_sha256','independent_random_draw_reproduction','independent_targeted_draw_reproduction','visible_private_prefix_separation','unique_tasks_and_phase1_exclusion','exact_source_bytes_per_sample','sha256_per_sample','complete_render_roundtrip','CSV_event_counts','actor_attribution','published_reward_breakdown_consistency_not_reexecution','candidate_event_bounds','whole_bundle_tool_link_inventory']}
(P/'evidence/verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
