"""Gated small actual service: shared executor/seed/Row/WAL and paid P work."""
from pathlib import Path
import sys,json,subprocess,hashlib,traceback,time,os
from memory_gpu_pilot import Power
W=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    D=O/'x_service_v2';D.mkdir();complete=[]
    try:
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
        for f in source['files']:assert hashlib.sha256((W/f['path']).read_bytes()).hexdigest()==f['sha256']
        gate=json.loads((O/'x_gpu_v1/SUMMARY.json').read_text());assert gate['status']=='COMPLETE_32_CONDITIONAL_STATE_TUPLES'
        spec=json.loads((W/'X_PROFILES_v1.json').read_text());chosen=[]
        for q in spec['profiles']:
            if q['source_id'] not in [s['source_id'] for s in chosen]:chosen.append(q['source'])
        # Bounded development service, two metadata-first sources, no outcome selection.
        manifest=dict(sessions=chosen[:2],scope='native independent full audio, first2 of frozen8 sources; bounded DEVELOPMENT service not held-out confirmation')
        put(D/'manifest.json',manifest);cells=[]
        for rep in [0,1]:
            for rho in [1,3]:
                methods=['fresh','strict-full','prefix','revtrace-prefix'];methods=methods[rep:]+methods[:rep]
                for mode in methods:cells.append(dict(mode=mode,rho=rho,repeat=rep))
        put(D/'FREEZE.json',dict(source=source,cells=cells,manifest=manifest,expected=16,
            scope='actual full native audio,2stream development service,4method×2fixedrho×2freshprocess; NOT population or held-out result',
            SLO=dict(display=2,commit=8),offered_denominator='all full audio, including unresolved frontiers',
            resources='same FP16 P0 +FP32 A1,physical microbatch1,eager256,Row-complete,current-input embedding optimization,event-COW kernel,real input/canonical WAL and Consumer'))
        for i,cell in enumerate(cells):
            name=f'{i:02}-{cell["mode"]}-rho{cell["rho"]}-r{cell["repeat"]}';C=D/name;C.mkdir()
            envelope=dict(method='standard_fair' if cell['mode']=='prefix' else 'dgft_original',budget_audio_seconds=1000.,
                warning_age=100.,critical_age=200.,clear_age=10.,display_slo=2.,queue_threshold=10000,reject_new_after_seconds=1000.,tick_seconds=.001)
            put(C/'envelope.json',envelope);put(C/'arrivals.json',dict(offsets=[0.,.25]))
            cmd=[sys.executable,str(W/'runtime/scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
                '--manifest',str(D/'manifest.json'),'--output',str(C/'attempt0'),'--code-commit',source['code_commit'],
                '--study-id','REVTRACE-LP1-X-SERVICE','--sessions','2','--microbatch','1','--max-new-tokens','256',
                '--timeout','180','--trusted-text-binding','--capture-model-inputs','--result-delivery','row','--protocol-kernel',
                '--prefix-executor-mode',cell['mode'],'--authority-rho',str(cell['rho']),'--kernel-copy-mode','event-cow',
                '--envelope-config',str(C/'envelope.json'),'--arrival-schedule',str(C/'arrivals.json'),'--episode-context',str(C/'episode.json'),
                '--input-journal-path',str(C/'input.wal'),'--durable-journal-path',str(C/'canonical.wal')]
            sampler=Power(C/'episode_power.jsonl')
            try:
                before=time.perf_counter()
                with (C/'runner.log').open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=330)
                after=time.perf_counter()
                if r.returncode==0:
                    measurement=json.loads((C/'attempt0/power_samples.json').read_text())
                    st,en=measurement['measurement_start_perf'],measurement['measurement_end_perf']
                    put(C/'POWER_MEASURED.json',dict(serving_start_perf=st,serving_end_perf=en,
                        serving_both_GPU_joules=sampler.joules(st,en),cold_launch_to_exit_both_GPU_joules=sampler.joules(before,after),
                        samples=len(sampler.rows),scope='actual external BOTH GPU power; serve vs cold-launch intervals separate; CPU host energy unmeasured'))
            finally:sampler.close()
            if r.returncode:raise RuntimeError(name+' runner failed rc='+str(r.returncode))
            complete.append(name);put(D/'PROGRESS.json',dict(status='RUNNING',completed=complete,expected=16))
            assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'owned GPU processes did not drain'
        put(D/'SUMMARY.json',dict(status='COMPLETE',completed=complete,expected=16))
    except BaseException:put(D/'STOP.json',dict(error=traceback.format_exc(),completed=complete));raise
if __name__=='__main__':main()
