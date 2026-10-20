"""Post-run evidence checks. Read-only inputs; never invokes a model."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT=Path('/home/hly/agent-research')
RUN=ROOT/'experiments/api_agent_round_20261020'
OUT=ROOT/'reports/evidence/api_authorized_20261020'
all_events=[];phases={}
for phase in ('smoke','pilot'):
    folder=RUN/phase
    if not folder.exists():continue
    events=[json.loads(x) for x in (folder/'events.jsonl').read_text().splitlines()]
    summary=json.loads((folder/'summary.json').read_text())
    rows=[json.loads(x) for x in (folder/'trajectories.jsonl').read_text().splitlines()]
    phases[phase]={'summary':summary,'environment_steps':len(rows),
                   'trajectory_count':len({(r['task_id'],r['branch']) for r in rows}),
                   'successful_responses':sum(e['kind']=='generation_response' for e in events)}
    all_events+=events
responses={e['request_id']:e for e in all_events if e['kind']=='generation_response'}
assert len(responses)==sum(e['kind']=='generation_response' for e in all_events)
db=sqlite3.connect('file:/home/hly/.config/agent-research/api-agent-20261020.sqlite3?mode=ro',uri=True)
requests=db.execute('SELECT request_id,phase,reserve_nano,max_tokens,state,result,estimated_nano FROM requests ORDER BY rowid').fetchall()
contract,halted=db.execute('SELECT contract,halted FROM meta').fetchone();contract=json.loads(contract)
complete=[r for r in requests if r[4]=='completed'];unknown=[r for r in requests if r[4]!='completed']
assert {r[0] for r in complete}==set(responses)
input_tokens=output_tokens=estimated=0
for rid,phase,reserved,limit,state,raw,cost in complete:
    result=json.loads(raw);u=result['usage']
    assert u==responses[rid]['usage']
    assert result['text']==responses[rid]['text']
    assert u['total_tokens']==u['prompt_tokens']+u['completion_tokens']
    assert u['completion_tokens']<=limit<=64
    assert cost==u['prompt_tokens']*150+u['completion_tokens']*600<=reserved
    input_tokens+=u['prompt_tokens'];output_tokens+=u['completion_tokens'];estimated+=cost
committed=estimated+sum(r[2] for r in unknown)
assert committed<=3000000000 and len(requests)<=400
pairs=[]
for file in sorted((RUN/'pilot').glob('*trial*.json')):
    record=json.loads(file.read_text());row=record['row']
    if row:
        for role in ('continue','verify'):
            branch=record['branches'][role]
            n=len(branch['actions'])-row['step_index']
            won=branch['states'][-1]['won']
            utility=(1 if won else -1)-n*.01-(.05 if role=='verify' else 0)
            assert n==row[role+'_branch_steps']
            assert won==row[role+'_correct']
            assert math.isclose(utility,row['u_'+role],abs_tol=1e-12)
    pairs.append({'pair_id':record['pair_id'],'valid':record['valid_pair'],'recomputed':record.get('recomputed'),
                  'invalid_reasons':record['invalid_reasons']})
pilot_events=[e for e in all_events if e['phase']=='pilot']
frozen=[i for i,e in enumerate(pilot_events) if e['kind']=='freeze_before_test']
tests=[i for i,e in enumerate(pilot_events) if e['kind']=='task_start' and e['split']=='test']
if tests:
    assert len(frozen)==1 and frozen[0]<min(tests)
    controls=json.loads((RUN/'pilot/frozen_controls_before_test.json').read_text())
    digest=hashlib.sha256(json.dumps(controls,sort_keys=True,allow_nan=False).encode()).hexdigest()
    assert digest==pilot_events[frozen[0]]['controls_hash']
result={'phase_results':phases,'budget':{'attempts_reserved':len(requests),'completed':len(complete),'unknown':len(unknown),
          'input_tokens_known_completed':input_tokens,'output_tokens_known_completed':output_tokens,
          'gross_pre_send_reservations_usd':sum(r[2] for r in requests)/1e9,'estimated_usd_known_completed':estimated/1e9,
          'unknown_reserved_usd':sum(r[2] for r in unknown)/1e9,'committed_usd':committed/1e9,
          'halted':halted,'bill_verified':False,'user_accepted_nominal_accounting':contract.get('user_accepted_nominal_accounting')},
        'pairs':pairs,'valid_pairs':sum(r['valid'] for r in pairs),'invalid_pairs':sum(not r['valid'] for r in pairs),
        'pre_action_audits':sum(e['kind']=='pre_action_replay_audit' for e in pilot_events),
        'passed_pre_action_audits':sum(e['kind']=='pre_action_replay_audit' and e['passed'] for e in pilot_events),
        'freeze_event_index':frozen[0] if frozen else None,'first_test_task_event_index':min(tests) if tests else None,
        'source_commit':json.loads((RUN/'smoke/plan.json').read_text())['source_commit']}
with (OUT/'results_verified.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('phase_results','pairs')},indent=2))
