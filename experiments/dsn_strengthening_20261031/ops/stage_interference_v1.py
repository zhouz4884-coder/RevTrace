"""Immutable observation-probe staging and formal zero-NN prerequisites."""
import hashlib,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_20261031';O=B+'/results/revtrace/dsn_strengthening_20261031';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python';COMMIT='2198b8d517e068cb8a08e0bc022104b4fed4c8c7'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
gate=E/'INTERFERENCE_PRELAUNCH_ROOT_NOARG_v1.json';assert not gate.exists();r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);gate.write_bytes(r.stdout);assert read(gate)['code_commit']==COMMIT
index=read(E/'interference_inputs_v1/INPUT_INDEX_v1.json');freeze=read(E/'interference_packages_v1/FREEZE_INDEX_v1.json');pairs=[(pathlib.Path(x['local']),x['remote']) for x in index['files']]
pairs += [(pathlib.Path(freeze[k]['local']),freeze[k]['remote']) for k in ('source_manifest','source_bundle','shared_environment')]
pairs += [(E/'buffer_fixture_reaudit_inputs_v2/INPUT_INDEX_v2.json',P+'/INPUT_INDEX_v2.json'),(E/'interference_inputs_v1/INPUT_INDEX_v1.json',P+'/interference_inputs_v1/INPUT_INDEX_v1.json'),(gate,P+'/INTERFERENCE_PRELAUNCH_ROOT_NOARG_v1.json')]
script=r'''import pathlib,json,subprocess,sys,os,hashlib,platform,importlib.metadata,datetime,shutil
P=pathlib.Path(__PROJECT__);O=pathlib.Path(__OUTPUT__);PY=__PYTHON_BIN__;S=P/'interference_source_v1';M=P/'INTERFERENCE_SOURCE_v1.json';m=json.loads(M.read_bytes())
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip()
if not S.exists():
 subprocess.run(['git','clone','-q','--no-checkout',str(P/'INTERFERENCE_SOURCE_v1.bundle'),str(S)],check=True);subprocess.run(['git','-C',str(S),'config','core.autocrlf','false'],check=True);subprocess.run(['git','-C',str(S),'checkout','-q',m['source_commit']],check=True)
sys.path.insert(0,str(S));from common import read,put,sha,need,verify_checkout,root_preflight_receipt,B
identity=verify_checkout(S,M,__COMMIT__);planpath=P/'interference_inputs_v1/INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json';need(sha(planpath)==__PLANSHA__,'frozen probe plan changed');plan=read(planpath);shared=read(plan['environment_record']);need(sha(plan['environment_record'])==plan['environment_sha256'],'frozen shared environment changed')
root_receipt=P/'INTERFERENCE_PRELAUNCH_ROOT_NOARG_v1.json';root_preflight_receipt(root_receipt,sha(root_receipt),identity['source_commit'],sha(M))
for dep in plan['dependencies'].values():verify_checkout(dep['source_root'],dep['source_manifest'],dep['source_commit'])
for package,version in shared['packages'].items():need(importlib.metadata.version(package)==version,'actual environment package differs: '+package)
need(pathlib.Path(sys.executable).resolve()==pathlib.Path(plan['environment_python']).resolve(),'wrong interpreter');need(shutil.disk_usage(B).free>100*1024**3,'insufficient experiment disk')
root=O/'interference_readiness_v1';root.mkdir(exist_ok=False);live=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),source=identity,shared_environment_sha256=plan['environment_sha256'],packages={k:importlib.metadata.version(k) for k in shared['packages']},trained_model_calls=0)
def begin(name,experiment,extra):
 out=root/name;out.mkdir();put(out/'CONFIG.json',dict(experiment_id=experiment,**extra));put(out/'ENVIRONMENT.json',live);put(out/'RUN_RECORD.json',dict(experiment_id=experiment,code_commit=identity['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')));return out
out=begin('linux98','SC_INTERFERENCE_FORMAL_LINUX98_V1',dict(expected_tests=98,source_manifest_sha256=sha(M),real_original_coordinator_differential_required=True));tmp=out/'tmp';tmp.mkdir();base=plan['dependencies']['final']['source_root']
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',TMPDIR=str(tmp),REVTRACE_CPU_SCRATCH=str(tmp),REVTRACE_NN_SOURCE=base,REVTRACE_CORE_SOURCE=base,REVTRACE_RESIDENT_PLAN=str(P/'RESIDENT4_v2_FROZEN.json'),REVTRACE_STRENGTHENING_EVIDENCE=str(P),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
modules=['test_interference','test_interference_identity','test_interference_prerequisites','test_buffer_reaudit_prerequisite','test_interference_supervisor','test_controls','test_supervisor_cleanup']
code="import json,unittest; names="+repr(modules)+";s=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in names);r=unittest.TextTestRunner(verbosity=2).run(s);print(json.dumps(dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped),successful=r.wasSuccessful())));raise SystemExit(0 if r.wasSuccessful() and r.testsRun==98 and not r.skipped else 1)"
r=subprocess.run([sys.executable,'-B','-c',code],cwd=S,capture_output=True,env=env,timeout=240);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);result=json.loads(r.stdout.splitlines()[-1]);gate=dict(status='PASS_FORMAL_INTERFERENCE98_LINUX_CPU_ZERO_SKIP' if r.returncode==0 else 'FAIL_FORMAL_INTERFERENCE_CPU_PRESERVED',source_commit=identity['source_commit'],source_manifest_sha256=sha(M),shared_environment_sha256=plan['environment_sha256'],new_neural_calls=0,**result);gate['real_original_coordinator_differential_pass']=b'test_actual_original_policy_state_and_proposals_unchanged' in r.stderr and r.returncode==0;put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate);need(r.returncode==0 and gate['real_original_coordinator_differential_pass'],'formal Linux98/differential failed');cpu=out/'GATE.json'
out=begin('real_os','SC_INTERFERENCE_REAL_OS_GROUP_CONTROL_V1',dict(CUDA_response_synthetic=True,GPU_or_NVML_checked=False));r=subprocess.run([sys.executable,'-B',str(S/'linux_cleanup_control.py')],cwd=S,capture_output=True,env=env,timeout=45);(out/'stdout.log').write_bytes(r.stdout);(out/'stderr.log').write_bytes(r.stderr);need(r.returncode==0,'real OS orphan control failed');g=json.loads(r.stdout.splitlines()[-1]);need(g['GPU_or_NVML_checked'] is False and g['CUDA_owner_query_was_synthetic'] is True and g['confirmed_no_executing_members'] is True,'OS control scope changed');g.update(source_commit=identity['source_commit'],source_manifest_sha256=sha(M),shared_environment_sha256=plan['environment_sha256']);put(out/'SUMMARY.json',g);put(out/'GATE.json',g);osgate=out/'GATE.json'
out=begin('live_assets','SC_INTERFERENCE_LIVE_MODEL26_FULL_HASH_V1',dict(asset_manifest_sha256=shared['assets_manifest_sha256'],hash_algorithm='full SHA256, no sampling'));need(sha(shared['assets_manifest_path'])==shared['assets_manifest_sha256'],'registered model manifest changed');configs=[read(c['config']) for c in plan['cells']];models=configs[0]['settings']['backend']['contract']['model_assets'];need(len(models)==26,'model26 partition differs');expected=dict(models)
for cfg in configs:
 need(cfg['settings']['backend']['contract']['model_assets']==models,'model asset sets differ between policies')
 for wav in cfg['settings']['model_sources']:expected[wav['path']]=dict(bytes=pathlib.Path(wav['path']).stat().st_size,sha256=wav['audio_sha256'])
rows=[]
with (out/'RAW_FULL_FILE_HASHES.jsonl').open('x',encoding='utf8') as stream:
 for path,info in sorted(expected.items()):
  p=pathlib.Path(path);need(p.resolve().is_relative_to(pathlib.Path(B).resolve()),'asset outside designated disk');need(p.stat().st_size==info['bytes'] and sha(p)==info['sha256'],'actual full model/audio bytes differ: '+path);row=dict(path=path,bytes=info['bytes'],sha256=info['sha256'],is_model_contract=path in models);rows.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
backend=configs[0]['settings']['backend'];author=pathlib.Path(backend['author_root']);head=subprocess.check_output(['git','-C',str(author),'rev-parse','HEAD'],text=True).strip();dirty=subprocess.check_output(['git','-C',str(author),'status','--porcelain','--untracked-files=all'],text=True).strip();need(head==shared['author_source_commit'] and not dirty and sha(author/'simul_whisper/simul_whisper.py')==backend['contract']['author_whisper_sha256'],'author source identity differs')
devices=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total,memory.used','--format=csv,noheader,nounits'],text=True,timeout=10);need('GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a' in devices and 'GPU-a696ce9a-7137-cf6f-b4d3-deb992a72f28' in devices,'physical GPU identity differs');need(not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True,timeout=10).strip(),'GPU occupied before probe')
assetgate=dict(status='PASS_INTERFERENCE_LIVE_MODEL26_AUDIO_AND_AUTHOR_BYTES',all_asset_bytes_verified=True,asset_manifest_sha256=shared['assets_manifest_sha256'],model_contract_files=26,full_files_hashed=len(rows),total_bytes=sum(r['bytes'] for r in rows),author_commit=head,author_dirty=False,source_commit=identity['source_commit'],shared_environment_sha256=plan['environment_sha256'],GPU_snapshot=devices,new_neural_calls=0);put(out/'SUMMARY.json',assetgate);put(out/'GATE.json',assetgate);asset=out/'GATE.json'
from buffer_reaudit_prerequisite import collect_receipts
from interference_prerequisites import validate_prior_scopes
prior=dict(paired32_summary=dict(path=str(O/'paired32_v2/SUMMARY.json'),sha256=sha(O/'paired32_v2/SUMMARY.json')),resident4_summary=dict(path=str(O/'resident4_v2/SUMMARY.json'),sha256=sha(O/'resident4_v2/SUMMARY.json')),buffer4_reaudit=collect_receipts(str(P/'BUFFER4_POSTHOC_REAUDIT_v2_FROZEN.json'),str(P/'INPUT_INDEX_v2.json'),str(O/'reader_linux_cpu_v2/GATE.json')))
priorgate=validate_prior_scopes(prior);put(root/'PRIOR_SCOPE_GATE.json',priorgate)
pre=dict(root_noarg_preflight=str(root_receipt),root_noarg_preflight_sha256=sha(root_receipt),exclusive_GPU_window_authorized_by_root=True,asset_byte_gate=dict(path=str(asset),sha256=sha(asset)),formal_interference_CPU_gate=dict(path=str(cpu),sha256=sha(cpu)),real_OS_gate=dict(path=str(osgate),sha256=sha(osgate)),prior_scope_completion=prior,source_commit=identity['source_commit'],source_manifest_sha256=sha(M),frozen_probe_plan_sha256=sha(planpath),new_neural_calls=0);target=P/'INTERFERENCE_PRELAUNCH_v1.json';put(target,pre)
verify_checkout(S,M);put(root/'SUMMARY.json',dict(status='PASS_INTERFERENCE_FORMAL_READINESS_NO_NN',CPU98=gate,OS_scope=g,model_asset_gate_sha256=sha(asset),prior_scope_gate_sha256=sha(root/'PRIOR_SCOPE_GATE.json'),prelaunch=str(target),prelaunch_sha256=sha(target)));put(root/'GATE.json',dict(status='PASS_INTERFERENCE_FORMAL_READINESS_NO_NN',new_neural_calls=0));print(json.dumps(dict(status='PASS_INTERFERENCE_FORMAL_READINESS_NO_NN',prelaunch=str(target),prelaunch_sha256=sha(target),CPU98=gate,assetgate=assetgate)))
'''.replace('__PROJECT__',repr(P)).replace('__OUTPUT__',repr(O)).replace('__PYTHON_BIN__',repr(PY)).replace('__COMMIT__',repr(COMMIT)).replace('__PLANSHA__',repr(sha(E/'interference_inputs_v1/INTERFERENCE_OPPORTUNITY4_v1_FROZEN.json')))
compile(script,'remote_interference_formal_readiness','exec')
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);need=o.read().strip();assert not need and o.channel.recv_exit_status()==0
 s=c.open_sftp();made=set()
 for local,remote in pairs:
  data=local.read_bytes();folder=pathlib.PurePosixPath(remote).parent
  for parent in [*reversed(folder.parents),folder]:
   if str(parent) in made or not str(parent).startswith(B):continue
   try:s.stat(str(parent))
   except FileNotFoundError:s.mkdir(str(parent))
   made.add(str(parent))
  try:
   with s.open(remote,'rb') as f:assert f.read()==data,'existing immutable bytes differ: '+remote
  except FileNotFoundError:
   with s.open(remote,'wx') as f:f.write(data);f.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=480);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(E/'INTERFERENCE_FORMAL_READINESS_STDOUT_v1.json').write_bytes(stdout);(E/'INTERFERENCE_FORMAL_READINESS_STDERR_v1.txt').write_bytes(stderr);print(stdout.decode());assert rc==0,stderr.decode()
finally:c.close()
