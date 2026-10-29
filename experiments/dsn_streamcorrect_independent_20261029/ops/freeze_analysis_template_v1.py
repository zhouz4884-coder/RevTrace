"""Freeze definitions/CPU controls now; bind service inputs only after all16."""
import datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];src=F/'analysis_source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip();tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=p,bytes=(src/p).stat().st_size,sha256=sha(src/p)) for p in tracked]
manifest=dict(source_commit=commit,code_commit=commit,files=files,scope='local offline final16/new4-speaker independent primary and actual-G text analysis; zero model/remote calls')
mp=F/'packages/ANALYSIS_SOURCE_v1.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
snap=F/'analysis_snapshot_v1';snap.mkdir(exist_ok=False)
for p in tracked:shutil.copyfile(src/p,snap/p)
bundle=F/'packages/ANALYSIS_SOURCE_v1.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
common=dict(analysis_source_commit=commit,actual_neural_source_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',
 expected_cells=16,expected_reference_calls=68,expected_full_fidelity_steps=272,expected_offered_frontiers=272,
 independent_acoustic_sources=4,fresh_repeats_per_arm_source=2,within_source_fresh_pairs=8,
 source_receipt=str((F/'SOURCE_RECEIPT_v1.json').resolve()),source_receipt_sha256=sha(F/'SOURCE_RECEIPT_v1.json'),
 metadata_selection=str((F/'METADATA_SELECTION_v1_FROZEN.json').resolve()),metadata_selection_sha256=sha(F/'METADATA_SELECTION_v1_FROZEN.json'),
 method_freeze=str((F.parent/'dsn_streamcorrect_stage_handoff_20261029/FINAL_NATIVE_METHOD_FREEZE_v1.json').resolve()),method_freeze_sha256='fb6a1f57aba24b4300d84b9c30cfc8828bcb86c0fd011db92d4023ef1519364d',
 appraisal=str((F/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json').resolve()),appraisal_sha256=sha(F/'FINAL_INDEPENDENT_APPRAISAL_v1_FROZEN.json'),
 reference_details=str((F/'REFERENCE_RESULTS_v1/DETAILS.json').resolve()),reference_gate=str((F/'REFERENCE_RESULTS_v1/GATE.json').resolve()),reference_gate_sha256='28aa26207c509a733db2a9ab95612c48a4b5a96d233faf4460fbaa88a0017524')
template=dict(status='TEMPLATE_ONLY_NOT_A_RECOUNT_OR_RESULT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 source_manifest_sha256=sha(mp),common=common,
 primary=dict(entrypoint='analyze_confirmation.py',required_late_bindings=['collection_root','collection_manifest_sha256','campaign_plan','campaign_plan_sha256','frozen_config_dir'],collection_schema=dict(all_bytes_equal=True,source_commit=common['actual_neural_source_commit'],files='rows{path,bytes,sha256}; flat cell_id/file and campaign/file paths')),
 content=dict(entrypoint='run_confirmation_content.py',required_late_bindings=['raw_result_location','inputs','cells','frozen_environment'],unchanged_endpoint_source_commit='c12803e3ab411ad7898a34a2e257fdee313df81c',max_input_bytes=134217728,max_output_bytes=33554432),
 rule='No execution until all16 original service cells, source manifest, frozen campaign/config/reference/collection byte receipts exist; inputs are mechanical hashes, no endpoint/source/criterion changes.')
tp=F/'FINAL_ANALYSIS_TEMPLATE_v1_FROZEN.json';assert not tp.exists();tp.write_text(json.dumps(template,indent=2)+'\n',encoding='utf-8')
out=F/'ANALYSIS_CPU_CONTROLS_v1';out.mkdir(exist_ok=False)
result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(src),'-p','test_*.py','-v'],capture_output=True,text=True,env=dict(__import__('os').environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''))
(out/'CPU_CONTROLS.log').write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0 and 'Ran 22 tests' in result.stderr and 'skipped' not in result.stderr
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
for row in files:assert sha(src/row['path'])==row['sha256']
env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,remote_operations=0,gpu_calls=0)
gate=dict(status='PASS_FROZEN_22_LOCAL_CPU_CONTROLS_NO_SERVICE_ANALYSIS_YET',tests=22,skips=0,code_commit=commit,source_manifest_sha256=sha(mp),template_sha256=sha(tp))
for name,obj in [('ENVIRONMENT.json',env),('GATE.json',gate),('RUN_RECORD.json',dict(experiment_id='SC_INDEPENDENT_FINAL_ANALYSIS_CPU_V1',code_commit=commit,config=str(tp.resolve()),config_sha256=sha(tp),environment=str((out/'ENVIRONMENT.json').resolve()),raw=str(out),gate=str(out/'GATE.json'),scope='CPU controls only; no new source neural/service outputs consumed'))]:
 (out/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,files=len(files),manifest_sha256=sha(mp),template_sha256=sha(tp),CPU_gate_sha256=sha(out/'GATE.json'))))
