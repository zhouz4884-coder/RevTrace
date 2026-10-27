from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_freeze_boundary_20261027'
V=sys.argv[1] if len(sys.argv)>1 else 'v6';assert V in ('v6','v7')
c=ssh_client()
try:
 sf=c.open_sftp();sf.get_channel().settimeout(40)
 for n in ['source_'+V+'.bundle','source_'+V+'.tar.gz','SOURCE_'+V+'.json']:
  dest=P+'/packages/CONTEXT_'+n
  try:
   with sf.open(dest,'rb') as f:old=f.read()
  except FileNotFoundError:sf.put(str(L/n),dest)
  else:assert hashlib.sha256(old).digest()==hashlib.sha256((L/n).read_bytes()).digest()
 script=r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,platform,subprocess,sys,tarfile,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';O=B/'results/revtrace/freeze_boundary_20261027';A=P/'packages';S=P/'context_analysis_v6';D=O/'paid_native_context_capacity_audit_v1';H=O/'paid_native_context_capacity_audit_v1_HANDLE.json'
m=json.loads((A/'CONTEXT_SOURCE_v6.json').read_text());commit=m['code_commit'];assert commit=='79cb171b3fc0418b4f989294d4581b75fbd40393'
def git(*x):return subprocess.check_output(['git','-C',str(S),*x],stderr=subprocess.PIPE,text=True).strip()
if not S.exists():
 S.mkdir()
 with tarfile.open(A/'CONTEXT_source_v6.tar.gz') as tar:
  for f in tar.getmembers():assert not f.issym() and not f.islnk() and (S/f.name).resolve().is_relative_to(S)
  tar.extractall(S,filter='data')
 git('init');git('config','core.autocrlf','false');git('fetch',str(A/'CONTEXT_source_v6.bundle'),'HEAD:refs/heads/frozen');git('symbolic-ref','HEAD','refs/heads/frozen');git('read-tree',commit)
assert git('rev-parse','HEAD')==commit and not git('status','--porcelain')
for f in m['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not D.exists() and not H.exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
study=O/'paid_native_context_capacity_v2';assert not (study/'STOP.json').exists() and json.loads((study/'SUMMARY.json').read_text())['status']=='PAID_FEASIBILITY_RECORDED'
cpu=O/'context_source_cpu_v6';assert not cpu.exists();cpu.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
argv=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),'--basetemp',str(cpu/'tmp'),'--junitxml',str(cpu/'results.xml'),*[str(S/n) for n in ['test_analysis.py','test_context_probe.py','test_context_audit.py']],'-q']
environment=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['pytest','numpy','transformers','soundfile']})
(cpu/'ENVIRONMENT.json').write_text(json.dumps(environment,indent=2)+'\n')
(cpu/'FREEZE.json').write_text(json.dumps(dict(experiment_id='REVTRACE-CONTEXT-ANALYSIS-LINUX-CPU-V6',source_commit=commit,source_manifest_sha256=hashlib.sha256((A/'CONTEXT_SOURCE_v6.json').read_bytes()).hexdigest(),environment_sha256=hashlib.sha256((cpu/'ENVIRONMENT.json').read_bytes()).hexdigest(),argv=argv,raw_result_location=str(cpu/'pytest.log'),aggregate_summary_location=str(cpu/'results.xml'),gate_decision_location=str(cpu/'GATE.json')),indent=2)+'\n')
with (cpu/'pytest.log').open('x') as f:r=subprocess.run(argv,env=env,cwd=S,stdout=f,stderr=subprocess.STDOUT)
(cpu/'GATE.json').write_text(json.dumps(dict(gate='PASS' if r.returncode==0 else 'FAIL_PRESERVED',source_commit=commit,returncode=r.returncode,GPU_calls=0),indent=2)+'\n');assert r.returncode==0
cmd=[sys.executable,'-B','-u',str(S/'audit_context.py'),'--study',str(study),'--out',str(D),'--source-manifest',str(A/'CONTEXT_SOURCE_v6.json'),'--model',str(B/'models/whisper-base.en')]
log=O/'paid_native_context_capacity_audit_v1_controller.log'
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc')/str(child.pid);r=dict(experiment_id='REVTRACE-INDEPENDENT-CONTEXT-AUDIT-V6',source_commit=commit,pid=child.pid,linux_start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=cmd,result=str(D),controller_log=str(log),launched_unix=time.time(),GPU_calls=0)
H.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
'''
 if V=='v7':
  for old,new in [('CONTEXT_SOURCE_v6','CONTEXT_SOURCE_v7'),('CONTEXT_source_v6','CONTEXT_source_v7'),('context_analysis_v6','context_analysis_v7'),('context_source_cpu_v6','context_source_cpu_v7'),('79cb171b3fc0418b4f989294d4581b75fbd40393','5963b2cae6dc3955ae87855723a2698e06441dd7'),('audit_v1','audit_v2'),('CPU-V6','CPU-V7'),('AUDIT-V6','AUDIT-V7')]:script=script.replace(old,new)
 i,o,e=c.exec_command(B+'/envs/revbatch-cu128/bin/python -B -',timeout=40);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
 if rc:raise RuntimeError('audit gate failed, inspect without rerun')
 name='paid_native_context_capacity_audit_v1_HANDLE.json' if V=='v6' else 'paid_native_context_capacity_audit_v2_HANDLE.json'
 (L/name).write_text(json.dumps(json.loads(out),indent=2)+'\n')
finally:c.close()
