"""Synthetic policy, real ALFWorld; never a real-model result."""
import pathlib,sys,os,json,dataclasses
R=pathlib.Path('/home/hly/agent-research');sys.path[:0]=[str(R/'calibration-is-not-control/src'),str(R/'calibration-is-not-control/scripts')]
os.environ['ALFWORLD_DATA']=str(R/'data/alfworld-cinc-audit')
import collect_alfworld_branches as c
import oversight_branching.alfworld_text as a
from oversight_branching.local_llm import GenerationOutput
class SyntheticModel:
 def generate_batch(self,prompts,**kwargs):
  return [GenerationOutput(p,'CONFIDENCE: 50' if 'CONFIDENCE:' in p else 'PLAN: inspect room\nREFLECTION: inspect\nACTION: look') for p in prompts]
model=SyntheticModel();out=R/'experiments/cinc_smoke_20261016'
m=json.loads((out/'task_manifest.json').read_text());game=m['train'][0]
candidates=c.rollout_base_prefix_candidates(model,[game],'SYNTHETIC_POLICY',2,3,24)
results={'label':'SYNTHETIC POLICY / REAL ENVIRONMENT','prefix_indices':[v['prefix'].step_index for v in candidates],'modes':{}}
for mode in ['expert_defer','llm_verify','self_reflect_retry','self_replan','self_plan_replan']:
 rows,matches=c.build_rows(model,candidates,1,8,24,24,.05,1.,.01,3,mode,2,-1,0.,13)
 results['modes'][mode]={'rows':len(rows),'matches':matches,'outcomes':[{k:r[k] for k in ['continue_correct','verify_correct','continue_branch_steps','verify_branch_steps','u_continue','u_verify']} for r in rows]}
bad=dict(candidates[0]);bad['prefix']=dataclasses.replace(bad['prefix'],observation='INTENTIONALLY WRONG OBSERVATION')
rows,matches=c.build_rows(model,[bad],1,8,24,24,.05,1.,.01,3,'llm_verify',2,-1,0.,13)
assert len(rows)==1 and matches==0 and not rows[0]['replay_matches_prefix']
results['mismatch_retained']={'row_count':len(rows),'match_count':matches}
# Actual available instances and instance identity overlap, without calling these semantic-task guarantees.
sets={s:set(pathlib.Path(g).parent.name for g in gs) for s,gs in m.items()}
results['instance_id_overlap']={f'{s}/{t}':len(sets[s]&sets[t]) for s,t in [('train','valid_seen'),('train','valid_unseen'),('valid_seen','valid_unseen')]}
results['selected_minimal_games']={s:gs[:n] for (s,gs),n in zip(m.items(),[2,2,2])}
(out/'extra_results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
