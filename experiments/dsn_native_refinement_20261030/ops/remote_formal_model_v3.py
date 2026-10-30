"""Root-authorized formal CPU specification on designated8TB, never neural."""
import argparse,hashlib,json,pathlib,shlex,sys,time
F=pathlib.Path(__file__).resolve().parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_native_refinement_20261030'
O=B+'/results/revtrace/dsn_native_refinement_20261030'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--action',choices=('stage_launch','status','collect'),required=True);a=p.parse_args()
manifest=F/'packages/SOURCE_v3.json';plan=F/'MODEL_PLAN_v3_FROZEN.json';bundle=F/'packages/SOURCE_v3.bundle'
m=json.loads(manifest.read_bytes());commit=m['source_commit']
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
def remote(code):
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=90);i.write(code);i.flush();i.channel.shutdown_write()
 output=o.read();err=e.read();rc=o.channel.recv_exit_status()
 if rc:raise RuntimeError(err.decode()+'\n'+output.decode())
 return output
try:
 if a.action=='stage_launch':
  gate=json.loads((F/'ROOT_MODEL_PREFLIGHT_v3.json').read_bytes());assert gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']==commit
  script="""import pathlib
B=pathlib.Path(B_VALUE)
for value in (P_VALUE,O_VALUE):
 p=pathlib.Path(value);assert p.resolve().is_relative_to(B.resolve());p.mkdir(parents=True,exist_ok=True)
print('bounded specification directories ready')
""".replace('B_VALUE',repr(B)).replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O))
  remote(script)
  s=c.open_sftp()
  try:
   for local,name in [(manifest,'SOURCE_v3.json'),(plan,'MODEL_PLAN_v3_FROZEN.json'),(bundle,'SOURCE_v3.bundle')]:
    target=P+'/'+name;data=local.read_bytes()
    try:
     with s.open(target,'rb') as f:assert f.read()==data
    except FileNotFoundError:
     with s.open(target,'wb') as f:f.write(data)
  finally:s.close()
  script="""import pathlib,json,hashlib,subprocess,sys,os,platform,datetime
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);source=P/'source_v3';manifest=P/'SOURCE_v3.json';planpath=P/'MODEL_PLAN_v3_FROZEN.json'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(manifest)==MANIFEST_SHA and sha(planpath)==PLAN_SHA and sha(P/'SOURCE_v3.bundle')==BUNDLE_SHA
m=json.loads(manifest.read_bytes());plan=json.loads(planpath.read_bytes())
assert m['source_commit']==plan['source_commit']==COMMIT
if not source.exists():
 subprocess.run(['git','clone','--no-checkout',str(P/'SOURCE_v3.bundle'),str(source)],check=True,capture_output=True)
 subprocess.run(['git','-C',str(source),'config','core.autocrlf','false'],check=True)
 subprocess.run(['git','-C',str(source),'checkout',COMMIT],check=True,capture_output=True)
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==COMMIT
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert set(subprocess.check_output(['git','-C',str(source),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for row in m['files']:assert (source/row['path']).stat().st_size==row['bytes'] and sha(source/row['path'])==row['sha256']
env=O/'PRELAUNCH_ENVIRONMENT_v3.json';record=O/'PRELAUNCH_RECORD_v3.json';handle=O/'MODEL_HANDLE_v3.json';out=O/'formal_model_v3'
assert not env.exists() and not record.exists() and not handle.exists() and not out.exists()
environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),code_commit=COMMIT,source_files=len(m['files']),models_or_GPU_calls=0,scope='Formal bounded symbolic CPU specification only; no Torch/import/model/data serving')
env.write_bytes((json.dumps(environment,indent=2)+'\\n').encode())
record.write_bytes((json.dumps(dict(experiment_id=plan['experiment_id'],code_commit=COMMIT,frozen_config=str(planpath),frozen_config_sha256=sha(planpath),environment_record=str(env),environment_record_sha256=sha(env),source_manifest_sha256=sha(manifest),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),scope=plan['scope']),indent=2)+'\\n').encode())
command=[sys.executable,'-B',str(source/'run_checks.py'),'--plan',str(planpath),'--manifest',str(manifest),'--out',str(out)]
log=O/'formal_model_v3_controller.log';assert not log.exists()
with log.open('x') as f:
 child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
proc=pathlib.Path('/proc')/str(child.pid)
r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),source_commit=COMMIT,manifest_sha256=sha(manifest),plan_sha256=sha(planpath),prelaunch_environment_sha256=sha(env),prelaunch_record_sha256=sha(record),out=str(out),log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),models_or_GPU_launched=False)
handle.write_bytes((json.dumps(r,indent=2)+'\\n').encode());print(json.dumps(r))
""".replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('MANIFEST_SHA',repr(sha(manifest))).replace('PLAN_SHA',repr(sha(plan))).replace('BUNDLE_SHA',repr(sha(bundle))).replace('COMMIT',repr(commit))
  data=remote(script);(F/'FORMAL_LAUNCH_STDOUT_v3.json').write_bytes(data);print(data.decode())
 else:
  script="""import pathlib,json,hashlib,datetime
O=pathlib.Path(O_VALUE);handle=json.loads((O/'MODEL_HANDLE_v3.json').read_bytes());proc=pathlib.Path('/proc')/str(handle['pid'])
exists=proc.exists();state=None;exact=True
if exists:
 tail=(proc/'stat').read_text().rsplit(')',1)[1].split();state=tail[0]
 exact=int(tail[19])==handle['start_ticks']
 if state!='Z':exact=exact and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==handle['cmdline_sha256']
 assert exact,'model PID identity changed; never restart from timeout'
gate=pathlib.Path(handle['out'])/'GATE.json';r=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exact_identity=exact,controller_alive=exists and state!='Z',state=state,handle=handle)
if gate.exists():r.update(gate=json.loads(gate.read_bytes()),gate_sha256=hashlib.sha256(gate.read_bytes()).hexdigest())
if COLLECT:
 assert not r['controller_alive'] and gate.exists(),'formal model still running/incomplete; do not collect'
 files=[]
 for f in sorted(pathlib.Path(handle['out']).glob('*')):
  if f.is_file():
   data=f.read_bytes();assert len(data)<2_000_000
   files.append(dict(path=f.name,remote=str(f),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 for name in ['PRELAUNCH_ENVIRONMENT_v3.json','PRELAUNCH_RECORD_v3.json','MODEL_HANDLE_v3.json','formal_model_v3_controller.log']:
  f=O/name;data=f.read_bytes();files.append(dict(path='launch/'+name,remote=str(f),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 r['files']=files
print(json.dumps(r,indent=2))
""".replace('O_VALUE',repr(O)).replace('COLLECT',repr(a.action=='collect'))
  data=remote(script);r=json.loads(data);(F/'FORMAL_LATEST_STATUS_v3.json').write_bytes(data)
  if a.action=='collect':
   dest=F/'FORMAL_RESULTS_v3';dest.mkdir(exist_ok=False);s=c.open_sftp()
   try:
    for row in r['files']:
     target=dest/row['path'];target.parent.mkdir(parents=True,exist_ok=True);s.get(row['remote'],str(target))
     assert target.stat().st_size==row['bytes'] and sha(target)==row['sha256']
   finally:s.close()
   receipt=dict(all_bytes_equal=True,actual_source_commit=commit,controller_exited=True,models_or_GPU_launched=False,files=r['files'],gate_sha256=r['gate_sha256'])
   (dest/'COLLECTION_MANIFEST.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
   assert r['gate']['status']=='PASS_BOUNDED_SPECIFICATION_REFINEMENT_AND_COUNTEREXAMPLE_CONTROLS',r['gate']
  print(json.dumps(r,indent=2))
finally:c.close()

