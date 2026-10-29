import pathlib,json,os,signal,hashlib,datetime
O=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028')
h=json.loads((O/'CPU_ENV_PIPELINE_v5_HANDLE.json').read_text());p=pathlib.Path('/proc')/str(h['pid'])
assert h['pid']==1631351 and h['start_ticks']==500131299
assert int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==h['start_ticks']
assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256']
status=json.loads((O/'cpu_environment_pipeline_v5/STATUS.json').read_text());assert status['status']=='WAITING_EXACT_ASSET_GATE'
os.kill(h['pid'],signal.SIGINT)
r=dict(status='WAITING_V5_SETUP_RETIRED_BEFORE_EXECUTION',reason='actual CPU config path-resolution preflight defect requires new frozen v6 source; no v5 model/source tests or inference started',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=h['pid'],start_ticks=h['start_ticks'])
(O/'CPU_ENV_PIPELINE_v5_RETIREMENT.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
