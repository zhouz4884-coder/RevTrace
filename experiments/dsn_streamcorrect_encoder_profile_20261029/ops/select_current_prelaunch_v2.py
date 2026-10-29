import datetime,hashlib,json,pathlib,shutil
F=pathlib.Path(__file__).resolve().parents[1];ROOT=F.parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
cfg=read(F/'PROFILE_PLAN_v2_FROZEN.json');pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json'
backup=F/'CURRENT_BEFORE_ENCODER_PROFILE_v2.json';assert not backup.exists();shutil.copyfile(pointer,backup)
p=read(pointer);p.update(source_worktree=str((F/'source_v2').resolve()),source_commit=cfg['profile_source_commit'],
 source_manifest=str((F/'packages/SOURCE_v2_LOCAL_PREFLIGHT.json').resolve()),source_manifest_sha256=sha(F/'packages/SOURCE_v2_LOCAL_PREFLIGHT.json'),
 research_state=str((F/'CURRENT_STATUS.json').resolve()),GPU_queue='EXCLUSIVE_FROZEN_ENCODER13_COMPONENT_WINDOW',previous_pointer=str(backup.resolve()),
 scope='Machine-local E13 component generator pointer only; imported bdfa runtime and all old experiments preserve their own actual commits.')
pointer.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
record=dict(experiment_id=cfg['experiment_id'],code_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit'],
 frozen_config=str((F/'PROFILE_PLAN_v2_FROZEN.json').resolve()),frozen_config_sha256=sha(F/'PROFILE_PLAN_v2_FROZEN.json'),
 environment_record=str((F/'references_v1/FROZEN_ENVIRONMENT.json').resolve()),environment_record_sha256=cfg['environment_sha256'],
 raw_result_location=cfg['out'],aggregate_summary_location=cfg['out']+'/SUMMARY.json',gate_decision_location=cfg['out']+'/GATE.json',
 profile_source_manifest_sha256=sha(F/'packages/SOURCE_v2.json'),imported_runtime_manifest_sha256=cfg['imported_runtime_manifest_sha256'],
 CPU17_gate_sha256='1ac312e981d60a5615c0660ccceed2070c7215f0926dec545089716caeb9d30c',
 asset_prerequisite_sha256='6473a07fea831bca671c49282f9b48b8dca17217c4aeb762b380ddb442d0ce72',
 status='PRELAUNCH_NOT_A_GPU_RESULT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
dest=F/'PRELAUNCH_RUN_RECORD_v2.json';assert not dest.exists();dest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
status=read(F/'CURRENT_STATUS.json');status.update(status='LINUX17_ASSETS_PASS_CURRENT_SELECTED_PREFLIGHT_PENDING',formal_remote_CPU_gate_complete=True,
 actual_CPU_tests=17,actual_CPU_skips=0,model_asset_full_rehash_bytes=10099049234,original_infer_calls_completed=0,
 next_action='ROOT noargument source/run-record preflight, then allocated exact13 component launch; no deployed cache/service claim')
(F/'CURRENT_STATUS.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(current_source=cfg['profile_source_commit'],normalized_manifest_sha256=p['source_manifest_sha256'],prelaunch_record_sha256=sha(dest))))
