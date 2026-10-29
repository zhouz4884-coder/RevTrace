"""Non-method template: freeze final16 mechanically after complete references."""
import argparse,copy,datetime,hashlib,json,pathlib,random,collections
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029'
METHOD='bdfa3b1307d267a5a4caf6484e1ad465c39a592e';SEED=2026102932;ARMS=('two_full_early','two_full_spec_early')
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def same(a,b):return json.dumps(a,sort_keys=True,ensure_ascii=False)==json.dumps(b,sort_keys=True,ensure_ascii=False)
def design(sources):
 rng=random.Random(SEED);base={}
 for s in sources:
  order=list(ARMS);rng.shuffle(order);base[s['source_id']]=order
 blocks=[dict(source_id=s['source_id'],speaker_id=s['speaker_id'],repeat=r,primary_gpu=r,
  arms=base[s['source_id']] if r==0 else list(reversed(base[s['source_id']]))) for s in sources for r in (0,1)]
 rng.shuffle(blocks);return blocks
def selftest():
 sources=[dict(source_id=str(i),speaker_id=str(i)) for i in range(4)];a=design(sources);assert a==design(sources) and len(a)==8
 for sid in range(4):
  q=sorted([b for b in a if b['source_id']==str(sid)],key=lambda b:b['repeat']);assert q[0]['arms']==list(reversed(q[1]['arms'])) and [b['primary_gpu'] for b in q]==[0,1]
 assert collections.Counter((b['source_id'],b['repeat'],arm) for b in a for arm in b['arms'])==collections.Counter((str(s),r,arm) for s in range(4) for r in (0,1) for arm in ARMS)
 print(json.dumps(dict(status='PASS_FINAL16_TEMPLATE_CPU_ONLY',blocks=8,cells=16,models=0,files_frozen=0)))
def freeze(receipt_path,reference_root):
 receipt=read(receipt_path);metadata=read(I/'METADATA_SELECTION_v1_FROZEN.json');method=read(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json')
 assert method['method_source_commit']==receipt['method_source_commit']==metadata['method_source_commit']==METHOD
 assert receipt['selection_sha256']==sha(I/'METADATA_SELECTION_v1_FROZEN.json') and receipt['frozen_method_sha256']==sha(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json')
 assert receipt['status']=='PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE' and receipt['model_calls']==receipt['gpu_calls']==0 and len(receipt['sources'])==4
 gate=read(reference_root/'GATE.json');summary=read(reference_root/'SUMMARY.json');details=reference_root/'DETAILS.json'
 assert gate['status']=='PASS_ALL_LOCKED_NEW_SPEAKER_ORIGINAL_FULL_REFERENCE_CALLS' and same(gate,summary)
 assert gate['imported_model_runtime_commit']==METHOD and gate['reference_only'] and gate['actual_serving_cells']==0
 assert gate['source_ids']==[s['source_id'] for s in receipt['sources']] and gate['full_calls']==sum((s['frames']+7999)//8000 for s in receipt['sources'])
 assert sha(details)==gate['reference_details_sha256']
 # Read only reference metadata for coverage. Never choose an arm/source from C outputs.
 refs=read(details)
 for s in receipt['sources']:assert [r['end'] for r in refs if r['source_id']==s['source_id']]==list(range(8000,s['frames'],8000))+[s['frames']]
 oldplan=read(H/'SERVICE_PILOT_v1_FROZEN.json');oldcell=next(c for c in oldplan['cells'] if c['arm']==ARMS[1]);oldcfg=read(H/'service_pilot_v1_configs'/pathlib.PurePosixPath(oldcell['config']).name)
 warm_source=next(s for s in oldcfg['settings']['model_sources'] if s['source_id']==oldcfg['settings']['warmup']['source_id'])
 source_by_id={s['source_id']:s for s in receipt['sources']};blocks=design(receipt['sources']);cells=[];folder=I/'service_v1_configs';folder.mkdir(exist_ok=False)
 for block_index,block in enumerate(blocks):
  for arm in block['arms']:
   position=len(cells);sid=block['source_id'];cell_id=f'SC_FINAL_INDEPENDENT_V1_{arm}_{sid}_r{block["repeat"]}'
   settings=copy.deepcopy(oldcfg['settings']);settings.update(source_commit=METHOD,sources=[source_by_id[sid]],model_sources=[warm_source,*receipt['sources']],primary_gpu=block['repeat'],max_ahead_frames=32000)
   cfg=dict(cell_id=cell_id,arm=arm,stage='independent_confirmation',cohort='four_new_speakers_single_chain',repeat=block['repeat'],position=position,pair_block=block_index,maximum_service_seconds=180,settings=settings)
   path=folder/(cell_id+'.json');path.write_bytes((json.dumps(cfg,ensure_ascii=False,indent=2)+'\n').encode())
   cells.append(dict(cell_id=cell_id,arm=arm,source_id=sid,repeat=block['repeat'],pair_block=block_index,position=position,config=P+'/service_v1_configs/'+path.name,config_sha256=sha(path),out=O+'/service_v1/cells/'+cell_id,log=O+'/service_v1/logs/'+cell_id+'.log'))
 plan=dict(experiment_id='SC_FINAL_INDEPENDENT_FOUR_NEW_SPEAKER_SERVICE_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=METHOD,source_root=oldplan['source_root'],source_manifest=oldplan['source_manifest'],source_manifest_sha256=oldplan['source_manifest_sha256'],
  environment_python=oldplan['environment_python'],environment_record=oldplan['environment_record'],environment_sha256=oldplan['environment_sha256'],
  reference_details=O+'/reference_v1/DETAILS.json',reference_details_sha256=sha(details),original_reference_gate=O+'/reference_v1/GATE.json',original_reference_gate_sha256=sha(reference_root/'GATE.json'),
  old_task_fidelity_gate=oldplan['old_task_fidelity_gate'],old_task_fidelity_gate_sha256=oldplan['old_task_fidelity_gate_sha256'],
  final_method_freeze_record=P+'/FINAL_NATIVE_METHOD_FREEZE_v1.json',final_method_freeze_sha256=sha(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json'),metadata_selection=P+'/METADATA_SELECTION_v1_FROZEN.json',metadata_selection_sha256=sha(I/'METADATA_SELECTION_v1_FROZEN.json'),
  source_receipt=B+'/datasets/revtrace/streamcorrect_independent_20261029/SOURCE_RECEIPT_v1.json',source_receipt_sha256=sha(receipt_path),expected_cells=16,random_order_seed=SEED,paired_blocks=blocks,cells=cells,
  raw_result_location=O+'/service_v1',campaign_output=O+'/service_v1/campaign',aggregate_summary_location=O+'/service_v1/campaign/SUMMARY.json',gate_decision_location=O+'/service_v1/campaign/GATE.json',
  original_D2_seconds=2,original_C8_seconds=8,all_offered_including_EOS=True,source_and_arm_order_chosen_without_reference_C_outputs=True,
  fidelity='All selected inputs/complete states/original C/IDs at every original frontier and partial EOS; only declared stage_execution projection',
  resource_rule='Root exclusive allocation only; no parallel model run or heavy CPU/IO during actual service; fresh workers for every cell',
  scope='Four metadata-selected new speakers, two fresh-process repeats and paired arm reversal/GPU swap. Same unchanged bdfa protected original full ASR/C/U, same whole-text Consumer, original D2/C8/all offered including EOS. Original-full references are offline inputs, never serving results.')
 dest=I/'FINAL_SERVICE_v1_FROZEN.json';assert not dest.exists();dest.write_bytes((json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode())
 print(json.dumps(dict(status='FROZEN_FINAL16_NO_MODEL_LAUNCH',plan=str(dest),plan_sha256=sha(dest),cells=16,reference_sha256=sha(details),method=METHOD),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--freeze',action='store_true');p.add_argument('--receipt',type=pathlib.Path,default=I/'SOURCE_RECEIPT_v1.json');p.add_argument('--reference-results',type=pathlib.Path,default=I/'REFERENCE_RESULTS_v1');a=p.parse_args();assert a.self_test!=a.freeze,'choose exactly --self-test or --freeze'
 selftest() if a.self_test else freeze(a.receipt,a.reference_results)
