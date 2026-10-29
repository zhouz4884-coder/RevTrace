"""One bounded import-only CPU inspection, after allocation; no model init."""
import pathlib,hashlib,json,subprocess,sys,shlex
T=pathlib.Path(__file__).resolve().parents[1];S=T/'identity_diagnostic_source_v2';P=T/'packages'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a],text=True).strip()
assert not git('status','--porcelain','--untracked-files=all');commit=git('rev-parse','HEAD')
manifest=dict(source_commit=commit,files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in git('ls-files').splitlines()])
mp=P/'IDENTITY_DIAGNOSTIC_SOURCE_v3.json';assert not mp.exists();mp.write_bytes(json.dumps(manifest,indent=2).encode())
snapshot=T/'identity_diagnostic_snapshot_v3';snapshot.mkdir()
for r in manifest['files']:(snapshot/r['path']).write_bytes((S/r['path']).read_bytes())
subprocess.run(['git','-C',str(S),'bundle','create',str((P/'IDENTITY_DIAGNOSTIC_SOURCE_v3.bundle').resolve()),'HEAD'],check=True)
program=(S/'diagnose.py').read_text(encoding='utf8')
config=dict(experiment_id='SC_STAGE_C7_IMPORT_CODE_IDENTITY_DIAGNOSTIC_V3',analysis_source_commit=commit,analysis_source_manifest_sha256=sha(mp),analysis_script_sha256=sha(S/'diagnose.py'),
 author_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f',adapter_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_stage_handoff_20261029/source_v1',
 adapter_source_commit='c7e403b4313ed1283dfea2af043116643e01a0f7',scope='load definitions only; no model construction, GPU, inference, or source mutation')
remote="""import pathlib,json,hashlib,sys,datetime,platform,subprocess,traceback,os
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_stage_handoff_20261029';out=O/'identity_diagnostic_v3';out.mkdir(exist_ok=False)
config=CONFIG_VALUE;program=PROGRAM_VALUE
def put(n,x):(out/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
put('CONFIG.json',config);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'))
put('RUN_RECORD.json',dict(experiment_id=config['experiment_id'],source_commit=config['analysis_source_commit'],source_manifest_sha256=config['analysis_source_manifest_sha256'],config_sha256=sha(out/'CONFIG.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'DETAILS.json'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
try:
 assert hashlib.sha256(program.encode()).hexdigest()==config['analysis_script_sha256']
 assert subprocess.check_output(['git','-C',config['adapter_root'],'rev-parse','HEAD'],text=True).strip()==config['adapter_source_commit']
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU still owned; do not overlap'
 scope={'__name__':'cpu_diagnostic'};exec(compile(program,'frozen_identity_diagnostic_v3.py','exec',dont_inherit=True),scope);r=scope['run'](config['author_root'],config['adapter_root']);put('DETAILS.json',r)
 summary=dict(status='PASS_CPU_IMPORT_ONLY_IDENTITY_DIAGNOSIS_RECORDED',models_constructed=0,gpu_launched=False,methods={k:{n:v[n] for n in ('loaded_vs_subset','loaded_vs_whole_module','subset_vs_whole_module','existing_guard_loaded_vs_subset')} for k,v in r['methods'].items()});put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(dict(out=str(out),gate_sha256=sha(out/'GATE.json'),summary=summary),ensure_ascii=False,indent=2))
except BaseException:
 (out/'failure.txt').write_text(traceback.format_exc());put('GATE.json',dict(status='FAIL_CPU_IMPORT_IDENTITY_DIAGNOSTIC_PRESERVED'));raise
""".replace('CONFIG_VALUE',repr(config)).replace('PROGRAM_VALUE',repr(program))
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python')+' -B -',timeout=60);i.write(remote);i.flush();i.channel.shutdown_write();out=o.read();err=e.read();rc=o.channel.recv_exit_status();(T/'IDENTITY_DIAGNOSTIC_STDOUT_v3.txt').write_bytes(out);(T/'IDENTITY_DIAGNOSTIC_STDERR_v3.txt').write_bytes(err);print(out.decode());print(err.decode(),file=sys.stderr);assert rc==0
finally:c.close()
