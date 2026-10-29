"""Root runs this only after CURRENT66/no-arg preflight and NN allocation."""
import pathlib,json,hashlib,sys,shlex
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029';ROOT=H.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_reference_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
planpath=I/'ORIGINAL_FULL_REFERENCE_PLAN_v1_FROZEN.json';plan=json.loads(planpath.read_bytes());current=json.loads((ROOT/'experiments/repository_identity_20261027/CURRENT.json').read_bytes())
assert current['source_commit']==plan['generator_source_commit']=='66abab7b8ce668a1a1ddefb65f6115af45e99cec'
assert current['source_manifest_sha256']==plan['generator_source_manifest_sha256']=='406c743e44eac2f9defe1d85de15c5b66bedec8d65f2f8249fb81b45ca355561'
assert sha(planpath)=='bf8dd4e8cc14ba4c23d6040f2502d80b5f45e426457ed49fd905dca3f4b66fe2'
assert not (I/'REFERENCE_HANDLE_v1.json').exists()
script="""import pathlib,json,hashlib,subprocess,sys,datetime,os
P=pathlib.Path(P_VALUE);O=pathlib.Path(O_VALUE);planpath=P/'REFERENCE_PLAN_v1_FROZEN.json';manifest=P/'GENERATOR_SOURCE_v1.json';plan=json.loads(planpath.read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(planpath)=='bf8dd4e8cc14ba4c23d6040f2502d80b5f45e426457ed49fd905dca3f4b66fe2'
assert sha(manifest)==plan['generator_source_manifest_sha256']
gate=O/'reference_cpu_v1/GATE.json';assert sha(gate)=='4d495ecfb10c5c391e68ca6663e8d93145dfbf5d5076ff9094e616fd91570ecd'
assert json.loads(gate.read_bytes())['status']=='PASS_REFERENCE_DATA_COMPLETE_SOURCE_ENVIRONMENT_AND_13_CPU_CONTROLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied: do not launch'
source=pathlib.Path(plan['generator_source_root']);assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==plan['generator_source_commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
assert not pathlib.Path(plan['raw_result_location']).exists() and not (O/'REFERENCE_HANDLE_v1.json').exists()
command=[sys.executable,'-B',str(source/'original_full_reference.py'),'--plan',str(planpath),'--manifest',str(manifest),'--out',plan['raw_result_location']];log=O/'reference_v1.log'
with log.open('x') as stream:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);record=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),command=command,
 generator_source_commit=plan['generator_source_commit'],imported_model_runtime_commit=plan['model_runtime_commit'],plan_sha256=sha(planpath),source_manifest_sha256=sha(manifest),CPU_gate_sha256=sha(gate),out=plan['raw_result_location'],log=str(log),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_only=True,actual_serving_cells=0,expected_original_full_calls=68)
(O/'REFERENCE_HANDLE_v1.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
""".replace('P_VALUE',repr(P)).replace('O_VALUE',repr(O))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(plan['environment_python'])+' -B -',timeout=20);i.write(script);i.flush();i.channel.shutdown_write();stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status();(I/'REFERENCE_LAUNCH_STDOUT_v1.txt').write_bytes(stdout);(I/'REFERENCE_LAUNCH_STDERR_v1.txt').write_bytes(stderr);assert rc==0,stderr.decode();record=json.loads(stdout);(I/'REFERENCE_HANDLE_v1.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record,indent=2))
finally:c.close()
