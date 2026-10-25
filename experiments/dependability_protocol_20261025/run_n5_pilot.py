"""Frozen4-cell N5 live pilot with outer real power measurement and owned cleanup."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time

def read(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    t=p.with_name(p.name+'.partial');t.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');t.replace(p)
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
WEIGHTS={'model-00001-of-00002.safetensors':'a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6',
         'model-00002-of-00002.safetensors':'6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc'}
def source_check(P):
    m=read(P/'runtime/SOURCE_MANIFEST.json')
    for r in m['files']:assert sha(P/'runtime'/r['path'])==r['sha256'],r['path']
    return m
def owned_released(C):
    handles=read(C/'OWNED_WORKER_HANDLES.json')
    for h in handles:
        p=Path('/proc')/str(h['pid'])
        assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks'])),'own worker still present'
    return handles
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
    assert str(B)=='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
    P=B/'projects/revtrace_dependability_20261025/n5_v1';O=B/'results/revtrace/dependability_20261025/n5_v1'
    m=source_check(P);assert idle(),'another task owns a GPU'
    for name,wanted in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==wanted
    sys.path.insert(0,str(P/'runtime/scripts/v100'));from run_v100_matrix import PowerSampler
    cells=[dict(method=method,load=load,arrival=arrival,repeat=0) for load,arrival in [(4,'sync'),(16,'staggered')] for method in ['fine_fair','cde_full']]
    dest=O/'pilot';dest.mkdir(exist_ok=False)
    save(dest/'FREEZE.json',dict(cells=cells,runtime_commit=m['code_commit'],runtime_manifest_sha256=sha(P/'runtime/SOURCE_MANIFEST.json'),
        manifest_sha256=sha(P/'DEVELOPMENT_MANIFEST.json'),controller_sha256=sha(Path(__file__)),
        model_weights=WEIGHTS,statistical_scope='development legality/cost pilot; not independent confirmation',pid=os.getpid()))
    done=[];active=None;proc=None;sampler=None
    try:
        for c in cells:
            assert idle(),'unexpected GPU occupancy; never terminate another task'
            source_check(P);active=f"{c['method']}-c{c['load']}-{c['arrival']}-r0";E=dest/active;E.mkdir()
            cfg=dict(method=c['method'],budget_audio_seconds=96,warning_age=4,critical_age=8,clear_age=2,
                display_slo=2,commit_slo=8,queue_threshold=8,reject_new_after_seconds=8,tick_seconds=.005,
                model_weight_sha256=WEIGHTS)
            save(E/'POLICY.json',cfg);save(E/'ARRIVAL.json',dict(offsets=[0 if c['arrival']=='sync' else .25*i for i in range(c['load'])]))
            C=E/'attempt0'
            cmd=[sys.executable,'-u',str(P/'runtime/scripts/run_tc_live_qwen.py'),
                '--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(P/'DEVELOPMENT_MANIFEST.json'),
                '--output',str(C),'--code-commit',m['code_commit'],'--study-id','REVTRACE-CDE-N5-20261026',
                '--sessions',str(c['load']),'--proposal-gpus','0','--authority-gpus','1','--microbatch','16',
                '--max-new-tokens','256','--seed','20261026','--timeout','300','--result-delivery','row',
                '--phase-n-instrumentation','--journal-sync-mode','group_ready','--durable-journal-path',str(E/'canonical.wal'),
                '--envelope-config',str(E/'POLICY.json'),'--arrival-schedule',str(E/'ARRIVAL.json'),
                '--episode-context',str(E/'CONTEXT.json'),'--input-journal-path',str(E/'input.wal')]
            save(E/'COMMAND.json',dict(cell=c,argv=cmd,runtime_commit=m['code_commit']))
            sampler=PowerSampler([0,1],interval=.2);sampler.start();launch=time.perf_counter()
            with (E/'attempt0.log').open('xb') as f:
                proc=subprocess.Popen(cmd,cwd=P/'runtime',stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
                stat=Path('/proc')/str(proc.pid)
                identity=dict(pid=proc.pid,start_ticks=stat.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
                    cmdline_sha256=sha(stat/'cmdline'),launch_perf=launch)
                save(E/'OWNER_HANDLE.json',identity)
                try:rc=proc.wait(timeout=390)
                except subprocess.TimeoutExpired:
                    if stat.exists() and stat.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==identity['start_ticks']:
                        os.killpg(proc.pid,signal.SIGKILL)
                    proc.wait();raise
            end=time.perf_counter();sample_summary=sampler.stop()
            save(E/'EPISODE_POWER.json',dict(samples=sampler.rows,sampler_summary=sample_summary,
                outer_launch_perf=launch,outer_end_perf=end,gpu_indices=[0,1],
                primary_window='original episode origin to actual Consumer/model drain; independently clipped after collection',
                scope='GPU power, not CPU/total system power; startup samples separately retained'))
            sampler=None
            assert rc==0,'pilot run failed; preserve raw and stop, do not silently retry'
            result=read(C/'result.json');assert result['fine_window_accounting_complete']
            handles=owned_released(C);assert idle(),'owned worker not drained or another task started'
            save(E/'RUN_COMPLETE_PENDING_AUDIT.json',dict(returncode=rc,owned_handles=handles,source=m['code_commit'],
                source_input_id=sha(P/'DEVELOPMENT_MANIFEST.json'),actual_episode_end_perf=end))
            done.append(active);save(dest/'PROGRESS.json',dict(status='RUNNING',completed=done,expected=4))
            print('COMPLETE',len(done),active,flush=True)
        for name,wanted in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==wanted
        save(dest/'SUMMARY.json',dict(status='COMPLETE4_REAL_GPU_PILOT_PENDING_INDEPENDENT_AUDIT',completed=done,expected=4,cells=4,
            GPU_queue_closed=True,development_sources_only=True))
    except BaseException as exc:
        if sampler:
            sampler.stop();save(dest/'FAILED_POWER.json',dict(samples=sampler.rows,scope='retained partial/failed GPU work'))
        save(dest/'STOP.json',dict(active=active,completed=done,error=repr(exc),all_raw_retained=True,no_automatic_retry=True))
        raise
if __name__=='__main__':main()
