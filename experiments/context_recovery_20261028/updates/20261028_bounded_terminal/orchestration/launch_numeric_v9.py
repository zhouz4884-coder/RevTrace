from pathlib import Path
import json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
c=ssh_client()
try:
 script=r'''from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027';A=P/'packages';S=P/'source_v9';D=O/'native_numeric_v9_v1';H=O/'native_numeric_v9_v1_HANDLE.json'
m=json.loads((A/'SOURCE_v9.json').read_text());assert m['code_commit']=='591c462317d61eda036668abf626fc90133eb9cd'
assert json.loads((O/'linux_cpu_v9_native/GATE.json').read_text())['gate']=='PASS'
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['code_commit']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'],text=True).strip()
for f in m['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not D.exists() and not H.exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[sys.executable,'-B','-u',str(S/'native_lifecycle/numeric_probe.py'),'--out',str(D),'--source-root',str(S),'--source-manifest',str(A/'SOURCE_v9.json'),'--config',str(S/'native_lifecycle/PILOT_CONFIG.json'),'--model-manifest',str(A/'NATIVE_QWEN25_ASSETS_v1.json'),'--native-reference',str(O/'native_v8_pilot_v1')]
log=O/'native_numeric_v9_v1_controller.log'
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid);r=dict(experiment_id='REVTRACE-NATIVE-NUMERIC-V9',source_commit=m['code_commit'],pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=cmd,result=str(D),controller_log=str(log),launched_unix=time.time(),scope='same-input precision diagnostic; no application writes')
H.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
'''
 i,o,e=c.exec_command(B+'/envs/revtrace_native_20261027/bin/python -B -',timeout=35);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
 if rc:raise RuntimeError('launch gate failed, do not duplicate')
 (L/'native_numeric_v9_v1_HANDLE.json').write_text(json.dumps(json.loads(out),indent=2)+'\n')
finally:c.close()
