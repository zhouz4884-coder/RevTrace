"""Preserve v1; correct one diagnostic label that included identity payloads."""
import datetime,hashlib,json,pathlib,shutil,subprocess
H=pathlib.Path(__file__).resolve().parents[1];src=H/'pilot_transport_analysis_source_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
cfg=json.loads((H/'PILOT_TRANSPORT_ANALYSIS_v1_FROZEN.json').read_text(encoding='utf-8'))
cfg.update(experiment_id='SC_STAGE_PILOT_TRANSPORT_DIAGNOSTICS_V2',analysis_source_commit=commit,
 analysis_source_files={x:sha(src/x) for x in ('.gitattributes','analyze.py')},
 out=str((H/'pilot_transport_analysis_RESULTS_v2').resolve()),
 frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 supersedes='V1 original_C_nonNone_jobs counted identity-prediction payloads as well as learned C. V2 separates these categories and labels completed-only job totals. No service/input/timing metric changes.')
cp=H/'PILOT_TRANSPORT_ANALYSIS_v2_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
snap=H/'pilot_transport_analysis_snapshot_v2';snap.mkdir(exist_ok=False)
for name in cfg['analysis_source_files']:shutil.copyfile(src/name,snap/name)
bundle=H/'packages/PILOT_TRANSPORT_ANALYSIS_v2.bundle'
subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
(H/'packages/PILOT_TRANSPORT_ANALYSIS_SOURCE_v2.json').write_text(json.dumps(dict(source_commit=commit,
 files=cfg['analysis_source_files'],config_sha256=sha(cp),bundle_sha256=sha(bundle),complete_tracked_files=True),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,config_sha256=sha(cp))))
