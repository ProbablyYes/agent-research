"""Record explicit user acceptance of nominal billing; never resets request totals."""
import json
import subprocess
from pathlib import Path
from pilot_validity.core import ROOT,dump,sha
from pilot_validity.run import validate_plan
from .budget import Ledger,ROUND_ID


def main():
    base=validate_plan(ROOT/'pilot_validity/plans/real_pilot_final/plan.json')
    oldpath=ROOT/'api_pilot/plans/round_20261020/plan.json'
    plan=json.loads(oldpath.read_text())
    assert plan['tasks']==base['tasks'] and plan['config']==base['config']
    if subprocess.check_output(['git','diff','HEAD','--','api_pilot','tests/api_pilot'],cwd=ROOT,text=True):
        raise RuntimeError('Commit source before freeze')
    authorization={'round_id':ROUND_ID,'user_authorized':True,
                   'basis':'User explicitly instructed to proceed despite unresolved billing-bound concern on 2026-10-20',
                   'budget_usd':'3','max_requests':400,'reliable_billing_bound':False,
                   'acceptance':'Nominal catalog-price accounting; not a provider-enforced invoice cap'}
    plan.update(label='OFOX_GPT4O_MINI_REAL_AGENT_ENGINEERING',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                api_source_sha256={str(p.relative_to(ROOT)):sha(p) for folder in ('api_pilot','tests/api_pilot') for p in (ROOT/folder).glob('*.py')},
                previous_blocked_plan={'path':str(oldpath),'sha256':sha(oldpath)},user_authorization=authorization)
    plan['budget']['contract']['user_accepted_nominal_accounting']=True
    plan['budget']['contract']['settle_completed_to_nominal_usage']=True
    plan['budget']['reservation_refunds']='Only after valid completed Usage: settle to nominal estimate; unknown/timeout retains full reservation'
    plan['execution'].update(enabled=True,blocked_by=None,collector_integration_complete=True)
    target=ROOT/'api_pilot/plans/round_20261020_authorized';target.mkdir(exist_ok=False)
    dump(target/'plan.json',plan);dump(target/'plan.sha256.json',{'sha256':sha(target/'plan.json')})
    l=Ledger()
    try:
        before=l.summary();l.accept_nominal_accounting(authorization);after=l.summary()
        dump(ROOT/'reports/evidence/api_authorized_20261020/authorization.json',{'authorization':authorization,'before':before,'after':after,'plan_sha256':sha(target/'plan.json')})
    finally:l.close()
    print(json.dumps({'source_commit':plan['source_commit'],'plan_sha256':sha(target/'plan.json'),'status':'authorized_nominal_accounting'}))


if __name__=='__main__':main()
