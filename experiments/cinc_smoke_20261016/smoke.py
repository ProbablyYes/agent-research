"""Zero-model smoke tests; synthetic rows are NOT research results."""
import os,sys,pathlib,json,ast,importlib,importlib.util,random,copy,traceback,csv
ROOT=pathlib.Path('/home/hly/agent-research'); REPO=ROOT/'calibration-is-not-control'; OUT=ROOT/'experiments/cinc_smoke_20261016'
sys.path[:0]=[str(REPO/'src'),str(REPO/'scripts')]
os.environ['ALFWORLD_DATA']=str(ROOT/'data/alfworld-cinc-audit')
random.seed(13)
results={}
def check(name,fn):
 try: results[name]={'status':'PASS','detail':fn()}
 except Exception: results[name]={'status':'FAIL','traceback':traceback.format_exc()}
 print(name,results[name],flush=True)
def syntax():
 files=list(REPO.rglob('*.py'))
 for p in files: ast.parse(p.read_text(),filename=str(p))
 return {'files':len(files)}
check('syntax',syntax)
def imports():
 import importlib.metadata as md
 return {m: {'version':md.version(pkg),'file':importlib.import_module(m).__file__} for m,pkg in [('numpy','numpy'),('sklearn','scikit-learn'),('alfworld','alfworld'),('textworld','textworld')]}
check('imports',imports)
def project_imports():
 return [importlib.import_module(m).__file__ for m in ['oversight_branching.alfworld_text','oversight_branching.local_llm','oversight_branching.policy_learning','collect_alfworld_branches','evaluate_controllers']]
check('project_imports',project_imports)
if results['project_imports']['status']=='PASS':
 import numpy as np
 np.random.seed(13)
 import oversight_branching.alfworld_text as a
 import oversight_branching.policy_learning as p
 import collect_alfworld_branches as c
 import evaluate_controllers as e
 def synthetic():
  dest=OUT/'SYNTHETIC'; dest.mkdir(exist_ok=True)
  rng=np.random.default_rng(13)
  allrows={}
  for split,n in [('train',48),('val',24),('test',24)]:
   rows=[]
   for i in range(n):
    cc,vc=[(True,True),(False,True),(False,False),(True,False)][i%4]
    features=a.basic_feature_vector('put apple on table','a room', ['look','open cabinet 1'],'look',i%10,i%10)+c.task_one_hot('pick_and_place_simple')
    features[2]+=float(rng.integers(0,5))
    rows.append(dict(example_id=f'SYNTHETIC:{split}:{i}',confidence=float(rng.integers(0,101)),continue_correct=cc,verify_correct=vc,u_continue=c.utility(cc,5,False,.05,1,.01),u_verify=c.utility(vc,3,True,.05,1,.01),u_quit=0.,features=features,verify_features=a.verify_feature_vector('a room',['look','open cabinet 1'],'look','open cabinet 1',i%10)+c.task_one_hot('pick_and_place_simple')))
   with (dest/f'{split}_rows.csv').open('w') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader()
    for row in rows:
     writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
   allrows[split]=rows
  (dest/'summary.json').write_text(json.dumps({'Synthetic':True,'config':{'verify_cost':.05,'wrong_penalty':1.,'step_cost':.01,'seed':13}}))
  res=e.analyze_run_dir(dest)
  (dest/'controllers.json').write_text(json.dumps(res,indent=2))
  assert res==e.analyze_run_dir(dest),'fixed seed reproducibility failed'
  x=p.feature_matrix(allrows['test']); xv=p.feature_matrix(allrows['test'],True)
  assert x.shape==(24,26) and xv.shape==(24,47)
  metrics=p.evaluate_actions(allrows['test'],['continue']*24)
  assert abs(metrics['utility']+.05)<1e-12 and metrics['success_rate']==.5 and abs(metrics['control_regret']-.755)<1e-12
  cm=p.fit_binary_classifier(x,np.zeros(24,dtype=int),0)
  mean,std=p.positive_probability_stats(cm,x); assert not mean.any() and not std.any()
  model=p.fit_failure_baseline(allrows['train']); mean,std=p.positive_probability_stats(model,x)
  assert np.allclose(std,np.std([t.predict_proba(x)[:,1] for t in model.estimators_],axis=0))
  altered=copy.deepcopy(allrows['test'])
  for row in altered: row.update(u_continue=999,u_verify=-999,continue_correct=False,verify_correct=True,continue_branch_steps=10000,verify_branch_steps=10000)
  assert np.array_equal(x,p.feature_matrix(altered)) and np.array_equal(xv,p.feature_matrix(altered,True))
  return {'rows':{k:len(v) for k,v in allrows.items()},'base_shape':list(x.shape),'preview_shape':list(xv.shape),'hand_calculated_metrics':metrics,'repeat_identical':True,'future_fields_do_not_enter_features':True,'lcb_std_verified':True}
 check('SYNTHETIC_controllers',synthetic)
 def bug_evidence():
  # Probability utility excludes actual branch cost.
  eu=float(p.expected_utility_from_probability([1],False,.05,1)[0]); actual=c.utility(True,20,False,.05,1,.01)
  assert eu==1 and actual==.8
  # Failure threshold candidate set cannot choose continue at a constant score.
  rows=[dict(continue_correct=True,verify_correct=False,u_continue=1.,u_verify=-1.05,u_quit=0.)]*3
  best=p.threshold_search_failure_scores(np.zeros(3),rows)
  assert best['utility']==0.
  # Cost sensitive tuning may select threshold=0 under a different routing rule than evaluation.
  class Fake:
   classes_=np.array([0,1,2])
   def predict_proba(self,x): return np.tile([.30,.25,.45],(len(x),1))
  x=np.zeros((3,1)); tuned=p.threshold_search_cost_sensitive_matrix(Fake(),x,rows)
  evaluated=p.evaluate_cost_sensitive_policy_matrix_with_threshold(rows,Fake(),x,tuned['quit_confidence_threshold'])
  assert tuned['utility']==1 and evaluated['utility']==0
  return {'EU_vs_realized': [eu,actual], 'failure_constant_score_best':best,'cost_sensitive_tuned':tuned,'cost_sensitive_evaluated':evaluated,'note':'cost-sensitive helpers not called by supplied CLIs'}
 check('logic_counterexamples',bug_evidence)
 def env_tests():
  manifest={s:a.collect_gamefiles(s,list(a.TASK_TYPE_TO_ID),999999,13+j) for j,s in enumerate(['train','valid_seen','valid_unseen'])}
  assert all(manifest.values()),{s:len(v) for s,v in manifest.items()}
  (OUT/'task_manifest.json').write_text(json.dumps(manifest,indent=2))
  records=[]
  for split,games in manifest.items():
   game=games[0]; env=a.make_single_game_env(game,20,True)
   obs,commands,won,infos=a.unwrap_reset(env.reset()); initial=obs
   assert commands
   action=infos.get('policy_commands',[[]])[0][0]
   obs,r,done,won,commands,infos=a.unwrap_step(env.step([action])); env.close()
   prefix=a.AlfworldPrefix(f'{split}:smoke:1',split,game,a.load_task_description(game),a.load_task_type(game),[action],[obs],obs,commands,1)
   restored,ro,rc,rd,rw,ri=c.replay_to_prefix(prefix,20,True)
   assert c.normalize_text(ro)==c.normalize_text(obs) and rc==commands and rd==done and rw==won
   restored.close()
   expert=c.rollout_expert_branch(prefix,20,-1,0,13)
   assert expert['replay_matches_prefix']
   records.append(dict(split=split,gamefile=game,initial_observation=initial,step_action=action,reward=r,done=done,won=won,admissible_count=len(commands),policy_command_count=len(ri.get('policy_commands',[[]])[0]),expert_result=expert))
  (OUT/'env_records.json').write_text(json.dumps(records,indent=2))
  return {'eligible_games':{s:len(v) for s,v in manifest.items()},'reset_step_replay_splits':len(records),'expert_wins':[r['expert_result']['won'] for r in records]}
 if os.environ.get('CINC_SKIP_ENV') != '1':
  check('ALFWorld_reset_step_replay_expert',env_tests)
 else:
  results['ALFWorld_reset_step_replay_expert']=json.loads((OUT/'results-first.json').read_text())['ALFWorld_reset_step_replay_expert']
(OUT/'results.json').write_text(json.dumps(results,indent=2))
