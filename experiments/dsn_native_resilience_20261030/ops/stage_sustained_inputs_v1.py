"""Stage only new immutable sustained8 configs; reuse real operator CPU identity."""
import argparse,hashlib,json,pathlib,shlex,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--plan',type=pathlib.Path,default=F/'FORMAL_SUSTAINED8_v1_FROZEN.json');a=p.parse_args()
if not a.execute:print(json.dumps(dict(status='DRY_RUN_NO_MUTATION',plan=str(a.plan),scope='No short85 bytes are uploaded to continuous-reference paths; source/operator CPU gates retain their original identities.')));raise SystemExit(0)
ready_path=F/'FORMAL_OPERATOR_PREREQUISITE_BYTES_v2.json';plan=read(a.plan);ready=read(ready_path);assert plan['campaign_kind']=='formal_sustained8' and plan['source_commit']==ready['neural_source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47';assert read(R/'experiments/repository_identity_20261027/CURRENT.json')['source_commit']==plan['source_commit']
pre=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);target=F/'SUSTAINED_INPUTS_ROOT_NOARG_v1.json';assert not target.exists();target.write_bytes(pre.stdout)
pairs=[(a.plan,P+'/'+a.plan.name)]
for cell in plan['cells']:
 remote=pathlib.PurePosixPath(cell['config']);local=F/remote.parent.name/remote.name;assert sha(local)==cell['config_sha256'];pairs.append((local,str(remote)))
script=r'''import pathlib,json,hashlib,subprocess,sys,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);pp=P/PLANNAME;plan=json.loads(pp.read_bytes());ready=json.loads((O/'FORMAL_OPERATOR_PREREQUISITE_v2.json').read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(pp)==PLANSHA and sha(O/'FORMAL_OPERATOR_PREREQUISITE_v2.json')==READYSHA and plan['campaign_kind']=='formal_sustained8'
sys.path.insert(0,str(P/'formal_operator_source_v2'));import run_campaign as op
op.gpu_empty();op.verify_checkout(P/'formal_operator_source_v2',P/'FORMAL_OPERATOR_SOURCE_v2.json',ready['operator_source_commit'],5);assert sha(ready['operator_CPU_gate'])==ready['operator_CPU_gate_sha256'];assert ready['tests']==26 and ready['skipped']==0
nnpre=O/'RUNTIME_PREREQUISITE_v2.json';assert sha(nnpre)==NNPRESHA;op.validate_inputs(pp,nnpre,NNPRESHA)
reference=json.loads(pathlib.Path(plan['reference_gate']).read_bytes());assert reference['source_commit']==plan['source_commit'] and reference['reference_full_calls']==reference['restored_full_calls']==875 and reference['all_original_full_state_C_IDs_equal']
record=dict(status='PASS_FROZEN_SUSTAINED8_INPUTS_AND_STRICT_CONTINUOUS_REFERENCE_NO_NN',experiment_id=plan['experiment_id']+'_INPUT_READINESS',neural_source_commit=plan['source_commit'],frozen_plan_sha256=sha(pp),operator_source_commit=ready['operator_source_commit'],operator_CPU_gate_sha256=ready['operator_CPU_gate_sha256'],operator_CPU_original_plan_sha256=ready['plan_sha256'],operator_CPU_readiness_sha256=sha(O/'FORMAL_OPERATOR_PREREQUISITE_v2.json'),neural_prerequisite_sha256=sha(nnpre),environment_sha256=plan['environment_sha256'],runtime_environment=plan['runtime_environment'],reference_details_sha256=plan['reference_details_sha256'],reference_gate_sha256=plan['reference_gate_sha256'],planned_cells=8,actual_serving_cells=0,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='New long inputs freshly validated; old operator CPU gate retains its own short-plan identity. Full continuous raw details stay on8TB and are never replaced by short85 data.')
target=O/'SUSTAINED_INPUTS_READY_v1.json';assert not target.exists();target.write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))
'''.replace('PROJECT',repr(P)).replace('OUTPUT',repr(O)).replace('PLANNAME',repr(a.plan.name)).replace('PLANSHA',repr(sha(a.plan))).replace('READYSHA',repr(sha(ready_path))).replace('NNPRESHA',repr(sha(F/'RUNTIME_PREREQUISITE_v2.json')))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15);assert not o.read().strip() and o.channel.recv_exit_status()==0,'NN owns host; defer immutable stage'
 s=c.open_sftp();dirs=set()
 for local,remote in pairs:
  folder=str(pathlib.PurePosixPath(remote).parent)
  if folder not in dirs:
   try:s.stat(folder)
   except FileNotFoundError:s.mkdir(folder)
   dirs.add(folder)
  with s.open(remote,'wx') as stream:stream.write(local.read_bytes());stream.flush()
 s.close();i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();assert o.channel.recv_exit_status()==0,stderr.decode();(F/'SUSTAINED_INPUTS_READY_STDOUT_v1.json').write_bytes(stdout)
 s=c.open_sftp()
 with s.open(O+'/SUSTAINED_INPUTS_READY_v1.json','rb') as stream:exact=stream.read()
 s.close();assert json.loads(exact)==json.loads(stdout);(F/'SUSTAINED_INPUTS_READY_v1.json').write_bytes(exact);print(stdout.decode())
finally:c.close()
