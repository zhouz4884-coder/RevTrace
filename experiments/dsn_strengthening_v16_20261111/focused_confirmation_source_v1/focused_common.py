import pathlib
from confirmation_common import need,read,sha,selected_sources,prespecified_reference_subset,RUNTIME,canonical
REFERENCE_GENERATOR='f367c4e1068a9391a0e99d8537c94995a3388e13'
def validate_focus_selection(receipt,sources):
    need(receipt.get('selection_use')=='focused_full_ready_confirmation','not a focused confirmation receipt')
    ix=receipt.get('comparison_bank_indices');need(ix in ([2,3],[4,5,6,7]),'unregistered confirmation voices')
    bank=receipt['parent_bank_receipt'];need(sha(bank['path'])==bank['sha256'],'bank bytes changed')
    ss=sorted(selected_sources(read(bank['path']),8),key=lambda s:(s['speaker_id'],s['source_id']))
    need(sources==[ss[i] for i in ix],'confirmation sources not metadata-fixed bank slice')
def original_contract(parent_ref,template):
    raw=pathlib.Path(parent_ref['reference_gate']['path']).parent;record=read(raw/'RUN_RECORD.json')
    need(record['code_commit']==REFERENCE_GENERATOR and record['actual_NN_source_commit']==RUNTIME,'measured reference roles changed')
    need(sha(record['frozen_config'])==record['config_sha256'],'reference config changed');plan=read(record['frozen_config']);s=template['settings']
    need(canonical(s['backend'])==canonical(plan['backend']) and canonical(s['warmup'])==canonical(plan['warmup']),'serving original task/warmup differs from measured parent')
    warm=[x for x in s['model_sources'] if x['source_id']==s['warmup']['source_id']]
    need(len(warm)==1 and warm[0]==plan['warmup_source'],'warmup input changed')
    need(s['corrector_dtype']=='float32' and s['max_ahead_frames']==32000,'dtype/lookahead changed');return warm[0]
