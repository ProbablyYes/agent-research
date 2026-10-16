"""Independent post-run JSON/CSV verification, no generation or environment calls."""
import csv
import json
import math
from pathlib import Path
from pilot_validity.core import ROOT, original, policy, sha, independent_metrics, corrected_thresholds
from pilot_validity.run import validate_plan

root=ROOT/'experiments/pilot_validity_cpu'
run=root/'run_final'
checks={}
plan=validate_plan(ROOT/'pilot_validity/plans/real_pilot_final/plan.json')
checks['frozen_final_plan_valid']=True
all_records=[]
for split in ['train','val','test']:
    records=json.loads((run/f'{split}_records.json').read_text())
    with (run/'original_raw'/f'{split}_rows.csv').open() as f:csvrows=list(csv.DictReader(f))
    assert len(records)==len(csvrows)==2
    for record,csvrow in zip(records,csvrows):
        row=record['row'];assert record['valid_pair']
        for role in ['continue','verify']:
            branch=record['branches'][role];k=row['step_index']
            count=len(branch['actions'])-k
            assert count==branch['states'][-1]['executed_actions']-k
            assert count==int(csvrow[role+'_branch_steps'])==row[role+'_branch_steps']
            won=branch['states'][-1]['won']
            assert won==(csvrow[role+'_correct']=='True')==row[role+'_correct']
            u=(1. if won else -1.)-.01*count-(.05 if role=='verify' else 0.)
            assert math.isclose(u,float(csvrow['u_'+role]),abs_tol=1e-12)
            assert math.isclose(u,record['recomputed'][role]['realized_utility'],abs_tol=1e-12)
    all_records.extend(records)
checks['reloaded_real_environment_branch_outcomes_and_costs']=12
checks['valid_pairs']=len(all_records)
events=[json.loads(x) for x in (run/'events.jsonl').read_text().splitlines()]
freeze=next(i for i,e in enumerate(events) if e['kind']=='freeze_before_test')
test_games={t['gamefile'] for t in plan['tasks'] if t['split']=='test'}
first_test=min(i for i,e in enumerate(events) if e.get('gamefile') in test_games)
assert freeze<first_test
checks['freeze_event_index']=freeze;checks['first_test_environment_event_index']=first_test
# Reproduce the author's unfiltered routing directly from saved CSVs.
from evaluate_controllers import load_rows
train=load_rows(run/'original_raw/train_rows.csv');val=load_rows(run/'original_raw/val_rows.csv');test=load_rows(run/'original_raw/test_rows.csv')
model=policy.fit_failure_baseline(train);controls=policy.threshold_search_failure(model,val)
scores=model.predict_proba(policy.feature_matrix(test))[:,1]
metrics=policy.evaluate_failure_policy(test,scores,controls['verify_threshold'],controls['quit_threshold'])
saved=json.loads((run/'summary.json').read_text())
assert saved['evaluation']['original_raw']['policies']['original']['author_metrics']==metrics
checks['author_raw_failure_result_exact_match']=True
# Saved original smoke still all PASS; output directory redirect was the only change.
smoke=json.loads((root/'reused_smoke/results.json').read_text())
assert all(v['status']=='PASS' for v in smoke.values())
checks['reused_smoke_checks_passed']=len(smoke)
# Retain a quantitative fair-baseline counterexample artifact.
rs=[dict(continue_correct=True,verify_correct=False,u_continue=.95,u_verify=-1.08,u_quit=0.)]*3
orig=policy.threshold_search_failure_scores([0.,0.,0.],rs)
fixed=corrected_thresholds(rs,[0.,0.,0.])
assert orig['utility']==0 and math.isclose(fixed['utility'],.95)
checks['constant_risk_counterexample']={'original':orig,'corrected':fixed,'validation_only':True}
with (root/'artifact_verification.json').open('x') as f:json.dump(checks,f,indent=2)
print(json.dumps(checks,indent=2))
