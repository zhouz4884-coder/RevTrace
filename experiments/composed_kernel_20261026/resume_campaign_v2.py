"""CPU checker-only repair; reuse all four completed GPU probes unchanged."""
from pathlib import Path
import json,subprocess,sys,time,hashlib,os
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def save(p,d):
    q=p.with_name(p.name+'.partial');q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)
def main():
    assert (O/'CAMPAIGN_STOP.json').exists() and (O/'boundary_pilot_AUDIT.json').exists()
    assert len(read(O/'boundary_pilot/SUMMARY.json')['completed'])==4
    assert not (O/'CAMPAIGN_RECOVERY_v2.json').exists()
    save(O/'CAMPAIGN_RECOVERY_v2.json',dict(reason='CPU checker selected Authority and Proposer at the same window; restrict follow-up to actual Proposer',
        source_unchanged=read(P/'runtime/SOURCE_MANIFEST.json')['code_commit'],new_GPU_repeats=0,
        original_failure_retained=True,pid=os.getpid()))
    complete=[]
    try:
        with (O/'boundary_pilot_CPU_ASSETS_v2.log').open('xb') as f:
            subprocess.run([sys.executable,str(P/'audit_assets_v2.py'),'--stage','boundary_pilot'],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
        complete.append('boundary_pilot')
        for stage in ['post_sync_pilot','normal','fault','boundary','post_sync']:
            for label,cmd in [('GPU',[sys.executable,'-u',str(P/'gpu_controller.py'),'--stage',stage]),
                ('INDEPENDENT',[sys.executable,str(P/'audit_ck5.py'),'--stage',stage]),
                ('CPU_ASSETS',[sys.executable,str(P/'audit_assets_v2.py'),'--stage',stage])]:
                save(O/'CAMPAIGN_PROGRESS_v2.json',dict(stage=stage,phase=label,completed=complete,status='RUNNING'))
                with (O/(stage+'_'+label+'.log')).open('xb') as f:subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
            complete.append(stage)
        save(O/'CAMPAIGN_COMPLETE_v2.json',dict(status='COMPLETE_ALL_SIX_STAGES_WITH_INDEPENDENT_AND_CPU_ASSET_GATES',
            stages=complete,source=read(P/'runtime/SOURCE_MANIFEST.json')['code_commit'],completed_perf=time.perf_counter()))
    except BaseException as ex:
        save(O/'CAMPAIGN_STOP_v2.json',dict(error=repr(ex),completed=complete,all_failures_retained=True));raise
if __name__=='__main__':main()
