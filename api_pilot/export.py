"""Read-only conversion of recorded events; no model calls."""
import argparse
import json
from pathlib import Path


def export(folder):
    folder=Path(folder)
    events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines()]
    summary=json.loads((folder/'summary.json').read_text())
    states={};histories={};descs={};first_base={};responses={};pending=None;rows=[]
    for e in events:
        identity=(e.get('phase'),e.get('task_id'))
        key=(*identity,e.get('role'))
        kind=e['kind']
        if kind=='task_start':descs[identity]=e['task_description']
        elif kind=='generation_response':responses[e['request_id']]=e
        elif kind=='parsed_action':pending=responses.get(e['request_id'])
        elif kind=='reset':states[key]=e['state'];histories[key]=[]
        elif kind=='step':
            history=histories[key];before=states[key];role=e['role']
            reused=role=='continue' and not history
            source=None if role=='verify' else first_base.get(identity) if reused else pending
            if role in ('base','smoke') and not history:first_base[identity]=source
            row={'record_type':'environment_step','phase':identity[0],'task_id':identity[1],
                 'split':e.get('split'),'branch':role,'step':len(history)+1,
                 'task_description':descs.get(identity),'history_prefix':list(history),
                 'observation_before':before['observation'],'admissible_commands':before['admissible_commands'],
                 'raw_model_output':source['text'] if source else None,'action':e['action'],
                 'observation_after':e['state']['observation'],'done':e['state']['done'],'won':e['state']['won'],
                 'request_id':source['request_id'] if source else None,
                 'usage':source['usage'] if source and not reused else None,
                 'source_usage':source['usage'] if source else None,'new_request_for_step':bool(source and not reused),
                 'latency_seconds':source['latency_seconds'] if source and not reused else None,
                 'action_origin':'oracle_planner' if role=='verify' else 'reused_base_proposal' if reused else 'llm',
                 'estimated_usd':(source['usage']['prompt_tokens']*.00000015+source['usage']['completion_tokens']*.0000006) if source and not reused else 0}
            rows.append(row);history.append({'action':e['action'],'observation':e['state']['observation']})
            states[key]=e['state'];pending=None
    for row in rows:
        state=states[(row['phase'],row['task_id'],row['branch'])]
        row['trajectory_won']=state['won']
        row['trajectory_stop_reason']='won' if state['won'] else 'budget_exhausted' if state['remaining_budget']<=0 else 'environment_done' if state['done'] else summary.get('stop_reason','branch_stopped')
    with (folder/'trajectories.jsonl').open('x') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    with (folder/'requests.jsonl').open('x') as f:
        for row in responses.values():f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return {'steps':len(rows),'successful_responses':len(responses),'trajectories':len(states)}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');print(json.dumps(export(p.parse_args().folder)))
