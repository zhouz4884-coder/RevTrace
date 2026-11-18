"""Bind completed fresh references to the predeclared80-cell two-stage campaign."""
from pathlib import Path
import copy,hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_native_joint_retention_20261118';O=B+'/results/revtrace/dsn_native_joint_retention_20261118'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def identity(label,folder):
 p=E/'packages'/(label+'.json');x=json.loads(p.read_bytes());return dict(source_commit=x['source_commit'],source_root=P+'/'+folder+'/source',source_manifest=P+'/'+folder+'/SOURCE.json',source_manifest_sha256=sha(p),complete_files=len(x['files']),clean=True)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 h=json.loads((E/'launch_ops/REFERENCE8_V3/HANDLE.json').read_bytes())
 raw=c.python('C='+repr(h)+'\n'+r'''
from pathlib import Path
import datetime,json,subprocess
p=Path('/proc')/str(C['pid']);state='EXITED'
if p.exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();state=s[0]if int(s[19])==C['start_ticks']else'PID_REUSED';assert state in('Z','X','PID_REUSED')
owners=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip();assert not owners
print(json.dumps(dict(status='PASS_REFERENCE_PROCESS_GENERATION_EXIT_AND_CUDA_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['pid'],start_ticks=C['start_ticks'],state=state,CUDA_owners=owners)))
''',timeout=25);(E/'launch_ops/REFERENCE8_V3/RESOURCE_CLOSURE.json').write_bytes(raw+b'\n')
 for n in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','REFERENCE_RECEIPT.json','GENESIS.json','REFERENCE_ENERGY.json','MODEL_READY.json']:
  c.get(O+'/REFERENCE8_V3/'+n,E/'gpu_results/REFERENCE8_V3'/n)
 ref=json.loads((E/'gpu_results/REFERENCE8_V3/REFERENCE_RECEIPT.json').read_bytes());assert ref['status']=='PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'
 c.get(ref['reference_details']['path'],E/'gpu_results/REFERENCE8_V3/REFERENCE_DETAILS.json')
 protocol=json.loads((E/'plans/SCIENTIFIC_PROTOCOL.json').read_bytes());template=json.loads((E/'plans/TEMPLATE.json').read_bytes());nn=identity('RUNTIME_SOURCE_V1','runtime_v1');driver=identity('CAMPAIGN_SOURCE_V1','campaign_v1');audit=identity('AUDIT_SOURCE_V1','audit_v1')
 support=json.loads((R/'experiments/dsn_strengthening_v16_20261111/baseline_ops/PILOT_PREPARATION_V2/SUMMARY.json').read_bytes())['production_support']
 warmid=template['settings']['warmup']['source_id'];warm=next(s for s in template['settings']['model_sources']if s['source_id']==warmid)
 env=json.loads((E/'plans/ENVIRONMENT.json').read_bytes());plans=[]
 for phase in ['PILOT20_V1','CONFIRM60_V1']:
  entries=[x for x in protocol['cells']if x['stage']==phase];ids={x['source_id']for x in entries};sources=[s for s in protocol['sources']if s['source_id']in ids];by={s['source_id']:s for s in sources};cells=[]
  configroot=P+'/configs_v1/'+phase;out=O+'/'+phase;c.python('from pathlib import Path\nPath('+repr(configroot)+').mkdir(parents=True,exist_ok=True)\n')
  for position,item in enumerate(entries):
   sid=item['source_id'];cond=item['condition'];arm,retain=protocol['condition_mapping'][cond];cfg=copy.deepcopy(template);settings=copy.deepcopy(template['settings']);settings.update(source_commit=nn['source_commit'],sources=[copy.deepcopy(by[sid])],model_sources=[copy.deepcopy(warm),copy.deepcopy(by[sid])],primary_gpu=item['primary_gpu'],record_state_telemetry=True,record_resources=True)
   cid=f'RS18_{phase}_{sid}_{cond}_r{item["repeat"]}'
   cfg.pop('cost_observer',None);cfg.update(cell_id=cid,experiment_id=cid,source_commit=nn['source_commit'],arm=arm,condition=cond,consumer_retain_views=retain,repeat=item['repeat'],position=position,stage=phase,cohort='existing8_current_runtime_factorial',settings=settings,maximum_service_seconds=240,maximum_owner_restarts=2,fault={'kind':'none'},require_reference=True,reference_kind='strict',reference_details=ref['reference_details']['path'],reference_details_sha256=ref['reference_details']['sha256'],reference_gate=ref['reference_gate']['path'],reference_gate_sha256=ref['reference_gate']['sha256'],runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'})
   local=E/'plans/configs'/phase/(cid+'.json');put(local,cfg);remote=configroot+'/'+local.name;c.put(local,remote)
   cells.append(dict(cell_id=cid,source_id=sid,speaker_id=by[sid]['speaker_id'],condition=cond,strategy=arm,consumer_retain_views=retain,repeat=item['repeat'],primary_gpu=item['primary_gpu'],position=position,version='final',estimand_role='anchor'if cond=='conservative_s1'else'factorial',config=remote,config_sha256=sha(local),out=out+'/cells/'+cid,log=out+'/logs/'+cid+'.log',external_power=out+'/external/'+cid+'.jsonl'))
  plan=dict(experiment_id='REVTRACE_NATIVE_RS_'+phase+'_20261118',driver=driver,actual_NN=nn,production_support=support,view_audit=audit,environment_record=P+'/ENVIRONMENT_v1_FROZEN.json',environment_sha256=sha(E/'plans/ENVIRONMENT.json'),environment_python=env['executable'],selection_receipt=dict(path=P+'/SELECTION.json',sha256=sha(E/'baseline/ORIGINAL_SELECTION_BANK.json')),reference_receipt=dict(path=O+'/REFERENCE8_V3/REFERENCE_RECEIPT.json',sha256=sha(E/'gpu_results/REFERENCE8_V3/REFERENCE_RECEIPT.json')),reference_details=ref['reference_details'],sources=sources,cells=cells,expected_trials=len(cells),raw_result_location=out,maximum_process_seconds=720.,original_D2_seconds=2.,original_C8_seconds=8.,cadence=dict(sample_rate_hz=16000,input_release_seconds=.5,full_step_samples=8000),runtime_environment={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},gpu_uuids={'0':'GPU-ef01d441-985f-50b3-6e64-5d4c3e2def3a','1':'GPU-a696ce9a-7137-cf6f-b4d3-deb992a72f28'},all_offered_including_partial_EOS=True,scientific_protocol=dict(path=P+'/SCIENTIFIC_PROTOCOL.json',sha256=sha(E/'plans/SCIENTIFIC_PROTOCOL.json')),zero_opportunity_is_not_failure=True,positive_difference_is_not_gate=True)
  put(E/'plans'/(phase+'_PLAN.json'),plan);c.put(E/'plans'/(phase+'_PLAN.json'),P+'/'+phase+'_PLAN.json');plans.append(plan)
  C=dict(plan=P+'/'+phase+'_PLAN.json')
  raw=c.python('C='+repr(C)+'\n'+r'''
import importlib,json,sys
from pathlib import Path
p=json.loads(Path(C['plan']).read_bytes());sys.path.insert(0,p['driver']['source_root']);import run_native_factorial as f
for k in ['driver','actual_NN','production_support','view_audit']:
 x=p[k];assert f.verify_source(x['source_root'],x['source_manifest'],x['source_commit'])==x
assert f.validate_matrix(p['cells'],p['sources']);details=f.validate_reference(p,p['driver'],p['actual_NN'])
for c in p['cells']:
 assert f.sha(c['config'])==c['config_sha256'];f.validate_cell(c,f.read(c['config']),p,p['actual_NN'])
print(json.dumps(dict(status='PASS_FROZEN_SERVICE_MATRIX_IDENTITIES_REFERENCE_AND_CONFIGS_CPU_ONLY',experiment_id=p['experiment_id'],cells=len(p['cells']),sources=len(p['sources']),reference_rows=len(details),new_model_calls=0)))
''',timeout=45);(E/'baseline'/(phase+'_ENTRY_PREFLIGHT.json')).write_bytes(raw+b'\n');print(raw.decode(),flush=True)
 put(E/'WORKING_STATE.json',dict(status='REFERENCE8_COMPLETE_ALL80_SERVICE_CONFIGS_FROZEN_ENTRY_PREFLIGHT_PASS',actual_NN=nn['source_commit'],driver=driver['source_commit'],audit=audit['source_commit'],planned_serving_trials=80,reference_original_steps=141,reference_restored_steps=282,serving_completed=0,manuscript_edits=False))
