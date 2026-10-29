import datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];ROOT=F.parents[1];src=F/'source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
method=ROOT/'experiments/dsn_streamcorrect_stage_handoff_20261029/FINAL_NATIVE_METHOD_FREEZE_v1.json'
assert sha(method)=='fb6a1f57aba24b4300d84b9c30cfc8828bcb86c0fd011db92d4023ef1519364d'
meta=ROOT/'experiments/dsn_streamcorrect_adaptation_20261028/public_asset_metadata_v3/ARCHIVE_ENTRIES_0.json'
assert sha(meta)=='efd03c4e9ef086548d353ead2efacb826afcc6440e1c5b866faf79d8e176ccc4'
packages=F/'packages';packages.mkdir(exist_ok=True);tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=x,bytes=(src/x).stat().st_size,sha256=sha(src/x)) for x in tracked]
manifest=dict(source_commit=commit,files=files,scope='CPU metadata selection and exact public ZIP acquisition only; no neural model')
(packages/'SOURCE_v1.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(packages/'SOURCE_v1_LOCAL_PREFLIGHT.json').write_text(json.dumps(dict(code_commit=commit,files=files),indent=2)+'\n',encoding='utf-8')
snap=F/'source_snapshot_v1';snap.mkdir(exist_ok=False)
for x in tracked:shutil.copyfile(src/x,snap/x)
bundle=packages/'SOURCE_v1.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
rule=dict(experiment_id='SC_INDEPENDENT4_METADATA_SELECTION_V1',selection_source_commit=commit,
 method_source_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',method_freeze=str(method.resolve()),method_freeze_sha256=sha(method),
 archive_index=str(meta.resolve()),archive_index_sha256=sha(meta),archive_public_url='https://huggingface.co/datasets/playwithmino/StreamCorrect/resolve/16f6fd1e17418f1c4111a18fdd39543813206d96/StreamCorrect.zip',
 seed=2026102931,excluded_speakers=['S0764','S0765','S0767','S0768'],
 predeclared_estimated_size_bands_seconds=[[8,9],[8,10],[8,15]],minimum_eligible_speakers=4,
 estimated_duration_rule='(ZIP uncompressed WAV member bytes -44)/32000; no WAV headers/content read',
 speaker_selection='uniform without replacement from sorted eligible speakers; preserve random draw order',
 source_selection='one uniform member from each sorted speaker pool; fixed cyclic lexicographic technical-header fallback order',
 source_reselection='No compatibility/quality/performance/output criterion; network/CRC errors may not change member. Only technical header failure advances predeclared same-speaker candidate.',
 selection_output=str((F/'METADATA_SELECTION_v1_FROZEN.json').resolve()),
 created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
rp=F/'SELECTION_RULE_v1_FROZEN.json';assert not rp.exists();rp.write_text(json.dumps(rule,indent=2)+'\n',encoding='utf-8')
env=F/'FROZEN_SELECTION_ENVIRONMENT_v1.json';env.write_text(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),scope='standard-library CPU selection only; no Torch/models'),indent=2)+'\n',encoding='utf-8')
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
record=dict(experiment_id=rule['experiment_id'],code_commit=commit,frozen_config=str(rp.resolve()),frozen_config_sha256=sha(rp),environment_record=str(env.resolve()),environment_record_sha256=sha(env),raw_result_location=B+'/results/revtrace/dsn_streamcorrect_independent_20261029/metadata_selection_v1',aggregate_summary_location=str((F/'METADATA_SELECTION_v1_FROZEN.json').resolve()),gate_decision_location=str((F/'METADATA_SELECTION_v1_FROZEN.json').resolve()),scope='Bounded metadata plan generation; source WAV bytes remain unread')
(F/'SELECTION_RUN_PRELAUNCH_v1.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json';backup=F/'CURRENT_BEFORE_DATA_SELECTION_v1.json';assert not backup.exists();shutil.copyfile(pointer,backup)
p=json.loads(pointer.read_text(encoding='utf-8'));p.update(source_worktree=str(src.resolve()),source_commit=commit,source_manifest=str((packages/'SOURCE_v1_LOCAL_PREFLIGHT.json').resolve()),source_manifest_sha256=sha(packages/'SOURCE_v1_LOCAL_PREFLIGHT.json'),research_state=str((F/'CURRENT_STATUS.json').resolve()),GPU_queue='CPU_ONLY_METADATA_AND_FOUR_PUBLIC_RANGES_NO_NEURAL',previous_pointer=str(backup.resolve()),scope='Machine-local CPU acquisition source pointer; final native METHOD remains separately frozen bdfa before new metadata.')
pointer.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,rule_sha256=sha(rp),files=len(files),no_WAV_or_transcripts_read=True)))
