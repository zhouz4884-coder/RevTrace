"""Execute only after the root allocates the profile GPU window."""
import pathlib,json,hashlib,subprocess,sys,os,datetime
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_stage_profile_20261029';O=B/'results/revtrace/dsn_streamcorrect_stage_profile_20261029'
assert json.loads((O/'PREREQUISITE_GATE_v1.json').read_text())['status']=='PASS_FROZEN_STAGE_SOURCE_DEPENDENCIES_AND_SAME_ENV_CPU_ONLY'
assert hashlib.sha256((P/'PLAN_v1_FROZEN.json').read_bytes()).hexdigest()=='402963085669343d6179d38b8b92b6db639ddc9777471e0a8ec922595c29cc21'
assert hashlib.sha256((P/'SOURCE_v1.json').read_bytes()).hexdigest()=='8c49ab116a36db8c810034932c6d60103587bba6754f466bd55401a481c0823d'
assert json.loads((B/'results/revtrace/dsn_streamcorrect_20261028/native_campaign_v8_continuation_auditfix_v1/GATE.json').read_text())['status']=='PASS_TWELVE_ACTUAL_NATIVE_CELLS_AND_FULL_HISTORY_EQUIVALENCE'
assert json.loads((B/'results/revtrace/physical_retirement_20261028/dsn_midpoint_controller_v1/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied'
handle=O/'HANDLE_v1.json';assert not handle.exists();assert not (O/'campaign_v1').exists()
command=[sys.executable,'-B',str(P/'source_v1/run_stage_profile.py'),'--plan',str(P/'PLAN_v1_FROZEN.json'),'--manifest',str(P/'SOURCE_v1.json'),'--out',str(O/'campaign_v1')]
log=O/'campaign_v1.log'
with log.open('x') as f:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit='41dea9bb6666e2c7397b394fb1c7a4a58b27888f',plan_sha256=hashlib.sha256((P/'PLAN_v1_FROZEN.json').read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((P/'SOURCE_v1.json').read_bytes()).hexdigest(),log=str(log),out=str(O/'campaign_v1'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
handle.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
