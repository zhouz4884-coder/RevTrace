"""Mechanical config only AFTER immutable four-source byte receipt exists."""
import argparse,copy,datetime,hashlib,json,pathlib,sys
H=pathlib.Path(__file__).resolve().parents[1];I=H.parent/'dsn_streamcorrect_independent_20261029'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_reference_20261029'
sys.path.insert(0,str(H/'reference_generator_source_v1'))
from original_full_reference import METHOD_COMMIT,METHOD_CONFIG_SHA256,validate_selection,validate_original_bindings
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def stamp(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=pathlib.Path,default=I/'SOURCE_RECEIPT_v1.json');a=parser.parse_args()
receipt=read(a.receipt);metadata=read(I/'METADATA_SELECTION_v1_FROZEN.json');final=read(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json')
assert sha(I/'METADATA_SELECTION_v1_FROZEN.json')=='4bf6249f275cbe5c43099c528316648e1c6aee3485be8968da08e1d50a3b7ccd'
assert sha(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json')=='fb6a1f57aba24b4300d84b9c30cfc8828bcb86c0fd011db92d4023ef1519364d'
assert final['method_source_commit']==metadata['method_source_commit']==receipt['method_source_commit']==METHOD_COMMIT
assert stamp(final['created_utc'])<stamp(metadata['selection_created_utc'])
assert metadata['metadata_only_before_neural'] and not metadata['reference_read'] and not metadata['WAV_bytes_read'] and metadata['model_calls']==0
assert receipt['selection_sha256']==sha(I/'METADATA_SELECTION_v1_FROZEN.json') and receipt['frozen_method_sha256']==sha(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json')
assert receipt['status']=='PASS_FOUR_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE' and receipt['model_calls']==receipt['gpu_calls']==0 and receipt['all_selected_valid_sources_retained']
for group,source in zip(metadata['selected'],receipt['sources']):
 index=source['technical_fallback_index'];entry=group['technical_fallback_order'][index]
 assert entry['source_id']==source['source_id'] and entry['speaker_id']==source['speaker_id'] and source['archive_member']==entry
assert len(metadata['selected'])==len(receipt['sources'])==4
validate_selection(receipt,receipt['sources'])
pilot=read(H/'SERVICE_PILOT_v1_FROZEN.json');cell=next(c for c in pilot['cells'] if c['arm']=='two_full_spec_early');localmethod=H/'service_pilot_v1_configs'/pathlib.PurePosixPath(cell['config']).name
assert sha(localmethod)==METHOD_CONFIG_SHA256;settings=read(localmethod)['settings'];warm=copy.deepcopy(settings['warmup']);oldsource=next(s for s in settings['model_sources'] if s['source_id']==warm['source_id'])
manifest=H/'packages/NEW_REFERENCE_GENERATOR_SOURCE_v1.json';generator=read(manifest)
plan=dict(experiment_id='SC_FINAL_INDEPENDENT_NEW4_ORIGINAL_FULL_REFERENCE_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 generator_source_commit=generator['source_commit'],generator_source_manifest_sha256=sha(manifest),generator_source_root=P+'/source_v1',generator_source_manifest=P+'/GENERATOR_SOURCE_v1.json',
 model_runtime_commit=METHOD_COMMIT,model_runtime_root=pilot['source_root'],model_runtime_manifest=pilot['source_manifest'],method_config=cell['config'],method_config_sha256=METHOD_CONFIG_SHA256,
 source_selection_manifest=B+'/datasets/revtrace/streamcorrect_independent_20261029/SOURCE_RECEIPT_v1.json',source_selection_manifest_sha256=sha(a.receipt),
 metadata_selection_manifest=P+'/METADATA_SELECTION_v1_FROZEN.json',metadata_selection_manifest_sha256=sha(I/'METADATA_SELECTION_v1_FROZEN.json'),
 final_method_freeze_record=P+'/FINAL_NATIVE_METHOD_FREEZE_v1.json',final_method_freeze_sha256=sha(H/'FINAL_NATIVE_METHOD_FREEZE_v1.json'),
 old_task_fidelity_gate=pilot['old_task_fidelity_gate'],old_task_fidelity_gate_sha256=pilot['old_task_fidelity_gate_sha256'],frozen_environment_record=pilot['environment_record'],frozen_environment_sha256=pilot['environment_sha256'],
 backend=copy.deepcopy(settings['backend']),corrector_dtype='float32',gpu=0,
 fixed_old_warmup=dict(source_id=warm['source_id'],fixed_start=24000,fixed_end=32000,original_reference_start_state=warm['original_reference_start_state'],audio_source=oldsource),
 sources=receipt['sources'],cache_root=B+'/cache/revtrace_streamcorrect_independent_reference_20261029',environment_python=pilot['environment_python'],
 raw_result_location=B+'/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1',aggregate_summary_location=B+'/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1/SUMMARY.json',gate_decision_location=B+'/results/revtrace/dsn_streamcorrect_independent_20261029/reference_v1/GATE.json',
 source_order_fixed_before_neural=True,reference_only=True,actual_serving_cells=0,no_outcome_based_source_replacement=True,
 reference_binding_rule='After complete reference gate, mechanically bind DETAILS SHA into final unchanged-bdfa timed plan; no source selection by output')
validate_original_bindings(plan,read(localmethod));dest=I/'ORIGINAL_FULL_REFERENCE_PLAN_v1_FROZEN.json';assert not dest.exists();dest.write_bytes(json.dumps(plan,ensure_ascii=False,indent=2).encode())
receiptpath=I/'ORIGINAL_FULL_REFERENCE_PLAN_FREEZE_v1.json';assert not receiptpath.exists();receiptpath.write_bytes(json.dumps(dict(plan_sha256=sha(dest),actual_generator_source_commit=generator['source_commit'],imported_model_runtime_commit=METHOD_COMMIT,selection_sha256=sha(a.receipt),metadata_sha256=sha(I/'METADATA_SELECTION_v1_FROZEN.json'),source_ids=[s['source_id'] for s in receipt['sources']],created_utc=plan['created_utc'],model_calls=0,gpu_calls=0),indent=2).encode())
print(json.dumps(dict(plan=str(dest),plan_sha256=sha(dest),source_ids=[s['source_id'] for s in receipt['sources']],model_calls=0,gpu_calls=0),indent=2))
