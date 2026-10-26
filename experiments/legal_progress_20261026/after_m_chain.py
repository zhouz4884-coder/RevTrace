"""Own scoped sequential queue. Never touch other jobs or start on failure."""
from pathlib import Path
import sys,json,time,subprocess,os,traceback
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/lp1_20261026';O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
    mark=O/'CHAIN_COMPLETE.json';assert not mark.exists();started=time.perf_counter()
    try:
        pid=json.loads((O/'OWNER_MS_v2.json').read_text())['M_gpu_pid']
        while True:
            proc=Path('/proc')/str(pid);alive=False
            if proc.exists():
                cmd=proc.joinpath('cmdline').read_bytes();state=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[0]
                alive=b'm_execution_v2/m_orthogonal.py' in cmd and state!='Z'
            if not alive:break
            if time.perf_counter()-started>7200:raise TimeoutError('own M queue wait expired')
            time.sleep(4)
        s=json.loads((O/'m_gpu_v2/SUMMARY.json').read_text());assert s['status']=='COMPLETE' and s['episodes']==320
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'other GPU task present: no new launch'
        A=P/'audit_execution_v1';V=P/'x_service_execution_v2'
        for d in [A,V]:
            assert not d.exists();d.mkdir();subprocess.run(['tar','-xzf',str(d)+'.tar.gz','-C',str(d)],check=True)
        with (O/'m_independent_audit_owner.log').open('x') as log:
            aud=subprocess.run([str(B/'envs/revtrace-er1-20261026/bin/python'),str(A/'m_independent_audit.py')],stdout=log,stderr=subprocess.STDOUT,timeout=100)
        put(O/'CHAIN_PROGRESS.json',dict(stage='OLD_TRUTH_CONTROL',M_audit_rc=aud.returncode))
        with (O/'m_old_truth_controls_owner.log').open('x') as log:
            ctl=subprocess.run([str(B/'envs/revtrace-er1-20261026/bin/python'),str(A/'m_old_controls.py')],stdout=log,stderr=subprocess.STDOUT,timeout=180)
        put(O/'CHAIN_PROGRESS.json',dict(stage='X_SERVICE',M_audit_rc=aud.returncode,old_control_rc=ctl.returncode))
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU not released: no new launch'
        with (O/'x_service_v2_owner.log').open('x') as log:
            run=subprocess.run([str(B/'envs/revbatch-cu128/bin/python'),str(V/'x_service_controller.py')],stdout=log,stderr=subprocess.STDOUT,timeout=7200)
        put(mark,dict(status='COMPLETE_QUEUE' if run.returncode==0 else 'X_SERVICE_STOPPED',M_audit_rc=aud.returncode,old_control_rc=ctl.returncode,X_service_rc=run.returncode))
    except BaseException:put(O/'CHAIN_STOP.json',dict(error=traceback.format_exc()));raise
if __name__=='__main__':main()
