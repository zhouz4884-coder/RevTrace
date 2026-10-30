"""Independent c4 checker on all fixed36 original8TB traces after NN release."""
import hashlib,json,pathlib,shlex,subprocess,sys
N=pathlib.Path(__file__).resolve().parents[1];R=N.parents[1];F=N.parent/'dsn_native_refinement_20261030';B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';Q=B+'/projects/revtrace_dsn_native_refinement_20261030';O=B+'/results/revtrace/dsn_native_refinement_20261030/formal_actual36_v1';P=B+'/projects/revtrace_dsn_native_resilience_20261030';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
M=F/'packages/TRACE_SOURCE_v2.json';m=read(M);assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==m['source_commit'];pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=N/'FORMAL_TRACE36_ROOT_NOARG_v1.json';assert not target.exists();target.write_bytes(pre.stdout)
plans=[N/'FORMAL_SHORT28_v1_FROZEN.json',N/'FORMAL_SUSTAINED8_v1_FROZEN.json'];assert [read(x)['expected_cells'] for x in plans]==[28,8]
pairs=[(M,Q+'/packages/TRACE_SOURCE_v2.json'),(F/'packages/TRACE_SOURCE_v2.bundle',Q+'/packages/TRACE_SOURCE_v2.bundle'),(F/'ops/bind_actual_trace_v1.py',Q+'/ops/bind_actual_trace_v1.py')]
script=r'''import pathlib,json,hashlib,subprocess,sys,os,datetime,platform
Q=pathlib.Path(PROJECT);P=pathlib.Path(NNPROJECT);O=pathlib.Path(OUTPUT);M=Q/'packages/TRACE_SOURCE_v2.json';S=Q/'trace_source_v2';m=json.loads(M.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
assert sha(M)==MSHA and sha(Q/'ops/bind_actual_trace_v1.py')==BINDERSHA
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'NN owns host; no heavy trace IO'
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(Q/'packages/TRACE_SOURCE_v2.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['source_commit'];assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip();assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (S/r['path']).stat().st_size==r['bytes'] and sha(S/r['path'])==r['sha256']
plans=[];cells=[]
for name,digest in PLANS:
 path=P/name;assert sha(path)==digest;plan=json.loads(path.read_bytes());assert plan['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47';gate=json.loads(pathlib.Path(plan['gate_decision_location']).read_bytes());assert gate['status']=='PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE' and gate['completed_cells']==plan['expected_cells'];plans.append(dict(path=str(path),sha256=digest));cells.extend(plan['cells'])
assert len(cells)==len({c['cell_id'] for c in cells})==36;O.mkdir();(O/'configs').mkdir();(O/'cases').mkdir();(O/'logs').mkdir();tmp=O/'tmp';tmp.mkdir()
put=lambda p,x:p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
cfg=dict(experiment_id='SC_FORMAL_ACTUAL36_INDEPENDENT_C4_TRACE_V1',checker_source_commit=m['source_commit'],actual_neural_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',plans=plans,expected_cases=36,input_mode='direct_original8TB_raw_not_local_copies',new_model_calls=0);put(O/'CONFIG.json',cfg);put(O/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',new_model_calls=0));put(O/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(O/'CONFIG.json'),config_sha256=sha(O/'CONFIG.json'),environment_record=str(O/'ENVIRONMENT.json'),environment_sha256=sha(O/'ENVIRONMENT.json'),raw_result_location=[c['out'] for c in cells],aggregate_summary_location=str(O/'SUMMARY.json'),gate_decision_location=str(O/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp));results=[]
for i,cell in enumerate(cells):
 cid=cell['cell_id'];config=O/'configs'/(cid+'.json');dest=O/'cases'/cid
 bind=[sys.executable,'-B',str(Q/'ops/bind_actual_trace_v1.py'),'--case-root',cell['out'],'--runtime-source-commit',cfg['actual_neural_source_commit'],'--output-config',str(config),'--experiment-id','TRACE_FORMAL36_V1_'+cid,'--original-raw-root',cell['out'],'--checker-version','2'];r=subprocess.run(bind,capture_output=True,env=env);(O/'logs'/(cid+'_bind.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,'input binding failed; original36 scope retained'
 with (O/'logs'/(cid+'.stdout.log')).open('x') as out,(O/'logs'/(cid+'.stderr.log')).open('x') as err:r=subprocess.run([sys.executable,'-B',str(S/'run_trace.py'),'--config',str(config),'--manifest',str(M),'--out',str(dest)],stdout=out,stderr=err,env=env)
 gate=json.loads((dest/'GATE.json').read_bytes());results.append(dict(cell_id=cid,returncode=r.returncode,gate=gate,gate_sha256=sha(dest/'GATE.json'),config_sha256=sha(config)));put(O/'PROGRESS.json',dict(completed=i+1,planned=36,current=cid,last_returncode=r.returncode))
summary=dict(status='PASS_ALL_FORMAL36_ACTUAL_ORIGINAL_FULLCALL_REFINEMENT' if all(r['returncode']==0 for r in results) else 'FAIL_FORMAL_TRACE_OR_SCHEMA_PRESERVED',checker_source_commit=m['source_commit'],actual_neural_source_commit=cfg['actual_neural_source_commit'],cases=36,results=results,new_model_calls=0,scope='Independent direct original8TB trace validation, all fixed36 cases; every case repeats frozen35 source controls. Not a CUDA/mechanized whole-program proof, human correctness, new NN run or unbounded liveness.')
put(O/'SUMMARY.json',summary);put(O/'GATE.json',summary);print(json.dumps(dict(status=summary['status'],cases=36,passing_cases=sum(r['returncode']==0 for r in results),checker_source_commit=m['source_commit'],new_model_calls=0)))
'''.replace('NNPROJECT',repr(P)).replace('PROJECT',repr(Q)).replace('OUTPUT',repr(O)).replace('MSHA',repr(sha(M))).replace('BINDERSHA',repr(sha(F/'ops/bind_actual_trace_v1.py'))).replace('PLANS',repr([(x.name,sha(x)) for x in plans]))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0,'NN owns host; defer trace source transfer'
 s=c.open_sftp()
 for folder in (Q,Q+'/packages',Q+'/ops'):
  try:s.stat(folder)
  except FileNotFoundError:s.mkdir(folder)
 for local,remote in pairs:
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as f:assert f.read()==data
  except FileNotFoundError:
   with s.open(remote,'wx') as f:f.write(data);f.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=600);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(N/'FORMAL_TRACE36_STDOUT_v1.json').write_bytes(stdout);(N/'FORMAL_TRACE36_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();print(stdout.decode())
finally:c.close()
