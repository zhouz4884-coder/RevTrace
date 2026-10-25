"""Sequential frozen N1 matrix; no retuning, no silent retries, scoped cleanup."""
from pathlib import Path
import argparse, hashlib, json, os, signal, subprocess, sys, time
P=Path(__file__).resolve().parent
B=P.parents[1]
O=B/'results/revtrace/dependability_20261025'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    tmp=p.with_name(p.name+'.partial');tmp.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def verify_source():
    manifest=read(P/'runtime/SOURCE_MANIFEST.json')
    for r in manifest['files']:assert sha(P/'runtime'/r['path'])==r['sha256'],r['path']
    return manifest
def released(C):
    for h in read(C/'OWNED_WORKER_HANDLES.json'):
        p=Path('/proc')/str(h['pid'])
        if p.exists():assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=str(h['linux_start_ticks']),'owned worker remains live'
def main():
    a=argparse.ArgumentParser();a.add_argument('--stage',choices=['pilot','formal'],required=True);a=a.parse_args()
    stage=a.stage;dest=O/stage;dest.mkdir(exist_ok=False);(dest/'journals').mkdir()
    manifest=verify_source();assert idle(),'GPU occupied, no other task is terminated'
    cells=[]
    if stage=='pilot':
        for window in ['covered','ahead']:cells.append(dict(method='full',consumer='two_lane',window=window,order='authority_first',repeat=0))
    else:
        for repeat in range(2):
            for window in ['covered','ahead']:
                for order in ['proposal_first','authority_first']:
                    for consumer in ['snapshot','two_lane']:
                        for method in ['full','omit','standard']:
                            cells.append(dict(method=method,consumer=consumer,window=window,order=order,repeat=repeat))
        for consumer in ['snapshot','two_lane']:
            for method in ['full','omit','standard']:cells.append(dict(method=method,consumer=consumer,window='none',order='none',repeat=0))
    save(dest/'FREEZE.json',{'cells':cells,'source':manifest['code_commit'],'manifest_sha256':sha(P/'MANIFEST.json'),
        'scope':'post-compute intervention; reused four PhaseD sources; no natural prevalence','pid':os.getpid()})
    done=[];active=None;proc=None
    try:
        for c in cells:
            assert idle(),'unrelated GPU occupancy; stop rather than competing'
            verify_source();active='-'.join(str(c[k]) for k in ['method','consumer','window','order','repeat']);C=dest/active
            cfg=None
            if c['window']!='none':
                p,a=(1,3) if c['window']=='covered' else (7,6)
                cfg=dest/(active+'.ORDER.json')
                save(cfg,{'proposal_window':p,'authority_window':a,'order':c['order'],'sessions':[0,1,2,3],'timeout_seconds':45})
            cmd=[sys.executable,'-u',str(P/'runtime/scripts/run_tc_live_qwen.py'),
                '--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(P/'MANIFEST.json'),
                '--output',str(C),'--code-commit',manifest['code_commit'],'--study-id','REVTRACE-DEPENDABILITY-N1-20261025',
                '--mode','coarse','--sessions','4','--proposal-gpus','0','--authority-gpus','1',
                '--microbatch','4','--max-new-tokens','256','--arrival','sync','--seed','20261025','--timeout','180',
                '--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--trusted-text-binding',
                '--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy',c['consumer'],
                '--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs',
                '--durable-journal-path',str(dest/'journals'/(active+'.wal')),'--journal-sync-mode','group_ready',
                '--result-delivery','batch','--async-implementation','standard' if c['method']=='standard' else 'revtrace']
            if cfg:cmd+=['--post-compute-order',str(cfg)]
            if c['method']=='omit':cmd+=['--omit-receive-freshness']
            save(dest/(active+'.COMMAND.json'),{'cell':c,'argv':cmd,'source_sha256':sha(P/'runtime/SOURCE_MANIFEST.json')})
            with (dest/(active+'.log')).open('xb') as f:
                proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=P/'runtime',start_new_session=True)
                try:rc=proc.wait(timeout=250)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise
            assert rc==0,'cell failed; no automatic retry'
            result=read(C/'result.json');assert result['fine_window_accounting_complete']
            if cfg:assert result['post_compute_order_completed']
            released(C);assert idle(),'GPU lease still present'
            done.append(active);save(dest/'PROGRESS.json',{'status':'RUNNING','completed':done,'expected':len(cells),'active':None})
            print('COMPLETE',stage,len(done),active,flush=True)
        save(dest/'SUMMARY.json',{'status':'COMPLETE_RUNS_PENDING_INDEPENDENT_AUDIT','completed':done,'cells':len(done),
            'expected':len(cells),'GPU_queue_closed':True})
    except BaseException as exc:
        save(dest/'STOP.json',{'error':repr(exc),'active':active,'completed':done,'raw_retained':True,'time_unix':time.time()})
        raise
if __name__=='__main__':main()
