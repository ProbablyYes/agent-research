"""Audited cloud Agent engineering round. No original files are modified."""
import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import random
import re
import subprocess

import cloudpickle
import numpy as np
from pilot_validity.core import (ROOT, AuditSession, Recorder, original, policy, sha, dump,
                                digest, freeze_baselines, evaluate_frozen, valid_rows, independent_metrics)
from pilot_validity.run import validate_plan as validate_local, check_upstream
from oversight_branching.local_llm import GenerationOutput
from .budget import Ledger, Halt, strict_action, guarded_call, MODEL, ENDPOINT, ROUND_ID

LOCAL_PLAN=ROOT/'pilot_validity/plans/real_pilot_final/plan.json'
PLAN=ROOT/'api_pilot/plans/round_20261020_authorized/plan.json'
OUTPUT=ROOT/'experiments/api_agent_round_20261020'


def validate():
    base=validate_local(LOCAL_PLAN)
    plan=json.loads(PLAN.read_text())
    if sha(PLAN)!=json.loads(PLAN.with_name('plan.sha256.json').read_text())['sha256']:
        raise Halt('plan_digest')
    if plan['tasks']!=base['tasks'] or plan['config']!=base['config']:
        raise Halt('plan_tasks_or_config_changed')
    for file,expected in plan['api_source_sha256'].items():
        if sha(ROOT/file)!=expected: raise Halt('api_source_changed')
    if plan['model']['name']!=MODEL or plan['model']['endpoint']!=ENDPOINT:
        raise Halt('model_changed')
    return plan


class EventLog:
    def __init__(self, output):
        self.file=(output/'events.jsonl').open('x')
        self.context={}
    def __call__(self,event):
        self.file.write(json.dumps({**self.context,**event},ensure_ascii=False,allow_nan=False)+'\n')
        self.file.flush();os.fsync(self.file.fileno())
    def close(self): self.file.close()


class CloudModel:
    def __init__(self, ledger, sink, phase, transport=None, credential_reader=None):
        self.ledger,self.sink,self.phase=ledger,sink,phase
        self.transport,self.credential_reader=transport,credential_reader
        self.sequence=ledger.summary()['request_reservations']
        self.last=None
    def generate_batch(self,prompts,batch_size=1,max_new_tokens=24,assistant_prefix=None,stop=None):
        outputs=[]
        for prompt in prompts:
            rendered=prompt + ('\nRespond starting with: '+assistant_prefix if assistant_prefix else '')
            payload={'model':MODEL,'messages':[{'role':'user','content':rendered}],
                     'temperature':0,'max_tokens':max_new_tokens,'stream':False}
            if stop is not None:payload['stop']=stop
            rid=f'{self.phase}:{self.sequence:04d}';self.sequence+=1
            self.sink({'kind':'generation_request','request_id':rid,'payload':payload})
            kwargs={}
            if self.transport is not None:kwargs['transport']=self.transport
            if self.credential_reader is not None:kwargs['credential_reader']=self.credential_reader
            try:
                result=guarded_call(self.ledger,rid,self.phase,payload,**kwargs)
            except Halt:
                row=self.ledger.db.execute('SELECT evidence FROM observations WHERE request_id=?',(rid,)).fetchone()
                if row:self.sink({'kind':'failed_response','request_id':rid,**json.loads(row[0])})
                raise
            self.last={'request_id':rid,**result}
            self.sink({'kind':'generation_response',**self.last})
            if assistant_prefix:
                match=re.fullmatch(r'\s*CONFIDENCE:\s*(\d+(?:\.\d+)?)\s*',result['text'])
                if not match or not 0<=float(match.group(1))<=100:
                    self.ledger.halt('confidence_parse_failure');raise Halt('confidence_parse_failure')
            outputs.append(GenerationOutput(prompt,result['text']))
        return outputs


@contextlib.contextmanager
def strict_parser(model,sink):
    previous=original.extract_action
    def parse(text,commands):
        try:action=strict_action(text,commands)
        except Halt:
            model.ledger.halt('action_parse_failure')
            sink({'kind':'action_parse_failure','raw_model_output':text,'admissible_commands':commands})
            raise
        sink({'kind':'parsed_action','action':action,'request_id':model.last['request_id'] if model.last else None})
        return action
    original.extract_action=parse
    try:yield
    finally:original.extract_action=previous


def smoke(model, task, config, sink):
    actions,observations=[],[]
    desc=original.load_task_description(task['gamefile'])
    sink({'kind':'task_start','task_description':desc,'task':task})
    raw=original.make_single_game_env(task['gamefile'],max_episode_steps=config['max_episode_steps'])
    env=Recorder(raw,task['gamefile'],config['max_episode_steps'],'smoke',sink)
    try:
        obs,commands,won,_=original.unwrap_reset(env.reset())
        done=False
        while not done and not won and len(actions)<config['max_episode_steps']:
            prompt=original.build_continue_prompt(desc,obs,original.history_to_text(actions,observations),commands)
            result=model.generate_batch([prompt],max_new_tokens=config['action_max_tokens'])[0]
            action=original.extract_action(result.text,commands)
            obs,_,done,won,commands,_=original.unwrap_step(env.step([action]))
            actions.append(action);observations.append(obs)
        return {'won':bool(won),'steps':len(actions),'protocol_passed':True,
                'stop_reason':'won' if won else 'budget_exhausted' if len(actions)>=config['max_episode_steps'] else 'environment_done',
                'actions':actions,'states':env.states,'task_description':desc}
    finally:env.close()


def freeze(records,output,sink):
    bundles={};controls={}
    for scope in ('valid_pairs','original_raw'):
        train,val=records['train'],records['val']
        if scope=='original_raw':
            train=[dict(r,valid_pair=True) for r in train if r['row'] is not None]
            val=[dict(r,valid_pair=True) for r in val if r['row'] is not None]
        model,c=freeze_baselines(train,val)
        eu=policy.fit_correctness_models(valid_rows(train),verify_mode='no_preview')
        bundles[scope]={'failure':model,'eu':eu,'controls':c};controls[scope]=c
    dump(output/'frozen_controls_before_test.json',controls)
    with (output/'frozen_models_before_test.pkl').open('xb') as f:cloudpickle.dump(bundles,f)
    sink({'kind':'freeze_before_test','controls_hash':digest(controls)})
    return bundles


def evaluate(bundles,records,config):
    summaries={}
    for scope,bundle in bundles.items():
        test=records['test'] if scope=='valid_pairs' else [dict(r,valid_pair=True) for r in records['test'] if r['row'] is not None]
        result=evaluate_frozen(bundle['failure'],bundle['controls'],test)
        if scope=='original_raw':
            result['scope']='UNFILTERED AUTHOR REFERENCE; not valid paired evidence'
            result['eligible_for_paired_claims']=False
            result['audit_valid']=sum(r['valid_pair'] for r in records['test'])
            result['audit_invalid']=sum(not r['valid_pair'] for r in records['test'])
        rows=valid_rows(test)
        if rows:
            x=policy.feature_matrix(rows)
            probabilities=[m.predict_proba(x)[:,1] for m in bundle['eu']]
            utilities=[policy.expected_utility_from_probability(p,verify=bool(i),verify_cost=config['verify_cost'],wrong_penalty=config['wrong_penalty']) for i,p in enumerate(probabilities)]
            actions=policy.choose_expected_utility_actions(*utilities)
            result['original_explicit_eu']={'actions':actions,'metrics':independent_metrics(rows,actions),
                                            'future_step_cost_omitted':True,'future_realized_steps_used':False}
        summaries[scope]=result
    return summaries


def pilot(model,tasks,config,output,sink):
    records={s:[] for s in ('train','val','test')}
    bundles={}
    with AuditSession(sink).install() as audit:
        for split in records:
            for task in [t for t in tasks if t['split']==split]:
                pair=split+':'+task['task_id']+':0'
                sink.context={'phase':'pilot','split':split,'task_id':task['task_id'],'pair_id':pair}
                sink({'kind':'task_start','task':task,'task_description':original.load_task_description(task['gamefile'])})
                audit.pair_id,audit.phase=pair,'base'
                try:
                    candidates=original.rollout_base_prefix_candidates(model,[task['gamefile']],split,1,config['max_episode_steps'],config['action_max_tokens'])
                    if len(candidates)!=1 or candidates[0]['prefix'].step_index!=0:raise Halt('checkpoint_missing')
                    # Preserve link to the first base proposal reused for Continue (no second API charge).
                    sink({'kind':'base_complete','candidate_action':candidates[0]['continue_action']})
                    audit.phase='branches'
                    kwargs={k:config[k] for k in ['batch_size','confidence_max_tokens','verify_max_tokens','action_max_tokens',
                           'verify_cost','wrong_penalty','step_cost','max_episode_steps','intervention_mode',
                           'repair_horizon','expert_max_policy_steps','expert_noise_rate']}
                    kwargs['seed']=config['seed']+{'train':0,'val':1000,'test':2000}[split]
                    rows,_=original.build_rows(model,candidates,**kwargs)
                    record=audit.paired_record(rows[0],config)
                except BaseException:
                    record={'pair_id':pair,'row':None,'valid_pair':False,'invalid_reasons':[{'reason':'execution_stopped_see_events'}]}
                    dump(output/(pair.replace(':','_')+'.json'),record)
                    records[split].append(record)
                    dump(output/'partial_records.json',records)
                    raise
                records[split].append(record)
                dump(output/(pair.replace(':','_')+'.json'),record)
                sink({'kind':'pair_complete','valid':record['valid_pair'],'recomputed':record['recomputed']})
                print(pair,'valid='+str(record['valid_pair']),flush=True)
            dump(output/(split+'_records.json'),records[split])
            raw=[r['row'] for r in records[split] if r['row'] is not None]
            if raw:original.save_rows(raw,output/'original_raw'/(split+'_rows.csv'))
            if split=='val':bundles=freeze(records,output,sink)
    return {'by_split':{s:{'attempted':len(rs),'valid':sum(r['valid_pair'] for r in rs),'invalid':sum(not r['valid_pair'] for r in rs)} for s,rs in records.items()},
            'evaluation':evaluate(bundles,records,config),'native_state_equivalence_proven':False,
            'no_resampling':True,'llm_usd_in_task_utility':False}


def run(phase):
    plan=validate();ledger=Ledger()
    if ledger.summary()['halted'] or ledger.summary()['unresolved_requests']:
        ledger.close();raise Halt('ledger_blocked')
    if phase=='pilot':
        prior=json.loads((OUTPUT/'smoke/summary.json').read_text())
        if not prior.get('protocol_passed') or not prior.get('execution_complete'):raise Halt('smoke_not_passed')
    output=OUTPUT/phase;output.mkdir(parents=True,exist_ok=False)
    dump(output/'plan.json',plan)
    random.seed(plan['config']['seed']);np.random.seed(plan['config']['seed'])
    sink=EventLog(output);sink.context={'phase':phase}
    model=CloudModel(ledger,sink,phase)
    result={}
    try:
        with strict_parser(model,sink):
            if phase=='smoke':
                sink.context.update(split='train',task_id=plan['tasks'][0]['task_id'])
                result=smoke(model,plan['tasks'][0],plan['config'],sink)
            else:result=pilot(model,plan['tasks'],plan['config'],output,sink)
        result['execution_complete']=True
    except BaseException as exc:
        reason=str(exc) if type(exc) is Halt and re.fullmatch('[a-z_]+',str(exc)) else 'environment_or_execution_error'
        ledger.halt(reason)
        result={'execution_complete':False,'protocol_passed':False,'stop_reason':reason,'error_type':type(exc).__name__}
        sink({'kind':'round_stopped',**result})
    finally:
        result['budget']=ledger.summary()
        dump(output/'summary.json',result)
        sink({'kind':'phase_end','summary':result});sink.close();ledger.close();check_upstream()
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    if not result['execution_complete']:raise SystemExit(2)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['smoke','pilot'])
    run(parser.parse_args().phase)
