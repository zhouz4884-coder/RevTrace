import datetime,hashlib,json,pathlib,shutil,subprocess
H=pathlib.Path(__file__).resolve().parents[1];src=H/'pilot_transport_analysis_source_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
inputroot=H/'SERVICE_PILOT_RESULTS_v1';inputs={}
for arm in ('two_full_spec_early','ready_handoff','two_full_early'):
 for name in ('SUMMARY.json','CONTENT_FRONTIERS.json','CONTENT.json','COMPLETE_TASK_FIDELITY.json','native_jobs.jsonl'):
  p=inputroot/f'SC_STAGE_SERVICE_PILOT_V1_{arm}_source0_r0'/name;inputs[p.relative_to(inputroot).as_posix()]=sha(p)
for name in ('STAGE_ADMISSIONS.json','CONSUMPTIONS.json','MATCHING_INFLIGHT_OPPORTUNITIES.json'):
 p=inputroot/'SC_STAGE_SERVICE_PILOT_V1_ready_handoff_source0_r0'/name;inputs[p.relative_to(inputroot).as_posix()]=sha(p)
files={name:sha(src/name) for name in ('.gitattributes','analyze.py')}
cfg=dict(experiment_id='SC_STAGE_PILOT_TRANSPORT_DIAGNOSTICS_V1',analysis_source_commit=commit,
 analysis_source_files=files,input_root=str(inputroot.resolve()),input_files=inputs,
 out=str((H/'pilot_transport_analysis_RESULTS_v1').resolve()),
 frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 scope='Local offline existing pilot logs only; no remote calls, new service, models or GPU')
cp=H/'PILOT_TRANSPORT_ANALYSIS_v1_FROZEN.json';assert not cp.exists();cp.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
snap=H/'pilot_transport_analysis_snapshot_v1';snap.mkdir(exist_ok=False)
for name in files:shutil.copyfile(src/name,snap/name)
bundle=H/'packages/PILOT_TRANSPORT_ANALYSIS_v1.bundle'
subprocess.run(['git','bundle','create',str(bundle.resolve()),'HEAD'],cwd=src,check=True)
manifest=dict(source_commit=commit,files=files,config_sha256=sha(cp),bundle_sha256=sha(bundle),complete_tracked_files=True)
(H/'packages/PILOT_TRANSPORT_ANALYSIS_SOURCE_v1.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(source_commit=commit,config_sha256=sha(cp),input_files=len(inputs))))
