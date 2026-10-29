"""Root-authorized CPU recounters, refusing overlap with timed GPU work."""
from pathlib import Path
import shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
program=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_service_stability_20261028';O=B/'results/revtrace/physical_retirement_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=P/'PLAN_v1_FROZEN.json';M=P/'ANALYSIS_SOURCE_v2.json';A=P/'analysis_source_v2'
assert sha(plan)=='bd06a99155b2f962b0ba9e832424ee84c9ce7d98cff79fad2091c756792fe39f'
assert sha(M)=='5eb6090e3e035170ec1613d852f494e6b2f452cbc8f8ce531915107bb9495e6d'
assert json.loads((O/'dsn_service_stability_controller_v1/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'do not interfere with timed GPU cells'
assert subprocess.check_output(['git','-C',str(A),'rev-parse','HEAD'],text=True).strip()=='fde6272b494db43a66eebea7444d7c9d1037e687'
assert not subprocess.check_output(['git','-C',str(A),'status','--porcelain','--untracked-files=all'],text=True).strip()
out=O/'dsn_service_stability_analysis_v1';log=O/'dsn_service_stability_analysis_v1.log';handle=P/'CPU_HANDLE_v1.json'
assert not out.exists() and not log.exists() and not handle.exists()
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(A/'run_analysis.py'),'--plan',str(plan),'--plan-sha256',sha(plan),'--source-manifest',str(M),'--output',str(out)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
with log.open('x') as f:child=subprocess.Popen(argv,cwd=A,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id='REVTRACE-DSN-SERVICE-STABILITY-20261028-V1-CPU-RECOUNT',pid=child.pid,start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),argv=argv,launched_unix=time.time(),result=str(out),log=str(log),code_commit='fde6272b494db43a66eebea7444d7c9d1037e687',plan_sha256=sha(plan),new_model_calls=0)
with handle.open('x') as f:json.dump(h,f,indent=2);f.write('\n')
print(json.dumps(h))
'''
c=ssh_client()
try:
    i,o,e=c.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45);i.write(program);i.flush();i.channel.shutdown_write()
    print(o.read().decode());err=e.read().decode();print(err) if err else None;assert o.channel.recv_exit_status()==0
finally:c.close()
