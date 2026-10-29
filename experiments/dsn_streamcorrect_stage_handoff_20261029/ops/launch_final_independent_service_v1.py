"""ROOT ONLY: launch after CURRENT bdfa/no-argument preflight and NN allocation."""
import pathlib,json,hashlib,sys,shlex,subprocess
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029';ROOT=H.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
PLAN_SHA='cab424783f30ff9b53db8deef5eba482d3b101f15336b65de8b1c7d9ced3679a';CPU_SHA='50f3e411a7bb6d0e3113b7eb01b2e5f5592f038c82322414260b184c23c4af6a'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
planpath=I/'FINAL_SERVICE_v2_FROZEN.json';plan=json.loads(planpath.read_bytes());assert sha(planpath)==PLAN_SHA
current=json.loads((ROOT/'experiments/repository_identity_20261027/CURRENT.json').read_bytes());assert current['source_commit']==plan['source_commit']=='bdfa3b1307d267a5a4caf6484e1ad465c39a592e';assert current['source_manifest_sha256']==sha(H/'packages/SOURCE_v3_LOCAL_PREFLIGHT.json')
assert not (I/'FINAL_SERVICE_HANDLE_v1.json').exists()
# Real no-argument preflight, not an inferred match from CURRENT text.
subprocess.run([sys.executable,'-B',str(ROOT/'experiments/repository_identity_20261027/preflight.py')],cwd=ROOT,check=True)
script="""import pathlib,json,hashlib,subprocess,sys,datetime,os
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);planpath=P/'FINAL_SERVICE_v2_FROZEN.json';plan=json.loads(planpath.read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(planpath)==PLAN_SHA
gate=O/'service_cpu_v1/GATE.json';assert sha(gate)==CPU_SHA and json.loads(gate.read_bytes())['status']=='PASS_FINAL16_EXACT_CONFIG_REFERENCE_SOURCE_DATA_ENV_CPU_PREREQUISITE'
for k in ('source_manifest','environment_record','reference_details','original_reference_gate','old_task_fidelity_gate','final_method_freeze_record','metadata_selection','source_receipt','frozen_appraisal'):
 h={'environment_record':'environment_sha256','final_method_freeze_record':'final_method_freeze_sha256'}.get(k,k+'_sha256');assert sha(plan[k])==plan[h],k
for cell in plan['cells']:
 assert sha(cell['config'])==cell['config_sha256'];assert not pathlib.Path(cell['out']).exists() and not pathlib.Path(cell['log']).exists()
source=pathlib.Path(plan['source_root']);manifest=pathlib.Path(plan['source_manifest']);assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==plan['source_commit'];assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
for f in json.loads(manifest.read_bytes())['files']:assert sha(source/f['path'])==f['sha256'] and (source/f['path']).stat().st_size==f['bytes']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied; do not launch'
assert not pathlib.Path(plan['campaign_output']).exists() and not (O/'FINAL_SERVICE_HANDLE_v1.json').exists()
for suffix in ('cells','logs'):(O/'service_v1'/suffix).mkdir(parents=True,exist_ok=True)
command=[sys.executable,'-B',str(source/'run_service_campaign.py'),'--plan',str(planpath),'--manifest',str(manifest),'--out',plan['campaign_output']];log=O/'service_v1/controller.log'
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,source_commit=plan['source_commit'],plan_sha256=sha(planpath),source_manifest_sha256=sha(manifest),CPU_gate_sha256=sha(gate),out=plan['campaign_output'],log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),expected_actual_serving_cells=16,reference_only=False)
(O/'FINAL_SERVICE_HANDLE_v1.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
""".replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O)).replace('PLAN_SHA',repr(PLAN_SHA)).replace('CPU_SHA',repr(CPU_SHA))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(I/'FINAL_SERVICE_LAUNCH_STDOUT_v1.txt').write_bytes(stdout);(I/'FINAL_SERVICE_LAUNCH_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();record=json.loads(stdout);(I/'FINAL_SERVICE_HANDLE_v1.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record,indent=2))
finally:c.close()
