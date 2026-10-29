import pathlib,json,subprocess,sys,hashlib,datetime,os
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_streamcorrect_20261028';O=B/'results/revtrace/dsn_streamcorrect_20261028'
assert json.loads((O/'cpu_environment_pipeline_v8/STATUS.json').read_text())['status']=='PASS_READY_FOR_ROOT_SERIALIZED_NATIVE_GPU_WINDOW'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
sys.path.insert(0,str(P/'runtime_source_v8'));from native_service import verify_source
source=verify_source(P/'SOURCE_v8.json');assert source['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c'
plan=json.loads((P/'NATIVE_CAMPAIGN_v8_FROZEN.json').read_text());first=json.loads(pathlib.Path(plan['cells'][0]['config']).read_text())
cfg=dict(experiment_id='SC_NATIVE_TRITON_MEDIAN_API_REPAIR_GPU_GATE_V8',code_commit=source['source_commit'],backend=first['settings']['backend'],source=first['settings']['sources'][0],
 cache_root=str(B/'cache/revtrace_streamcorrect_20261028'),scope='same frozen v6 first-warmup ASR input; repeated legacy API failure; original Torch median oracle on both cards; finite-domain numerical and operator timing controls only',
 source_manifest_sha256=hashlib.sha256((P/'SOURCE_v8.json').read_bytes()).hexdigest(),preceding_failed_native_source_commit='a720d02a8cb81db6545d7d9ec6bdc31419dd091d')
config=P/'MEDIAN_GPU_GATE_v8_FROZEN.json';assert not config.exists();config.write_text(json.dumps(cfg,indent=2))
out=O/'median_gpu_gate_v8';handle=O/'MEDIAN_GPU_GATE_v8_HANDLE.json';log=O/'median_gpu_gate_v8.log';assert not out.exists() and not handle.exists() and not log.exists()
command=[sys.executable,'-B',str(P/'runtime_source_v8/run_median_gpu_gate.py'),'--config',str(config),'--manifest',str(P/'SOURCE_v8.json'),'--out',str(out)]
supervisor='''import subprocess,pathlib,json,sys
command=json.loads(sys.argv[1]);out=pathlib.Path(sys.argv[2]);r=subprocess.run(command)
if r.returncode and not (out/'GATE.json').exists():
 out.mkdir(parents=True,exist_ok=True);(out/'GATE.json').write_text(json.dumps(dict(status='FAIL_NATIVE_MEDIAN_GPU_CONTROL_PRESERVED',returncode=r.returncode)))
 if not (out/'SUMMARY.json').exists():(out/'SUMMARY.json').write_text(json.dumps(dict(status='FAIL_NATIVE_MEDIAN_GPU_CONTROL_PRESERVED',returncode=r.returncode,interpretation='Technical control execution failed; inspect persistent process log, no native serving conclusion')))
raise SystemExit(r.returncode)'''
with log.open('x') as f:child=subprocess.Popen([sys.executable,'-B','-c',supervisor,json.dumps(command),str(out)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
proc=pathlib.Path('/proc')/str(child.pid);r=dict(pid=child.pid,start_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=source['source_commit'],frozen_config=str(config),frozen_config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),out=str(out),log=str(log),control_command=command)
handle.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
