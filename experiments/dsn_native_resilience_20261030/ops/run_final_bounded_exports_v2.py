"""Frozen e94 exporter on all36 completed original raw trials; no model replay."""
import hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030/bounded_formal36_v2';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
M=F/'packages/FIGURE_TOOLS_SOURCE_v2.json';m=read(M);assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==m['source_commit'];pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=F/'FINAL_EXPORT36_ROOT_NOARG_v2.json';assert not target.exists();target.write_bytes(pre.stdout);plans=[F/'FORMAL_SHORT28_v1_FROZEN.json',F/'FORMAL_SUSTAINED8_v1_FROZEN.json']
script=r'''import pathlib,json,hashlib,subprocess,sys,os,platform,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);M=P/'FIGURE_TOOLS_SOURCE_v2.json';m=json.loads(M.read_bytes());S=P/'figure_tools_source_v2'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
assert sha(M)==MSHA and not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'FIGURE_TOOLS_SOURCE_v2.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==m['source_commit'];assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip();assert set(subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert (S/r['path']).stat().st_size==r['bytes'] and sha(S/r['path'])==r['sha256']
cells=[];plan_records=[]
for name,digest in PLANS:
 pp=P/name;assert sha(pp)==digest;plan=json.loads(pp.read_bytes());g=json.loads(pathlib.Path(plan['gate_decision_location']).read_bytes());assert g['status']=='PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE' and g['completed_cells']==plan['expected_cells'];assert plan['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47';cells.extend(plan['cells']);plan_records.append(dict(path=str(pp),sha256=digest))
assert len(cells)==len({c['cell_id'] for c in cells})==36;O.mkdir();(O/'cells').mkdir();(O/'logs').mkdir();cpu=O/'cpu';cpu.mkdir();tmp=cpu/'tmp';tmp.mkdir()
put=lambda p,x:p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
cfg=dict(experiment_id='SC_FORMAL36_BOUNDED_ORIGINAL_SERIES_EXPORT_V2',code_commit=m['source_commit'],actual_neural_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',plans=plan_records,expected_cases=36,new_model_calls=0);put(O/'CONFIG.json',cfg);put(O/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0));put(O/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(O/'CONFIG.json'),config_sha256=sha(O/'CONFIG.json'),environment_record=str(O/'ENVIRONMENT.json'),environment_sha256=sha(O/'ENVIRONMENT.json'),raw_result_location=[c['out'] for c in cells],aggregate_summary_location=str(O/'SUMMARY.json'),gate_decision_location=str(O/'GATE.json'),new_model_calls=0,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
cpu_cfg=dict(experiment_id='SC_FROZEN_E94_CPU5_LINUX_V2',code_commit=m['source_commit'],source_manifest_sha256=sha(M),expected_tests=5,new_model_calls=0);put(cpu/'CONFIG.json',cpu_cfg);put(cpu/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0));put(cpu/'RUN_RECORD.json',dict(experiment_id=cpu_cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(cpu/'CONFIG.json'),config_sha256=sha(cpu/'CONFIG.json'),environment_record=str(cpu/'ENVIRONMENT.json'),environment_sha256=sha(cpu/'ENVIRONMENT.json'),raw_result_location=str(cpu/'unittest.log'),aggregate_summary_location=str(cpu/'GATE.json'),gate_decision_location=str(cpu/'GATE.json'),new_model_calls=0))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp));harness="import io,json,unittest; suite=unittest.defaultTestLoader.discover('.',pattern='test_*.py'); stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite); print(stream.getvalue()); print(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful()))); raise SystemExit(0 if result.wasSuccessful() and result.testsRun==5 and not result.skipped else 1)"
r=subprocess.run([sys.executable,'-B','-c',harness],cwd=S,capture_output=True,env=env);(cpu/'unittest.log').write_bytes(r.stdout+r.stderr);test=json.loads(r.stdout.splitlines()[-1]);put(cpu/'GATE.json',dict(status='PASS_FROZEN_E94_CPU5_LINUX_ZERO_SKIP' if r.returncode==0 else 'FAIL_CPU_PRESERVED',code_commit=m['source_commit'],new_model_calls=0,**test));assert r.returncode==0 and test['tests']==5 and test['skipped']==0
results=[]
for i,cell in enumerate(cells):
 raw=pathlib.Path(cell['out']);original=pathlib.Path(cell['config']);assert sha(original)==cell['config_sha256'];assert json.loads(original.read_bytes())==json.loads((raw/'CONFIG.json').read_bytes());dest=O/'cells'/cell['cell_id'];command=[sys.executable,'-B',str(S/'export_bounded.py'),'--case-root',str(raw),'--runtime-source-root',str(P/'source_v2'),'--out',str(dest)]
 with (O/'logs'/(cell['cell_id']+'.stdout.log')).open('x') as out,(O/'logs'/(cell['cell_id']+'.stderr.log')).open('x') as err:r=subprocess.run(command,stdout=out,stderr=err,env=env)
 assert r.returncode==0,'completed-case bounded export failed; preserved output, no truncation';meta=json.loads((dest/'COLLECTION_METADATA.json').read_bytes());assert meta['raw_config_sha256']==sha(raw/'CONFIG.json') and meta['all_observed_rows_retained'];results.append(dict(cell_id=cell['cell_id'],bounded_dir=str(dest),metadata_sha256=sha(dest/'COLLECTION_METADATA.json'),original_config_sha256=cell['config_sha256'],echo_config_sha256=meta['raw_config_sha256'],counts=meta['counts']));put(O/'PROGRESS.json',dict(completed=i+1,planned=36,current=cell['cell_id']))
summary=dict(status='PASS_ALL36_BOUNDED_SERIES_AND_ORIGINAL_ENDPOINT_RECOUNTS',code_commit=m['source_commit'],actual_neural_source_commit=cfg['actual_neural_source_commit'],cases=36,CPU_controls=5,new_model_calls=0,plans=plan_records,results=results,scope='Full original observed series, all planned cells; no performance/visual point selection. Large original facts/logs stay on8TB. Semantic/forward-count claims require separate exact audits.')
put(O/'SUMMARY.json',summary);put(O/'GATE.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('results','plans')}))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('MSHA',repr(sha(M))).replace('PLANS',repr([(p.name,sha(p)) for p in plans]))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0,'NN owns host; no export IO'
 s=c.open_sftp()
 for local,remote in [(M,P+'/FIGURE_TOOLS_SOURCE_v2.json'),(F/'packages/FIGURE_TOOLS_SOURCE_v2.bundle',P+'/FIGURE_TOOLS_SOURCE_v2.bundle')]:
  data=local.read_bytes()
  try:
   with s.open(remote,'rb') as f:assert f.read()==data
  except FileNotFoundError:
   with s.open(remote,'wx') as f:f.write(data);f.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=600);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'FINAL_EXPORT36_STDOUT_v2.json').write_bytes(stdout);(F/'FINAL_EXPORT36_STDERR_v2.txt').write_bytes(stderr);assert rc==0,stderr.decode();print(stdout.decode())
finally:c.close()
