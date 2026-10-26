"""Scientific dependency runner: no GPU overlap; fail closed at every audit."""
from pathlib import Path
import json,subprocess,sys,time,hashlib,os
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def save(p,d):
    tmp=p.with_name(p.name+'.partial');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def main():
    assert not (O/'CAMPAIGN_STARTED.json').exists()
    source=read(P/'runtime/SOURCE_MANIFEST.json')
    stages=['boundary_pilot','post_sync_pilot','normal','fault','boundary','post_sync']
    # Freeze every formal cell definition by controller hash before seeing any
    # new validation results. No validation-dependent parameter changes.
    save(O/'CAMPAIGN_STARTED.json',dict(stages=stages,source=source['code_commit'],
        pid=os.getpid(),start_ticks=(Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')',1)[1].split()[19],
        controller_sha256=hashlib.sha256((P/'gpu_controller.py').read_bytes()).hexdigest(),
        normal_expected=24,fault_expected=36,boundary_expected=16,post_sync_expected=8,
        no_extra_gpu_after_final=True))
    complete=[]
    try:
        for stage in stages:
            for label,cmd in [
                ('GPU',[sys.executable,'-u',str(P/'gpu_controller.py'),'--stage',stage]),
                ('INDEPENDENT',[sys.executable,str(P/'audit_ck5.py'),'--stage',stage]),
                ('CPU_ASSETS',[sys.executable,str(P/'audit_assets.py'),'--stage',stage])]:
                save(O/'CAMPAIGN_PROGRESS.json',dict(stage=stage,phase=label,completed=complete,status='RUNNING'))
                with (O/(stage+'_'+label+'.log')).open('xb') as f:
                    subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
            complete.append(stage)
        save(O/'CAMPAIGN_COMPLETE.json',dict(status='COMPLETE_ALL_SIX_STAGES_WITH_INDEPENDENT_AND_CPU_ASSET_GATES',
            stages=complete,source=source['code_commit'],completed_perf=time.perf_counter()))
    except BaseException as ex:
        save(O/'CAMPAIGN_STOP.json',dict(error=repr(ex),completed=complete,all_failures_retained=True));raise
if __name__=='__main__':main()
