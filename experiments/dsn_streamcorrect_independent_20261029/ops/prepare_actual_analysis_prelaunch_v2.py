import datetime,hashlib,json,pathlib,platform,sys
F=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(F/'FINAL_SERVICE_v2_FROZEN.json')
raw=plan['raw_result_location']
assert raw.startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/')
for kind in ('PRIMARY','CONTENT'):
 cfg=F/f'FINAL_{kind}_ANALYSIS_v2_FROZEN.json';c=read(cfg)
 env=c['frozen_environment'] if kind=='CONTENT' else dict(python=sys.version,executable=sys.executable,platform=platform.platform(),stdlib_CPU_only=True,model_imported=False,gpu_launched=False)
 ep=F/f'FROZEN_{kind}_ANALYSIS_ENVIRONMENT_v2.json';assert not ep.exists();ep.write_text(json.dumps(env,indent=2)+'\n',encoding='utf-8')
 out=F/f'FINAL_{kind}_RESULTS_v2'
 r=dict(experiment_id=c['experiment_id'],code_commit=c['analysis_source_commit'],frozen_config=str(cfg.resolve()),frozen_config_sha256=sha(cfg),environment_record=str(ep.resolve()),environment_record_sha256=sha(ep),raw_result_location=raw,
   bounded_local_input_collection=str((F/'SERVICE_RESULTS_v1').resolve()),bounded_local_derived_output=str(out.resolve()),aggregate_summary_location=str((out/'SUMMARY.json').resolve()),gate_decision_location=str((out/'GATE.json').resolve()),
   source_manifest=str((F/'packages/ANALYSIS_SOURCE_v2.json').resolve()),source_manifest_sha256=sha(F/'packages/ANALYSIS_SOURCE_v2.json'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Independent CPU recount of existing complete16 service outputs; no new model/remote operations; endpoints frozen before execution.')
 p=F/f'{kind}_ANALYSIS_PRELAUNCH_v2.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(kind=kind,run_record=str(p.resolve()),run_record_sha256=sha(p),config_sha256=sha(cfg))))
