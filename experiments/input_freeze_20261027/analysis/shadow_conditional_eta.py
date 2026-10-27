"""Replay completed owner events in order; predictions see no future output."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,statistics


def main():
    p=argparse.ArgumentParser();p.add_argument('--remote',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--estimator',type=Path);p.add_argument('--warm-bank',type=Path)
    a=p.parse_args();assert not a.output.exists()
    here=Path(__file__).resolve().parent
    estimator=a.estimator or here/'dispatch_wait.py';estimator_sha=hashlib.sha256(estimator.read_bytes()).hexdigest()
    spec=importlib.util.spec_from_file_location('audited_dispatch_wait',estimator)
    dm=importlib.util.module_from_spec(spec);sys.modules[spec.name]=dm;spec.loader.exec_module(dm)
    hs=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
    helper=importlib.util.module_from_spec(hs);hs.loader.exec_module(helper);c=helper.ssh_client();sf=c.open_sftp();sf.get_channel().settimeout(40)
    inputs=[];rows=[]
    def load(path,lines=False):
        b=sf.open(a.remote+'/'+path).read();inputs.append(dict(path=path,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
        return [json.loads(x) for x in b.decode().splitlines() if x.strip()] if lines else json.loads(b)
    def summarize(xs):
        if not xs:return dict(n=0,old_MAE=None,new_MAE=None)
        return dict(n=len(xs),old_MAE=statistics.mean(abs(x['actual']-x['old']) for x in xs),
            new_MAE=statistics.mean(abs(x['actual']-x['new']) for x in xs),
            old_underpredict=sum(x['old']<x['actual'] for x in xs),
            new_underpredict=sum(x['new']<x['actual'] for x in xs),
            new_unsupported=sum(x['unsupported'] for x in xs),
            old_median=statistics.median(x['old'] for x in xs),
            new_median=statistics.median(x['new'] for x in xs),actual_median=statistics.median(x['actual'] for x in xs))
    try:
        summary=load('SUMMARY.json');freeze=load('FREEZE.json')
        assert len(summary['completed'])==summary['expected']==6
        for cell in summary['completed']:
            prefix=cell+'/attempt0/';cfg=load(prefix+'config.json');events=load(prefix+'events.jsonl',True)
            ctl=dm.DispatchWaitController(dict(cfg['dispatch_wait'],eta_mode='conditional',eta_min_tail_samples=4,install_cost_default_seconds=.3))
            if a.warm_bank and cfg['dispatch_wait']['policy']!='immediate':
                ctl.load_prior_history(a.warm_bank,hashlib.sha256(a.warm_bank.read_bytes()).hexdigest())
            t0=next(e['t0_perf'] for e in events if e['kind']=='run-start')
            # Future outcomes are kept in a separate audit dictionary and are
            # never passed to the estimator or its event observer.
            truth={e['job_id']:t0+e['installed'] for e in events if e['kind']=='commit'}
            out=[]
            for e in events:
                if e['kind']=='dispatch-wait-decision' and e['pending_authority']:
                    old=e['pending_authority'];jid=old['job_id'];receipt=ctl._authority_receipts.get(jid)
                    observed=e['observed_perf'];age=max(0.,observed-(t0+receipt['received'])) if receipt else 0.
                    n=old['physical_batch_size'] if old['physical_batch_size'] else receipt['batch_size'] if receipt else 0
                    prediction=ctl._remaining_authority(n,old['elapsed_seconds'],already_received=receipt is not None,receipt_age=age)
                    out.append(dict(session_id=e['session_id'],window=e['window'],job_id=jid,actual_old_wait=e['decision']=='wait',
                        old=old['remaining_estimate_seconds'],new=prediction['remaining_estimate_seconds'],
                        actual=truth[jid]-observed,unsupported=prediction['eta_unsupported_tail'],
                        receipt_survivors=prediction['receipt_conditional_survivors'],
                        installation_observations=prediction['installation_duration_observations'],
                        already_received=receipt is not None,
                        original_wait_budget=e['wait_budget_seconds']))
                ctl.observe_event(e)
            row=dict(policy=cfg['dispatch_wait']['policy'],warm_bank_used=ctl.profile()['prior_history'],all_pending_decisions=summarize(out),
                originally_selected_waits=summarize([x for x in out if x['actual_old_wait']]),
                supported_only=summarize([x for x in out if not x['unsupported']]),predictions=out)
            rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='predictions'}),flush=True)
    finally:sf.close();c.close()
    assert hashlib.sha256(estimator.read_bytes()).hexdigest()==estimator_sha,'estimator changed during audit'
    report=dict(experiment_id='REVTRACE-FREEZE-20261027-PAST-ONLY-ETA-SHADOW',
        status='COMPLETE_DIAGNOSTIC_REPLAY_NOT_SERVING',base_source_commit=freeze['code_commit'],
        estimator_sha256=estimator_sha,estimator_bytes_unchanged_during_audit=True,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,inputs=inputs,
        new_GPU_calls=0,gate='DIAGNOSTIC_ONLY; changed decisions require new real execution',
        limitations=['Rows/repeats are dependent.','Past-only forecast replay is not a counterfactual schedule or speedup.',
          'Unknown tails use conservative policy fallback; not a confidence bound.','No heldout data tuned the estimator.'])
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
