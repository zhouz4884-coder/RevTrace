"""Build a bounded collection request from local frozen plans; no SSH or GPU.

This script does not fetch, execute experiments, stage Git files or publish.
Root can use its explicit remote-path requests after process closure.
"""
from pathlib import Path
import argparse,hashlib,json

PHASES=('PILOT20_V1','CONFIRM60_V1')
CELL_FILES=(
 'CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ORIGIN.json','GENESIS.json',
 'SERVICE_END.json','SUMMARY.json','GATE.json','EXTERNAL_FACTORIAL_AUDIT.json',
 'INDEPENDENT_VIEW_AUDIT.json','WORKER_TIMER_LEDGER.json','JOB_ACCOUNTING.json',
 'SAMPLED_ENERGY_OWNERSHIP.json','view_audit/SUMMARY.json','view_audit/GATE.json',
 'view_audit/CANONICAL_SUPPORT_EVENTS.json','view_audit/OBSERVED_LOSS_WINDOWS.json',
)
CAMPAIGN_FILES=('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','PROGRESS.json','PARTIAL_RESULTS.json')
REFERENCE_FILES=('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','REFERENCE_RECEIPT.json','GENESIS.json','REFERENCE_ENERGY.json','MODEL_READY.json','REFERENCE_DETAILS.json')
SOURCE_MAP=(('RUNTIME_SOURCE_V1','runtime_source',67),('CAMPAIGN_SOURCE_V1','campaign_source',22),('AUDIT_SOURCE_V1','audit_source',20),('READINESS_SOURCE','baseline/readiness_source',3),('ANALYSIS_SOURCE_V1','analysis_source',3),('PRODUCTION_SUPPORT_SOURCE','baseline/production_support_source',18))

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def prepare(root):
 root=Path(root).resolve();requests=[];cells=[];input_hashes={};seen=set()
 def load(path):
  path=Path(path);input_hashes[path.relative_to(root).as_posix()]=dict(bytes=path.stat().st_size,sha256=digest(path));return json.loads(path.read_bytes())
 def add(remote,local,role,required=True,expected_sha256=None):
  if remote in seen:raise ValueError('Duplicate collection path '+remote)
  seen.add(remote);item=dict(remote_path=remote,local_relative_path=local,evidence_role=role,required_after_successful_closure=required,maximum_bytes=8_000_000)
  if expected_sha256:item['expected_source_byte_sha256']=expected_sha256
  requests.append(item)
 plans={phase:load(root/'plans'/f'{phase}_PLAN.json')for phase in PHASES}
 expected_counts={'PILOT20_V1':20,'CONFIRM60_V1':60}
 remote_roots={phase:plan['raw_result_location'].rstrip('/')for phase,plan in plans.items()}
 all_ids=set();condition_counts={}
 for phase,plan in plans.items():
  if plan['expected_trials']!=expected_counts[phase]or len(plan['cells'])!=expected_counts[phase]:raise ValueError('Frozen campaign extent changed')
  remote=remote_roots[phase]
  for name in CAMPAIGN_FILES:add(remote+'/'+name,'gpu_results/'+phase+'/'+name,'closed_campaign_metadata',required=name!='PROGRESS.json')
  for cell in plan['cells']:
   cid=cell['cell_id']
   if cid in all_ids:raise ValueError('Duplicate trial ID')
   all_ids.add(cid);condition_counts[cell['condition']]=condition_counts.get(cell['condition'],0)+1
   cfg=root/'plans/configs'/phase/(cid+'.json')
   if not cfg.exists()or digest(cfg)!=cell['config_sha256']:raise ValueError('Local frozen source config changed: '+str(cfg))
   load(cfg)
   add(cell['config'],'frozen_configs/'+phase+'/'+cid+'.json','source_config_bytes',expected_sha256=cell['config_sha256'])
   cellroot=cell['out'].rstrip('/')
   if cellroot!=remote+'/cells/'+cid:raise ValueError('Trial output escaped its frozen campaign')
   for name in CELL_FILES:add(cellroot+'/'+name,'gpu_results/'+phase+'/cells/'+cid+'/'+name,'closed_trial_bounded_metadata')
   for suffix in('_PRELAUNCH.json','_HANDLE.json'):
    name=cid+suffix;add(remote+'/records/'+name,'gpu_results/'+phase+'/records/'+name,'generation_bound_trial_launch')
   cells.append(dict(cell_id=cid,condition=cell['condition'],source_id=cell['source_id'],repeat=cell['repeat'],remote_trial_root=cellroot,external_power_path=cell['external_power'],process_log_path=cell['log'],raw_files_are_hash_index_only=True,raw_config_and_source_config_may_have_distinct_serialization=True))
 if len(cells)!=80 or set(condition_counts)!={'r0s0','r0s1','r1s0','r1s1','conservative_s1'}or set(condition_counts.values())!={16}:raise ValueError('Full80 matrix incomplete')
 first=plans[PHASES[0]];receipt=load(root/'gpu_results/REFERENCE8_V3/REFERENCE_RECEIPT.json');refroot=str(Path(receipt['reference_details']['path']).parent).replace('\\','/')
 for name in REFERENCE_FILES:
  expected=receipt['reference_details']['sha256']if name=='REFERENCE_DETAILS.json'else None
  add(refroot+'/'+name,'gpu_results/REFERENCE8_V3/'+name,'paid_reference_only',expected_sha256=expected)
 for tag in('REFERENCE8_V1','REFERENCE8_V2'):
  closure=load(root/'launch_ops'/tag/'ROOT_CLOSEOUT.json')
  if closure.get('model_calls')!=0:raise ValueError('Premodel failure reclassified')
  handle=closure.get('original_handle',closure.get('handle'))
  add(handle['log'],'preserved_premodel_failures/'+tag+'/process.log','operator_metadata_failure_before_model_load',required=True)
 sources=[]
 for name,folder,count in SOURCE_MAP:
  manifest=load(root/'packages'/(name+'.json'))
  if len(manifest['files'])!=count:raise ValueError('Source snapshot count changed: '+name)
  snapshot=root/folder
  # Readiness is an already frozen external dependency; its plain snapshot may
  # not be duplicated locally. Its Git bundle/manifest remain mandatory.
  available=snapshot.is_dir()
  if available:
   for row in manifest['files']:
    path=snapshot/row['path']
    if '.git'in Path(row['path']).parts or path.is_symlink()or not path.resolve().is_relative_to(snapshot.resolve()):raise ValueError('Unsafe source member')
    if not path.is_file()or path.stat().st_size!=row['bytes']or digest(path)!=row['sha256']:raise ValueError('Source bytes changed: '+str(path))
  bundle=root/'packages'/(name+'.bundle')
  if not bundle.is_file():raise ValueError('Missing complete source bundle')
  sources.append(dict(role=name,source_commit=manifest['source_commit'],complete_files=count,manifest_relative_path='packages/'+name+'.json',manifest_sha256=digest(root/'packages'/(name+'.json')),bundle_relative_path='packages/'+name+'.bundle',bundle_bytes=bundle.stat().st_size,bundle_sha256=digest(bundle),plain_source_relative_path=folder if available else None))
 return dict(record_type='LOCAL_BOUNDED_COLLECTION_REQUEST_NOT_EXPERIMENT_RESULT',frozen_campaigns=PHASES,expected_actual_serving_trials=80,condition_counts=condition_counts,input_hashes=input_hashes,source_snapshots=sources,requests=requests,trial_hash_index_requests=cells,raw_hash_index_method='After closure, stream SHA256 of each regular raw-trial file plus its external power and process log; preserve relative/absolute identities and file lengths; verify stat size/mtime before and after hashing.',closure_prerequisite='Root must prove both serving controllers exited by PID+start_ticks and all actual model CUDA ownership released before final raw hashing/publication.',request_count=len(requests),maximum_individual_download_bytes=8_000_000,publication_soft_budget_bytes=96_000_000,publication_hard_budget_bytes=128_000_000,bulk_raw_download_authorized=False,model_or_audio_download_authorized=False,ready_or_SLO_success_filtering_authorized=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);a=p.parse_args()
 result=prepare(a.root);out=a.out or a.root/'COLLECTION_REQUESTS.json';out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(dict(output=str(out),requests=result['request_count'],trials=result['expected_actual_serving_trials'],source_snapshots=len(result['source_snapshots']),no_network_calls=True,no_Git_writes=True)))
