"""Prepare fixed short same-source integration pilot; no execution or remote access."""
import argparse,copy,datetime,hashlib,json,pathlib,random,subprocess
F=pathlib.Path(__file__).resolve().parents[1];R=F.parents[1];H=F.parent/'dsn_streamcorrect_stage_handoff_20261029';I=F.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_resilience_20261030';O=B+'/results/revtrace/dsn_native_resilience_20261030'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):assert not p.exists();p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--version',default='v1');p.add_argument('--fault-target',type=int,default=32000);a=p.parse_args()
 assert a.fault_target==32000,'fixed development site may not be adapted after outcomes'
 mpath=F/'packages'/('SOURCE_'+a.version+'.json')
 if not a.freeze:print(json.dumps(dict(status='DRY_RUN_NO_MUTATION',source_manifest=str(mpath),source_id='BAC009S0908W0369',normal_cells=2,fullcall_fault_development_cells=4,seed=2026103021,maximum_service_seconds=240,neural_launched=False)));return
 m=read(mpath);source=F/('source_'+a.version)
 assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==m['source_commit']
 assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
 for row in m['files']:assert sha(source/row['path'])==row['sha256']
 receipt=read(I/'SOURCE_RECEIPT_v1.json');target=next(s for s in receipt['sources'] if s['source_id']=='BAC009S0908W0369');assert target['frames']==132145
 oldplan=read(H/'SERVICE_PILOT_v1_FROZEN.json');oldcell=next(c for c in oldplan['cells'] if c['arm']=='two_full_spec_early');oldcfg=read(H/'service_pilot_v1_configs'/pathlib.PurePosixPath(oldcell['config']).name);settings=copy.deepcopy(oldcfg['settings']);warm=next(s for s in settings['model_sources'] if s['source_id']==settings['warmup']['source_id'])
 settings.update(source_commit=m['source_commit'],sources=[target],model_sources=[warm,target],primary_gpu=0,max_ahead_frames=32000,record_state_telemetry=True)
 details=I/'REFERENCE_RESULTS_v1/DETAILS.json';assert sha(details)=='58a33465f5af8dc0f39983253abdcf9bccb9ac79e03690e342792281a36c57a6'
 rng=random.Random(2026103021);normal=['conservative','fullcall'];rng.shuffle(normal);faults=['worker_after_asr','worker_partial_frame','owner_before_durable','owner_after_durable'];rng.shuffle(faults)
 definitions=[dict(arm=arm,fault='none') for arm in normal]+[dict(arm='fullcall',fault=fault) for fault in faults]
 folder=F/('short_pilot_'+a.version+'_configs');folder.mkdir(exist_ok=False);cells=[]
 for position,item in enumerate(definitions):
  cid='SC_RESILIENCE_DEV_'+a.version+'_'+item['fault']+'_'+item['arm'];cfg=dict(cell_id=cid,experiment_id=cid,source_commit=m['source_commit'],arm=item['arm'],stage='same_source_development_pilot',cohort='S0908_single_chain',repeat=0,position=position,maximum_service_seconds=240,maximum_owner_restarts=2,settings=copy.deepcopy(settings),fault=dict(kind=item['fault'],source_id=target['source_id'],target=a.fault_target),reference_details=B+'/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1/DETAILS.json',reference_details_sha256=sha(details),reference_kind='short_bdfa_static_source_mapping',require_reference=True,expected_owner_error_types=[],scope='Integration/opportunity development, not independent acoustic confirmation or part of formal24. Same protected full models/two GPUs/warmup/early whole Consumer/durability/recovery in both arms; original2/8 and alloffered/EOS retained.')
  path=folder/(cid+'.json');put(path,cfg);cells.append(dict(cell_id=cid,arm=item['arm'],fault_kind=item['fault'],config=P+'/short_pilot_'+a.version+'_configs/'+path.name,config_sha256=sha(path),out=O+'/short_pilot_'+a.version+'/cells/'+cid,log=O+'/short_pilot_'+a.version+'/logs/'+cid+'.log'))
 plan=dict(experiment_id='SC_NATIVE_RESILIENCE_SHORT_DEVELOPMENT_PILOT_'+a.version.upper(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=m['source_commit'],source_root=P+'/source_'+a.version,source_manifest=P+'/SOURCE_'+a.version+'.json',source_manifest_sha256=sha(mpath),environment_python=oldplan['environment_python'],environment_record=oldplan['environment_record'],environment_sha256=oldplan['environment_sha256'],reference_details=cells and cfg['reference_details'],reference_details_sha256=sha(details),reference_kind='short_bdfa_static_source_mapping',source_receipt_sha256=sha(I/'SOURCE_RECEIPT_v1.json'),expected_cells=6,normal_cells=2,fault_development_cells=4,cells=cells,seed=2026103021,frozen_order=[dict(arm=x['arm'],fault=x['fault']) for x in definitions],normal_before_fault_development=True,original_D2_seconds=2.,original_C8_seconds=8.,all_offered_including_EOS=True,raw_result_location=O+'/short_pilot_'+a.version,aggregate_summary_location=O+'/short_pilot_'+a.version+'/SUMMARY.json',gate_decision_location=O+'/short_pilot_'+a.version+'/GATE.json',scope='Six development trials only: normal two arms first, four fullcall fault sites next. No result yet; final formal24 and sustained validation require separate frozen plans.',resource_rule='Root exclusive NN queue; remote source/assets/formal zero-skip CPU prerequisites and no-argument source gate before launch.')
 pp=F/('SHORT_PILOT_'+a.version+'_FROZEN.json');put(pp,plan);put(F/('SHORT_PILOT_'+a.version+'_FREEZE_RECORD.json'),dict(source_commit=m['source_commit'],plan_sha256=sha(pp),normal_cells=2,fault_development_cells=4,source_id=target['source_id'],GPU_launched=False))
 print(json.dumps(dict(status='FROZEN_SHORT_DEVELOPMENT6_NO_NEURAL_LAUNCH',plan=str(pp),plan_sha256=sha(pp),source_commit=m['source_commit'],frozen_order=plan['frozen_order']),indent=2))
if __name__=='__main__':main()

