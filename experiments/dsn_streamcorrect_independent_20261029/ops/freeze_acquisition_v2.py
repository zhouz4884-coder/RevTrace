import datetime,hashlib,json,pathlib,shutil,subprocess
F=pathlib.Path(__file__).resolve().parents[1];ROOT=F.parents[1];src=F/'source_v2'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip();tracked=subprocess.check_output(['git','ls-files'],cwd=src,text=True).splitlines()
files=[dict(path=x,bytes=(src/x).stat().st_size,sha256=sha(src/x)) for x in tracked];packages=F/'packages'
manifest=dict(source_commit=commit,files=files,scope='Transport recovery only; original selection source18 and immutable metadata lock retained')
for name,obj in [('SOURCE_v2.json',manifest),('SOURCE_v2_LOCAL_PREFLIGHT.json',dict(code_commit=commit,files=files))]:
 (packages/name).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
snap=F/'source_snapshot_v2';snap.mkdir(exist_ok=False)
for x in tracked:shutil.copyfile(src/x,snap/x)
bundle=packages/'SOURCE_v2.bundle';subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
cfg=read(F/'ACQUISITION_v1_FROZEN.json');staged=read(F/'STAGED_RANGE_TRANSPORT_v2.json')
assert cfg['selection_sha256']==staged['selection_sha256']
cfg.update(experiment_id='SC_INDEPENDENT4_EXACT_PUBLIC_RANGE_ACQUISITION_V2',source_commit=commit,source_files=files,
 out=cfg['out'].replace('acquisition_v1','acquisition_v2'),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 staged_ranges={x['source_id']:x for x in staged['records']},same_original_selection_unchanged=True,
 transport_recovery='B networkConnectionReset104; identical official public ranges via localRAM directlytoB, no localWAVfile; preserve original validWAV')
for key in ('summary','gate','source_receipt'):cfg[key]=cfg[key].replace('acquisition_v1','acquisition_v2')
cp=F/'ACQUISITION_v2_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
env=read(F/'CPU_GATE_v1.json');ep=F/'FROZEN_ACQUISITION_ENVIRONMENT_v2.json';ep.write_text(json.dumps({k:env[k] for k in ('python','executable','platform')},indent=2)+'\n',encoding='utf-8')
record=dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(cp.resolve()),frozen_config_sha256=sha(cp),environment_record=str(ep.resolve()),environment_record_sha256=sha(ep),raw_result_location=cfg['out'],aggregate_summary_location=cfg['summary'],gate_decision_location=cfg['gate'],method_source_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',selection_source_commit='18c7a0f079f211146ab3375cfd5208d6cbef8a76')
(F/'ACQUISITION_RUN_PRELAUNCH_v2.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
pointer=ROOT/'experiments/repository_identity_20261027/CURRENT.json';backup=F/'CURRENT_BEFORE_DATA_RECOVERY_v2.json';assert not backup.exists();shutil.copyfile(pointer,backup)
p=read(pointer);p.update(source_worktree=str(src.resolve()),source_commit=commit,source_manifest=str((packages/'SOURCE_v2_LOCAL_PREFLIGHT.json').resolve()),source_manifest_sha256=sha(packages/'SOURCE_v2_LOCAL_PREFLIGHT.json'),research_state=str((F/'CURRENT_STATUS.json').resolve()),previous_pointer=str(backup.resolve()),GPU_queue='CPU_ONLY_EXACT_SAME_SELECTION_TRANSPORT_RECOVERY_NO_NEURAL')
pointer.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,config_sha256=sha(cp),selection_unchanged=cfg['selection_sha256'])))
