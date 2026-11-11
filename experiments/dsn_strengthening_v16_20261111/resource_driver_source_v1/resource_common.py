"""Eight-cell synchronous resource-control matrix, separate from pilot estimands."""
import copy,random,pathlib
from confirmation_common import (RUNTIME,SUPPORT,need,read,sha,canonical,verify_source,selected_sources,
    reference_binding,prespecified_reference_subset)
REFERENCE_GENERATOR='f367c4e1068a9391a0e99d8537c94995a3388e13'
SEED=2026111104
ARMS=('conservative','fullcall')

def groups_from_sources(sources):
    need(len(sources)==4 and sources==sorted(sources,key=lambda s:(s['speaker_id'],s['source_id'])),'resource groups must be metadata-first ordered four')
    return [dict(group_id='sync'+str(n),source_count=n,sources=copy.deepcopy(sources[:n]),source_ids=[s['source_id'] for s in sources[:n]]) for n in (2,4)]

def blocks(groups):
    rng=random.Random(SEED);ordered=list(groups);rng.shuffle(ordered);orders={}
    for group in ordered:
        order=list(ARMS);rng.shuffle(order);orders[group['group_id']]=order
    result=[]
    for repeat in (0,1):
        for g in (ordered if repeat==0 else list(reversed(ordered))):
            order=orders[g['group_id']] if repeat==0 else orders[g['group_id']][::-1]
            result.append(dict(group=g,repeat=repeat,primary_gpu=repeat,strategies=order))
    return result,orders

def validate_matrix(cells,groups):
    need(len(cells)==8 and len({c['cell_id'] for c in cells})==8,'complete8-cell resource matrix required')
    expected=[(b['group']['group_id'],arm,b['repeat'],b['primary_gpu'],b['group']['source_ids']) for b in blocks(groups)[0] for arm in b['strategies']]
    actual=[(c['group_id'],c['strategy'],c['repeat'],c['primary_gpu'],c['source_ids']) for c in sorted(cells,key=lambda c:c['position'])]
    need(expected==actual and [c['position'] for c in cells]==list(range(8)),'resource order/group/GPU reversal mismatch')

def reference_contract(full_selection,subset_selection,full_reference,subset_reference,generator):
    parent_sources,subset_sources=prespecified_reference_subset(read(full_selection),read(subset_selection))
    need(generator['source_commit']==REFERENCE_GENERATOR,'resource controller is not the measured reference generator')
    full=reference_binding(full_reference,full_selection,parent_sources,REFERENCE_GENERATOR)
    subset=reference_binding(subset_reference,subset_selection,subset_sources,REFERENCE_GENERATOR)
    need(subset['measured_parent_reference']==dict(path=str(full_reference),sha256=sha(full_reference)),'group2 subset binds another measured parent')
    raw=pathlib.Path(full['reference_gate']['path']).parent;record=read(raw/'RUN_RECORD.json')
    need(record['code_commit']==REFERENCE_GENERATOR and record['actual_NN_source_commit']==RUNTIME,'measured parent execution roles differ')
    need(sha(record['frozen_config'])==record['config_sha256'],'measured reference configuration changed')
    return groups_from_sources(parent_sources),{'sync2':subset,'sync4':full},read(record['frozen_config'])

def check_task_settings(template,reference_plan):
    settings=template['settings']
    need(canonical(settings['backend'])==canonical(reference_plan['backend']),'resource backend differs from measured original reference')
    need(canonical(settings['warmup'])==canonical(reference_plan['warmup']),'resource warmup differs from measured reference')
    warm=[s for s in settings['model_sources'] if s['source_id']==settings['warmup']['source_id']]
    need(len(warm)==1 and warm[0]==reference_plan['warmup_source'],'resource warmup source differs')
    need(settings['corrector_dtype']=='float32' and settings['max_ahead_frames']==32000,'resource dtype/lookahead altered')
    return warm[0]

def validate_cell(cfg,cell,group,reference_plan=None):
    need(cfg['arm']==cell['strategy'] and cfg['arm'] in ARMS,'resource policy differs')
    need(cfg['settings']['source_commit']==RUNTIME and cfg['settings']['sources']==group['sources'],'group complete source objects differ')
    need(cfg['settings']['primary_gpu']==cell['primary_gpu'] and cfg['settings']['corrector_dtype']=='float32' and cfg['settings']['max_ahead_frames']==32000,'resource execution contract differs')
    need(cfg['reference_kind']=='strict' and cfg['require_reference'] is True and cfg['fault']['kind']=='none','group strict task/reference contract differs')
    need(not any(k in cfg or k in cfg['settings'] for k in ('source_offsets','phase_offsets','source_origin_offsets')),'staggered clocks forbidden')
    if reference_plan is not None:
        warm=check_task_settings(cfg,reference_plan)
        need(cfg['settings']['model_sources']==[warm]+group['sources'],'group model preload does not cover warmup plus every chain')
