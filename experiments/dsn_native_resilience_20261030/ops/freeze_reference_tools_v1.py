"""Freeze the independent CPU exporter and fixed prior inputs; no actual export."""
import datetime,hashlib,json,pathlib,shutil,subprocess,sys
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];H=F.parent/'dsn_streamcorrect_stage_handoff_20261029';I=F.parent/'dsn_streamcorrect_independent_20261029';S=F/'reference_tools_source_v1'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def run(*args):return subprocess.check_output(list(args),text=True).strip()
assert not (S/'.git').exists()
run('git','init','-q','-b','codex/prior-bdfa-short85-reference',str(S));run('git','-C',str(S),'config','core.autocrlf','false');run('git','-C',str(S),'config','user.name','RevTrace Research');run('git','-C',str(S),'config','user.email','research@revtrace.invalid');run('git','-C',str(S),'add','.');run('git','-C',str(S),'commit','-qm','Freeze independent prior-BDFA short85 reference exporter')
commit=run('git','-C',str(S),'rev-parse','HEAD');files=[dict(path=n,bytes=(S/n).stat().st_size,sha256=sha(S/n)) for n in run('git','-C',str(S),'ls-files').splitlines()];packages=F/'packages';packages.mkdir(exist_ok=True)
manifest=dict(source_commit=commit,code_commit=commit,files=files,scope='Independent CPU prior actual BDFA reference export only; no neural/performance replay.')
mp=packages/'REFERENCE_EXPORT_SOURCE_v1.json';put(mp,manifest);bundle=packages/'REFERENCE_EXPORT_SOURCE_v1.bundle';run('git','-C',str(S),'bundle','create',str(bundle.resolve()),'HEAD');run('git','-C',str(R),'fetch',str(bundle.resolve()),'HEAD:refs/research/dsn-prior-bdfa-short85-reference-v1')
snap=F/'reference_tools_snapshot_v1';snap.mkdir()
for row in files:(snap/row['path']).write_bytes((S/row['path']).read_bytes())
old=H/'SERVICE_CONFIRMATION_RESULTS_v1/SC_STAGE_SERVICE_CONFIRM_V1_two_full_early_BAC009S0764W0209_r0'
mapping={'old_config':old/'CONFIG.json','old_run_record':old/'RUN_RECORD.json','old_gate':old/'GATE.json','old_jobs':old/'native_jobs.jsonl','old_histories':old/'CANONICAL_HISTORIES.json','old_wal':old/'canonical_wal.jsonl','old_dispatch':old/'DISPATCHES.json','old_events':old/'events.jsonl','new_reference_details':I/'REFERENCE_RESULTS_v1/DETAILS.json','new_reference_gate':I/'REFERENCE_RESULTS_v1/GATE.json'}
inputs={k:dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p)) for k,p in mapping.items()}
assert inputs['new_reference_details']['sha256']=='58a33465f5af8dc0f39983253abdcf9bccb9ac79e03690e342792281a36c57a6'
cfg=dict(experiment_id='SC_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_CPU_EXPORT_V1',code_commit=commit,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs=inputs,original_remote_raw_root=read(mapping['old_run_record'])['raw_result_location'],fixed_old_source='BAC009S0764W0209',fixed_old_arm='two_full_early',fixed_old_repeat=0,expected_source0_calls=17,expected_existing_new4_calls=68,expected_combined_calls=85,scope='Fixed prior raw conservative r0 protected calls plus existing original new4 reference. No model output selects a run, no old99 source marker rewrite, no service metrics replay.')
cp=F/'SHORT_REFERENCE_EXPORT_v1_FROZEN.json';put(cp,cfg)
put(F/'CURRENT_REFERENCE_EXPORT_CANDIDATE_v1.json',dict(source_worktree=str(S.resolve()),source_manifest=str(mp.resolve()),source_manifest_sha256=sha(mp),source_commit=commit,GPU_queue='LOCAL_CPU_PRIOR_BDFA_REFERENCE_EXPORT_ONLY',scope='Candidate only; global CURRENT unchanged, formal CPU/export awaits root noarg window.'))
put(F/'SHORT_REFERENCE_EXPORT_READY_v1.json',dict(source_commit=commit,source_manifest_sha256=sha(mp),config_sha256=sha(cp),files=len(files),development_controls=13,actual_export_executed=False,new_model_calls=0))
print(json.dumps(dict(source_commit=commit,manifest_sha256=sha(mp),config_sha256=sha(cp),files=len(files),actual_export_executed=False),indent=2))

