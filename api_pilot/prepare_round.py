"""Freeze this round and persist the unresolved billing gate; no generation calls."""
import json
from pathlib import Path
import subprocess

from pilot_validity.core import ROOT, dump, sha
from pilot_validity.run import validate_plan
from .budget import Ledger, LEDGER_PATH, BUDGET_NANO, MAX_REQUESTS, ROUND_ID
from .probe import ENDPOINT, MODEL


def main():
    evidence=ROOT/'reports/evidence/api_round_20261020'
    parent=ROOT/'pilot_validity/plans/real_pilot_final/plan.json'
    local=validate_plan(parent)
    sources={str(p.relative_to(ROOT)):sha(p) for folder in ('api_pilot','tests/api_pilot') for p in (ROOT/folder).glob('*.py')}
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','diff','HEAD','--','api_pilot','tests/api_pilot'],cwd=ROOT,text=True):
        raise RuntimeError('Commit implementation before freezing')
    model=json.loads((evidence/'model.json').read_text())
    assert model['id']==MODEL
    assert model['pricing']['prompt']=='0.00000015' and model['pricing']['completion']=='0.0000006'
    assert model['context_length']==128000
    assert 'max_tokens' in model['supported_parameters']
    contract={'reliable_billing_bound':False,'input_bound':128000,
              'input_nano_per_token':150,'output_nano_per_token':600,
              'catalog_sha256':sha(evidence/'model.json'),
              'reason':'account_effective_fallback_and_enforced_billing_bound_not_verified',
              'price_unit':'nanodollars per token; 1 USD = 1000000000 nanodollars',
              'sources':['https://ofox.ai/docs/develop/observability/pricing',
                         'https://ofox.ai/docs/develop/observability/dashboard',
                         'https://ofox.ai/docs/develop/advanced/fallback',
                         'https://ofox.ai/docs/changelog'],
              'qualification':'Public pricing is verified; complete per-request billing ceiling is not.'}
    plan={k:v for k,v in local.items() if k!='model'}
    plan.update(schema='api-real-round-v1',round_id=ROUND_ID,label='API_ROUND_BLOCKED_AT_BILLING_GATE',
                source_commit=commit,api_source_sha256=sources,
                parent_local_plan={'path':str(parent),'sha256':sha(parent)},
                model={'name':MODEL,'gateway':'OFOX','developer':'OpenAI','catalog_owned_by':model['owned_by'],
                       'endpoint':ENDPOINT,'interface':'chat_completions','revision':None,
                       'catalog_canonical_slug':model['canonical_slug'],'backend_version_verified':False,
                       'temperature':0,'stream':False,'max_output_tokens_absolute':64,
                       'http_wall_deadline_seconds':60,'automatic_retries':0,'follow_redirects':False},
                budget={'usd':'3','nano_usd':BUDGET_NANO,'max_requests':MAX_REQUESTS,
                        'ledger_path':str(LEDGER_PATH),'shared_phases':['smoke','pilot'],
                        'reservation_refunds':False,'contract':contract},
                smoke={'task':local['tasks'][0],'max_environment_steps':20,'natural_trajectory_only':True,
                       'max_tokens':24,'strict_action_parsing':True,'fallback_forbidden':True},
                execution={'enabled':False,'blocked_by':contract['reason'],
                           'output':str(ROOT/'experiments/api_agent_round_20261020'),
                           'no_resampling':True,'no_overwrite':True,'collector_integration_complete':False},
                protocol_changes=['Strict ACTION + exact normalized admissible match; no original fuzzy/first-command fallback',
                                  'Any protocol/environment/parse exception stops whole round; not caught-and-continued',
                                  'API USD accounting separate from original task utility'],
                required_audited_components=['AuditSession','paired_record','freeze_baselines','evaluate_frozen'],
                limitation='Accessible-state equality does not prove native causal-state equivalence; expert_defer is Oracle.')
    target=ROOT/'api_pilot/plans/round_20261020'
    target.mkdir(exist_ok=False)
    dump(target/'plan.json',plan)
    dump(target/'plan.sha256.json',{'sha256':sha(target/'plan.json')})
    ledger=Ledger.create(LEDGER_PATH,contract)
    try:
        ledger.halt('unverified_billing_bound')
        dump(evidence/'budget_snapshot.json',ledger.summary())
    finally:ledger.close()
    dump(evidence/'billing_gate.json',{'status':'BLOCKED','reliable_billing_bound':False,
                                     'real_generation_requests':0,'contract':contract})
    (evidence/'trajectories.jsonl').open('x').close()  # Zero trajectories, not a synthetic replacement.
    dump(evidence/'trajectory_schema.json',{'record_type':'environment_step','fields':[
         'round_id','phase','split','task_id','branch','step','history_prefix','observation_before',
         'admissible_commands','raw_model_output','action','observation_after','done','won',
         'request_id','usage','latency_seconds','reserved_nano_usd','estimated_nano_usd','stop_reason'],
         'rows_exported':0,'reason':'No environment or model execution after blocked stage A'})
    print(json.dumps({'status':'BLOCKED','plan_sha256':sha(target/'plan.json'),'source_commit':commit,
                      'requests':0,'task_instances_run':0}))


if __name__=='__main__':main()
