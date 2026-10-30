"""Launch exactly the frozen second pilot cell; no scheduling choices or clock rewriting."""
import hashlib,json,pathlib,subprocess,sys,shlex
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
planpath=F/'SHORT_PILOT_v1_FROZEN.json';plan=json.loads(planpath.read_bytes());cell=plan['cells'][1];pre=F/'RUNTIME_PREREQUISITE_v1_r2.json'
assert cell['arm']=='fullcall' and cell['fault_kind']=='none'
pointer=json.loads((R/'experiments/repository_identity_20261027/CURRENT.json').read_bytes());assert pointer['source_commit']==plan['source_commit']
check=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True);(F/'SECOND_CELL_ROOT_PREFLIGHT_v1.json').write_bytes(check.stdout)
record=dict(experiment_id=cell['cell_id'],actual_neural_source_commit=plan['source_commit'],frozen_config=cell['config'],config_sha256=cell['config_sha256'],source_manifest_sha256=plan['source_manifest_sha256'],environment_record=plan['environment_record'],environment_sha256=plan['environment_sha256'],prerequisite_sha256=sha(pre),raw_result_location=cell['out'],aggregate_summary_location=cell['out']+'/SUMMARY.json',gate_decision_location=cell['out']+'/GATE.json',scope='Root launcher only; actual runtime9492 executes the complete frozen second trial. No model result replay.')
p=F/'SECOND_CELL_PRELAUNCH_v1.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode())
script=r"""import pathlib,json,hashlib,subprocess,os,sys,datetime
P=pathlib.Path(PROJECT);O=pathlib.Path(OUTPUT);plan=json.loads((P/'SHORT_PILOT_v1_FROZEN.json').read_bytes());cell=plan['cells'][1]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(P/'SHORT_PILOT_v1_FROZEN.json')==PLAN_SHA and sha(O/'RUNTIME_PREREQUISITE_v1_r2.json')==PRE_SHA
pre=json.loads((O/'RUNTIME_PREREQUISITE_v1_r2.json').read_bytes());assert pre['tests']==249 and pre['skipped']==0 and pre['source_commit']==plan['source_commit']
assert sha(cell['config'])==cell['config_sha256']
sys.path.insert(0,plan['source_root']);from native_service import verify_source;assert verify_source(pathlib.Path(plan['source_manifest']))['source_commit']==plan['source_commit']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
for name in ('cells','logs'):(pathlib.Path(plan['raw_result_location'])/name).mkdir(parents=True,exist_ok=True)
assert not pathlib.Path(cell['out']).exists() and not pathlib.Path(cell['log']).exists()
cmd=[sys.executable,'-B',str(pathlib.Path(plan['source_root'])/'resilience_trial.py'),'--config',cell['config'],'--manifest',plan['source_manifest'],'--out',cell['out']]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1');env.pop('CUDA_VISIBLE_DEVICES',None)
with open(cell['log'],'x') as f:child=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=env)
proc=pathlib.Path('/proc')/str(child.pid);r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=cmd,source_commit=plan['source_commit'],plan_sha256=PLAN_SHA,config_sha256=cell['config_sha256'],prerequisite_sha256=PRE_SHA,cell_id=cell['cell_id'],out=cell['out'],log=cell['log'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cell_position=1,expected_campaign_cells=6)
handle=O/'SECOND_CELL_HANDLE_v1.json';assert not handle.exists();handle.write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps(r))
""".replace('PROJECT',repr('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_native_resilience_20261030')).replace('OUTPUT',repr('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030')).replace('PLAN_SHA',repr(sha(planpath))).replace('PRE_SHA',repr(sha(pre)))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=30);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(F/'SECOND_CELL_LAUNCH_STDOUT_v1.txt').write_bytes(stdout);(F/'SECOND_CELL_LAUNCH_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();(F/'SECOND_CELL_HANDLE_v1.json').write_bytes(stdout);print(stdout.decode())
finally:c.close()

