from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');T=Path(__file__).parent
V=sys.argv[1] if len(sys.argv)>1 else 'v8';assert V in ('v8','v9')
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_freeze_boundary_20261027'
c=ssh_client()
try:
    sf=c.open_sftp();sf.get_channel().settimeout(30);local=T/'PAID_OPERATOR_CASES.json';dest=P+'/packages/PAID_OPERATOR_CASES_v1.json'
    try:
        with sf.open(dest,'rb') as f:old=f.read()
    except FileNotFoundError:sf.put(str(local),dest)
    else:assert hashlib.sha256(old).digest()==hashlib.sha256(local.read_bytes()).digest()
    script=r'''from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027'
S=P/'source_v8';D=O/'paid_wait_operator_v8_v1';H=O/'paid_wait_operator_v8_v1_HANDLE.json';A=P/'packages'
source=json.loads((A/'SOURCE_v8.json').read_text());assert source['code_commit']=='27804a4f7b0da57d6e431360677ec791161cb60e'
assert not D.exists() and not H.exists()
assert json.loads((O/'linux_cpu_v8_native/GATE.json').read_text())['status']=='PASS'
for f in source['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[sys.executable,'-B','-u',str(S/'paid_wait_operator.py'),'--out',str(D),'--cases',str(A/'PAID_OPERATOR_CASES_v1.json'),'--source-manifest',str(A/'SOURCE_v8.json'),'--reference-source-manifest',str(A/'SOURCE_v3.json')]
log=O/'paid_wait_operator_v8_v1_controller.log';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid);r=dict(experiment_id='REVTRACE-PAID-WAIT-OPERATOR-V8',source_commit=source['code_commit'],pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),result=str(D),controller_log=str(log),argv=cmd,launched_unix=time.time(),scope='paid production executor old/new input experiment, not deployed service')
H.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
'''
    if V=='v9':
        for old,new in [('source_v8','source_v9'),('SOURCE_v8','SOURCE_v9'),('linux_cpu_v8_native','linux_cpu_v9_native'),('27804a4f7b0da57d6e431360677ec791161cb60e','591c462317d61eda036668abf626fc90133eb9cd'),('paid_wait_operator_v8','paid_wait_operator_v9'),('OPERATOR-V8','OPERATOR-V9')]:script=script.replace(old,new)
    i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -',timeout=35);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
    if rc:raise RuntimeError('paid operator launch gate failed, inspect without retry')
    r=json.loads(out);(L/('paid_wait_operator_'+V+'_v1_HANDLE.json')).write_text(json.dumps(r,indent=2)+'\n')
finally:c.close()
