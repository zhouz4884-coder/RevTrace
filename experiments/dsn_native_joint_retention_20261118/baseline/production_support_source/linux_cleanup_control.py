"""Real Linux orphan-group control; synthetic CUDA response, no model/GPU run."""
import json,os,pathlib,subprocess,sys,time
from unittest.mock import patch
from common import need
import process_cleanup as pc
def main():
    need(sys.platform.startswith('linux'),'real OS control requires Linux; not silently skipped')
    code="""import json,os,subprocess,sys,time
os.setsid()
p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def ticks(pid):return int(open('/proc/'+str(pid)+'/stat').read().rsplit(')',1)[1].split()[19])
print(json.dumps(dict(owner_pid=os.getpid(),owner_start_ticks=ticks(os.getpid()),worker_pid=p.pid,worker_start_ticks=ticks(p.pid))),flush=True)
"""
    owner=subprocess.Popen([sys.executable,'-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    raw,error=owner.communicate(timeout=10);need(owner.returncode==0,'synthetic leader failed: '+error);value=json.loads(raw);known=[dict(pid=value['worker_pid'],start_ticks=value['worker_start_ticks'])]
    proof=pc.group_proof(value['owner_pid'],value['owner_start_ticks'],bound_event=True,known_members=known)
    try:
        with patch.object(pc,'cuda_owners',return_value=[]):release=pc.terminate_group(None,proof,timeout=10.)
        active=[r for r in pc.process_group_members(value['owner_pid']) if r['state'] not in ('Z','X')];need(not active,'real orphan worker remained executing')
        print(json.dumps(dict(status='PASS_REAL_LINUX_DEAD_LEADER_ORPHAN_GROUP_CONTROL',owner_exitcode=owner.returncode,actual_group_SIGKILL=release['group_SIGKILL_sent'],confirmed_no_executing_members=not active,GPU_or_NVML_checked=False,CUDA_owner_query_was_synthetic=True,scope='Real POSIX PID-generation/session/group termination only. No neural, CUDA release, service, or performance evidence.')))
    finally:
        # Same proof and exact session; no broad PID-name kill.
        if any(r['state'] not in ('Z','X') for r in pc.process_group_members(value['owner_pid'])):pc.signal_group(proof)
if __name__=='__main__':main()
