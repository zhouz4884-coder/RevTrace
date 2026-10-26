"""Checker-only repair of one owner-enqueue/pre-submit SIGKILL interleaving."""
from pathlib import Path
import json,subprocess,sys,time,os
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def save(p,d):
    q=p.with_name(p.name+'.partial');q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)
def main():
    assert (O/'CAMPAIGN_STOP_v2.json').exists()
    assert len(read(O/'fault/SUMMARY.json')['completed'])==36
    assert not (O/'CAMPAIGN_RECOVERY_v3.json').exists()
    save(O/'CAMPAIGN_RECOVERY_v3.json',dict(reason='one genuine owner-only enqueue before any Worker pre-submit/result; audit it as logical, not a missing GPU result',
        source_unchanged=read(P/'runtime/SOURCE_MANIFEST.json')['code_commit'],new_GPU_repeats=0,
        original_failure_retained=True,pid=os.getpid()))
    complete=['boundary_pilot','post_sync_pilot','normal']
    try:
        for label,cmd in [('INDEPENDENT',[sys.executable,str(P/'audit_ck5_v2.py'),'--stage','fault']),
            ('CPU_ASSETS',[sys.executable,str(P/'audit_assets_v2.py'),'--stage','fault'])]:
            save(O/'CAMPAIGN_PROGRESS_v3.json',dict(stage='fault',phase=label,completed=complete,status='RUNNING'))
            with (O/('fault_'+label+'_v2.log')).open('xb') as f:subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
        complete.append('fault')
        for stage in ['boundary','post_sync']:
            for label,cmd in [('GPU',[sys.executable,'-u',str(P/'gpu_controller.py'),'--stage',stage]),
                ('INDEPENDENT',[sys.executable,str(P/'audit_ck5_v2.py'),'--stage',stage]),
                ('CPU_ASSETS',[sys.executable,str(P/'audit_assets_v2.py'),'--stage',stage])]:
                save(O/'CAMPAIGN_PROGRESS_v3.json',dict(stage=stage,phase=label,completed=complete,status='RUNNING'))
                with (O/(stage+'_'+label+'.log')).open('xb') as f:subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
            complete.append(stage)
        save(O/'CAMPAIGN_COMPLETE_v3.json',dict(status='COMPLETE_ALL_SIX_STAGES_WITH_INDEPENDENT_AND_CPU_ASSET_GATES',
            stages=complete,source=read(P/'runtime/SOURCE_MANIFEST.json')['code_commit'],completed_perf=time.perf_counter()))
    except BaseException as ex:
        save(O/'CAMPAIGN_STOP_v3.json',dict(error=repr(ex),completed=complete,all_failures_retained=True));raise
if __name__=='__main__':main()
