from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
L=Path(r'D:\VLA_QWEN\RevTrace\experiments\context_recovery_20261028');B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_freeze_boundary_20261027'
c=ssh_client()
try:
 sf=c.open_sftp();sf.get_channel().settimeout(30)
 for n in ['source_v10.tar.gz','source_v10.bundle','SOURCE_v10.json']:
  q=P+'/packages/CONTEXT_'+n
  try:
   with sf.open(q,'rb') as f:old=f.read()
  except FileNotFoundError:sf.put(str(L/n),q)
  else:assert hashlib.sha256(old).digest()==hashlib.sha256((L/n).read_bytes()).digest()
 script=r'''from pathlib import Path
import hashlib,importlib.metadata,json,os,platform,subprocess,sys,tarfile,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_freeze_boundary_20261027';A=P/'packages';O=B/'results/revtrace/freeze_boundary_20261027';S=P/'context_analysis_v9';D=O/'native_prompt_clarity_v1';H=O/'native_prompt_clarity_v1_HANDLE.json'
m=json.loads((A/'CONTEXT_SOURCE_v9.json').read_text());commit=m['code_commit'];assert commit=='fdd289943a237001e2a50e82c02d86c26de09a5f'
def git(*x):return subprocess.check_output(['git','-C',str(S),*x],stderr=subprocess.PIPE,text=True).strip()
if not S.exists():
 S.mkdir()
 with tarfile.open(A/'CONTEXT_source_v9.tar.gz') as t:
  for f in t.getmembers():assert not f.issym() and not f.islnk() and (S/f.name).resolve().is_relative_to(S)
  t.extractall(S,filter='data')
 git('init');git('config','core.autocrlf','false');git('fetch',str(A/'CONTEXT_source_v9.bundle'),'HEAD:refs/heads/frozen');git('symbolic-ref','HEAD','refs/heads/frozen');git('read-tree',commit)
assert git('rev-parse','HEAD')==commit and not git('status','--porcelain')
for f in m['files']:assert hashlib.sha256((S/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not D.exists() and not H.exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
ref=O/'native_strong_v10_v1';assert json.loads((ref/'SMOKE_SUMMARY.json').read_text())['execution_complete']
cpu=O/'context_source_cpu_v9';assert not cpu.exists();cpu.mkdir();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
argv=[sys.executable,'-B','-m','pytest','-c',str(S/'pytest.ini'),'-p','no:cacheprovider','--rootdir',str(S),'--confcutdir',str(S),'--basetemp',str(cpu/'tmp'),'--junitxml',str(cpu/'results.xml'),*[str(S/n) for n in ['test_analysis.py','test_context_probe.py','test_context_audit.py','test_native_prompt.py']],'-q']
environment=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['pytest','torch','transformers']});(cpu/'ENVIRONMENT.json').write_text(json.dumps(environment,indent=2)+'\n')
(cpu/'FREEZE.json').write_text(json.dumps(dict(experiment_id='REVTRACE-NATIVE-SCHEMA-CPU-V9',source_commit=commit,source_manifest_sha256=hashlib.sha256((A/'CONTEXT_SOURCE_v9.json').read_bytes()).hexdigest(),environment_sha256=hashlib.sha256((cpu/'ENVIRONMENT.json').read_bytes()).hexdigest(),argv=argv,raw_result_location=str(cpu/'pytest.log'),aggregate_summary_location=str(cpu/'results.xml'),gate_decision_location=str(cpu/'GATE.json')),indent=2)+'\n')
with (cpu/'pytest.log').open('x') as f:r=subprocess.run(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
(cpu/'GATE.json').write_text(json.dumps(dict(gate='PASS' if r.returncode==0 else 'FAIL_PRESERVED',source_commit=commit,returncode=r.returncode,GPU_calls=0),indent=2)+'\n');assert r.returncode==0
cmd=[sys.executable,'-B','-u',str(S/'native_prompt_probe.py'),'--out',str(D),'--source-manifest',str(A/'CONTEXT_SOURCE_v9.json'),'--runtime',str(P/'source_v10'),'--runtime-manifest',str(A/'SOURCE_v10.json'),'--config',str(A/'NATIVE_STRONG_CONFIG_v1.json'),'--model-manifest',str(A/'NATIVE_QWEN3_4B_ASSETS_v1.json'),'--reference',str(ref)]
log=O/'native_prompt_clarity_v1_controller.log'
with log.open('x') as f:child=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
q=Path('/proc')/str(child.pid);r=dict(experiment_id='REVTRACE-NATIVE-SCHEMA-CLARITY-PAID-20261028',source_commit=commit,pid=child.pid,linux_start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=hashlib.sha256(q.joinpath('cmdline').read_bytes()).hexdigest(),argv=cmd,result=str(D),controller_log=str(log),launched_unix=time.time(),scope='eight paid first-request operators, no installs; unchanged sources and task scorer; no target answer supplied')
H.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
'''
 for old,new in [('context_analysis_v9','context_analysis_v10'),('CONTEXT_SOURCE_v9','CONTEXT_SOURCE_v10'),('CONTEXT_source_v9','CONTEXT_source_v10'),('context_source_cpu_v9','context_source_cpu_v10'),('fdd289943a237001e2a50e82c02d86c26de09a5f','93022eb9c308681f980ef266ee01a0104f5c5ca5'),('CPU-V9','CPU-V10')]:script=script.replace(old,new)
 script=script.replace("'test_context_audit.py','test_native_prompt.py'","'test_context_audit.py','test_native_prompt.py','test_anomaly_merge.py'")
 i,o,e=c.exec_command(B+'/envs/revtrace_native_20261027/bin/python -B -',timeout=45);i.write(script);i.channel.shutdown_write();out=o.read().decode();err=e.read().decode();rc=o.channel.recv_exit_status();print(out);print(err)
 if rc:raise RuntimeError('prompt probe gate failed, inspect before any new attempt')
 (L/'native_prompt_clarity_v1_HANDLE.json').write_text(json.dumps(json.loads(out),indent=2)+'\n')
finally:c.close()
