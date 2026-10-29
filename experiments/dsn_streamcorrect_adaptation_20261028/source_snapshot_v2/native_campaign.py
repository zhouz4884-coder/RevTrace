"""Bounded original-selection witness gate, then frozen twelve-cell comparison."""
import argparse,datetime,hashlib,json,os,pathlib,subprocess,sys,time,traceback
from native_audit import audit_cell,audit_campaign
from native_service import verify_source,put
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--source-manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    source=verify_source(a.source_manifest);plan=json.loads(a.plan.read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',plan);put(out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],source=source,frozen_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_result=str(out/'execution.jsonl'),summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json')))
    witnesses=[];completed=[]
    try:
        for cell in plan['cells']:
            if cell['stage']=='formal' and not witnesses:raise ValueError('native prerequisites not witnessed')
            command=[sys.executable,str(pathlib.Path(__file__).parent/'native_service.py'),'--config',cell['config'],'--source-manifest',str(a.source_manifest),'--out',cell['out']]
            with open(out/(cell['cell_id']+'.log'),'x',encoding='utf-8') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                put(out/'ACTIVE_CHILD.json',dict(cell_id=cell['cell_id'],pid=child.pid,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
                rc=child.wait()
            if rc:raise RuntimeError('native cell failed and preserved: '+cell['cell_id'])
            recounted=audit_cell(cell['out']);completed.append(dict(cell_id=cell['cell_id'],stage=cell['stage'],audit=recounted))
            if cell['stage']=='witness':
                witnesses.append(recounted)
                if len(witnesses)==2:
                    changed=sum(x['corrected_updates'] for x in witnesses);same=sum(x['unchanged_updates'] for x in witnesses)
                    gate=dict(status='PASS_NATURAL_CORRECTED_AND_UNCHANGED_SELECTIONS' if changed and same else 'NO_NATURAL_BOTH_TYPE_WITNESS_IN_FIXED_FOUR_SOURCES',corrected_updates=changed,unchanged_updates=same,sources=[s for x in witnesses for s in x['source_ids']])
                    put(out/'WITNESS_GATE.json',gate)
                    if not(changed and same):
                        put(out/'SUMMARY.json',dict(completed=completed,stopped_at='predeclared natural feedback witness gate'))
                        put(out/'GATE.json',gate);return 0
            put(out/'PROGRESS.json',dict(completed=completed,remaining=len(plan['cells'])-len(completed)))
            for attempt in range(30):
                apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
                if not apps:break
                time.sleep(.2)
            if apps:raise RuntimeError('GPU context still present after worker shutdown; no next cell launched')
        r=audit_campaign(plan);put(out/'SUMMARY.json',r);put(out/'GATE.json',dict(status=r['status']));return 0 if r['status'].startswith('PASS_') else 1
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());put(out/'SUMMARY.json',dict(completed=completed));put(out/'GATE.json',dict(status='FAIL_NATIVE_CAMPAIGN_PRESERVED'));return 1
if __name__=='__main__':raise SystemExit(main())
