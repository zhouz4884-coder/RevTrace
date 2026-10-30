"""Formal pure-CPU controls and metadata lock; root has already selected this source."""
import datetime,hashlib,json,pathlib,platform,re,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];S=F/'source_v1';M=F/'packages/DATA_SOURCE_v1.json'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
cfg=read(F/'SELECTION_RULE_v1_FROZEN.json');identity=read(F/'ROOT_DATA_SELECTION_PREFLIGHT_v1.json')
assert identity['gate']=='SOURCE_IDENTITY_PASS' and identity['code_commit']==cfg['selection_source_commit']
current=read(R/'experiments/repository_identity_20261027/CURRENT.json')
assert current['source_commit']==cfg['selection_source_commit'] and current['source_manifest_sha256']==sha(M)
out=F/'CPU_RESULTS_v1';out.mkdir()
control=dict(experiment_id='SC_SUSTAINED_DATA_SOURCE_CPU_CONTROLS_V1',source_commit=cfg['selection_source_commit'],manifest_sha256=sha(M),tests_expected=18,source=str(S.resolve()),new_audio_read=False,new_model_calls=0)
put(out/'CONFIG.json',control);put(out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0))
put(out/'RUN_RECORD.json',dict(experiment_id=control['experiment_id'],code_commit=control['source_commit'],frozen_config=str(out/'CONFIG.json'),config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out/'CPU_CONTROLS.log'),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='synthetic standard-library CPU controls only, no new source audio or neural model'))
result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(S),'-p','test_*.py','-v'],capture_output=True)
(out/'CPU_CONTROLS.log').write_bytes(result.stdout+b'\n'+result.stderr)
tests=re.search(rb'Ran (\d+) tests?',result.stderr);ok=result.returncode==0 and tests and int(tests[1])==18 and b'skipped=' not in result.stderr
gate=dict(status='PASS_ALL18_SYNTHETIC_CPU_CONTROLS' if ok else 'FAIL_CPU_CONTROLS_PRESERVED',source_commit=control['source_commit'],tests=int(tests[1]) if tests else None,skipped=0,new_model_calls=0,new_audio_read=False)
put(out/'SUMMARY.json',gate);put(out/'GATE.json',gate)
if not ok:raise RuntimeError(result.stderr.decode('utf8',errors='replace'))
r=subprocess.run([sys.executable,'-B',str(S/'select_recipe.py'),'--config',str(F/'SELECTION_RULE_v1_FROZEN.json'),'--manifest',str(M)],capture_output=True)
(F/'SELECTION_STDOUT_v1.txt').write_bytes(r.stdout);(F/'SELECTION_STDERR_v1.txt').write_bytes(r.stderr)
assert r.returncode==0,r.stderr.decode('utf8',errors='replace')
selected=read(F/'METADATA_SELECTION_v1_FROZEN.json')
put(F/'METADATA_SELECTION_GATE_v1.json',dict(status=selected['status'],selection_sha256=sha(F/'METADATA_SELECTION_v1_FROZEN.json'),source_commit=control['source_commit'],speaker_ids=selected['selected_speakers'],fixed_members=48,synthetic_long_streams=2,CPU_controls=18,new_audio_read=False,new_reference_text_read=False,new_model_calls=0))
print(json.dumps(dict(status=selected['status'],selection_sha256=sha(F/'METADATA_SELECTION_v1_FROZEN.json'),speakers=selected['selected_speakers'],estimated_seconds={x['stream_id']:x['estimated_seconds'] for x in selected['recipes']},new_audio_read=False,new_model_calls=0)))

