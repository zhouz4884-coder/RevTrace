"""Frozen serial factorial; observations are not causal fractions."""
import argparse,fcntl,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def save(p,x):
    q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');q.replace(p)
def idle():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True).strip(),'Other GPU owner active'
def main():
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--code-commit',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    lock=(a.output/'RUN.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    source=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    for r in source['files']:assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256']
    cells=[]
    base=[('fine_certified','segment',True),('fine_certified','decoupled',True),
          ('coarse','segment',True),('coarse','decoupled',True),
          ('fine_certified','decoupled',False),('coarse','decoupled',False)]
    for repeat in range(3):
        order=base[repeat%len(base):]+base[:repeat%len(base)]
        for mode,barrier,instrument in order:
            name=f'{mode}-{barrier}-obs{int(instrument)}-r{repeat}'
            cells.append({'name':name,'mode':mode,'barrier':barrier,'instrumentation':instrument,'repeat':repeat})
    frozen={'experiment_id':'PHASE-N-T1-20261021','code_commit':a.code_commit,'cells':cells,'seed':20260906,
        'scope':'12-cell factorial plus six matched instrumentation cost controls; no injected delivery hold',
        'commit_p99_risk_gate_for_future_v2':.05,'minimum_future_selector_eligible_ready_fraction':.25,
        'minimum_future_selector_inclusive_cost_saving':.10,'instrumentation_material_overhead_threshold':.05}
    save(a.output/'RUN.json',frozen);done=[]
    try:
        for cell in cells:
            idle();dest=a.output/cell['name'];(a.output/'logs').mkdir(exist_ok=True)
            command=[sys.executable,'-u',str(ROOT/'scripts/run_tc_live_qwen.py'),'--model',str(a.data_root/'models/Qwen3-ASR-1.7B'),
                '--manifest',str(a.data_root/'datasets/tc_live_20260906/manifest.json'),'--output',str(dest),
                '--code-commit',a.code_commit,'--study-id',frozen['experiment_id'],'--mode',cell['mode'],
                '--sessions','16','--microbatch','16','--proposal-barrier',cell['barrier'],'--proposal-reconciliation','lazy',
                '--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
                '--durable-journal-path',str(a.output/'journals'/(cell['name']+'.wal')),'--journal-sync-mode','group_ready']
            if cell['instrumentation']:command+=['--phase-n-instrumentation','--capture-model-inputs']
            with (a.output/'logs'/(cell['name']+'.log')).open('w') as log:
                run=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            assert run.returncode==0,cell['name']+' failed; preserve and diagnose'
            result=json.loads((dest/'result.json').read_text());done.append(cell['name'])
            save(a.output/'PROGRESS.json',{'status':'RUNNING','completed':done,'total':len(cells)})
            print(json.dumps({'complete':cell['name'],'count':len(done),'xrt':result['audio_seconds_per_wall_second']}),flush=True)
        save(a.output/'SUMMARY.json',{'status':'COMPLETE','completed':done,'expected':18})
    except BaseException as exc:
        save(a.output/'STOP.json',{'error':repr(exc),'completed':done});raise
    finally:lock.close()
if __name__=='__main__':main()
