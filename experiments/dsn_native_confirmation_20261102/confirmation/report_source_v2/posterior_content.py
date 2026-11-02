"""Aggregate already-written NN4f posterior first-G partitions only.

No Consumer/raw trace reader, text normalization, token alignment or model call.
Raw and whitespace-stripped modes remain separate. Original primary/bootstrap
accounts are untouched; this adds secondary descriptive content accounting.
"""
from __future__ import annotations
import collections,math,pathlib
from report_common import CELLS,SPEAKERS,need,read,csvout

MODES=('raw','whitespace_stripped')
STATES=('supported','mismatching','unknown')
FIELD={'supported':'original_credit_supported_seconds','mismatching':'original_credit_mismatching_seconds','unknown':'original_credit_unknown_seconds'}

def close(a,b):return abs(a-b)<=1e-8

def parse_partition(original,cell):
    p=original['primary'];content=original['content'];posterior=original['posterior_whole_text_support']
    den=cell['offered_audio_s'];credit=cell['credit_audio_s'];frontiers=cell['offered_frontiers']
    need(close(p['offered_audio_seconds'],den) and p['offered_frontiers']==frontiers,'posterior original offered denominator changed')
    need(close(p['dual_deadline_audio_credit_seconds'],credit) and close(content['original_dual_credit_audio_seconds'],credit),'posterior and original primary/content credit differ')
    need(content['offered_frontiers']==frontiers and 0<=credit<=den+1e-8,'posterior original credit/frontier bounds invalid')
    result=[]
    for mode in MODES:
        part=posterior[mode];counts=part['all_offered_frontier_counts']
        need(set(counts)<=set(STATES),'unexpected posterior classification')
        values={state:part[FIELD[state]] for state in STATES}
        need(all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 for v in values.values()),'invalid posterior duration')
        full_counts={state:counts.get(state,0) for state in STATES}
        need(all(type(v) is int and v>=0 for v in full_counts.values()) and sum(full_counts.values())==frontiers,'all-offered posterior count partition does not conserve frontiers')
        need(close(sum(values.values()),credit),'posterior durations do not conserve original D2/C8 credit')
        missed=den-credit
        need(close(sum(values.values())+missed,den),'posterior and missed mass do not conserve all offered audio')
        result.append(dict(cell_id=cell['cell_id'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],policy=cell['policy'],repeat=cell['repeat'],mode=mode,
            offered_audio_s=den,original_credit_audio_s=credit,deadline_missed_audio_s=missed,
            supported_audio_s=values['supported'],mismatching_audio_s=values['mismatching'],unknown_audio_s=values['unknown'],
            all_offered_frontiers=frontiers,all_offered_supported_frontiers=full_counts['supported'],all_offered_mismatching_frontiers=full_counts['mismatching'],all_offered_unknown_frontiers=full_counts['unknown']))
    return result

def combine(items):
    keys=('offered_audio_s','original_credit_audio_s','deadline_missed_audio_s','supported_audio_s','mismatching_audio_s','unknown_audio_s',
          'all_offered_frontiers','all_offered_supported_frontiers','all_offered_mismatching_frontiers','all_offered_unknown_frontiers')
    total={key:sum(row[key] for row in items) for key in keys}
    need(close(total['supported_audio_s']+total['mismatching_audio_s']+total['unknown_audio_s'],total['original_credit_audio_s']),'aggregate posterior credit partition failed')
    need(close(total['original_credit_audio_s']+total['deadline_missed_audio_s'],total['offered_audio_s']),'aggregate all-offered denominator failed')
    total.update(supported_percent_of_all_offered=100*total['supported_audio_s']/total['offered_audio_s'],mismatching_percent_of_all_offered=100*total['mismatching_audio_s']/total['offered_audio_s'],unknown_percent_of_all_offered=100*total['unknown_audio_s']/total['offered_audio_s'])
    return total

def pair_content(conservative,fullcall):
    need(close(conservative['offered_audio_s'],fullcall['offered_audio_s']),'posterior source-paired offered denominator changed')
    den=conservative['offered_audio_s']
    return dict(offered_audio_s=den,conservative_supported_audio_s=conservative['supported_audio_s'],fullcall_supported_audio_s=fullcall['supported_audio_s'],
        supported_gain_audio_s=fullcall['supported_audio_s']-conservative['supported_audio_s'],supported_gain_pp=100*(fullcall['supported_audio_s']-conservative['supported_audio_s'])/den,
        conservative_mismatching_audio_s=conservative['mismatching_audio_s'],fullcall_mismatching_audio_s=fullcall['mismatching_audio_s'],mismatching_gain_audio_s=fullcall['mismatching_audio_s']-conservative['mismatching_audio_s'],
        conservative_unknown_audio_s=conservative['unknown_audio_s'],fullcall_unknown_audio_s=fullcall['unknown_audio_s'],unknown_gain_audio_s=fullcall['unknown_audio_s']-conservative['unknown_audio_s'],
        original_deadline_credit_gain_audio_s=fullcall['original_credit_audio_s']-conservative['original_credit_audio_s'])

def aggregate_existing(cells,out):
    need(len(cells)==CELLS and len({c['source_id'] for c in cells})==SPEAKERS,'complete new32/source8 required for posterior accounting')
    items=[]
    for cell in cells:items.extend(parse_partition(read(pathlib.Path(cell['raw_result_location'])/'SUMMARY.json'),cell))
    policies=[];source_pairs=[]
    for mode in MODES:
        for policy in ('conservative','fullcall'):
            own=[r for r in items if r['mode']==mode and r['policy']==policy];need(len(own)==16,'complete policy posterior rows missing')
            policies.append(dict(mode=mode,policy=policy,trials=16,**combine(own)))
        for sid in sorted({c['source_id'] for c in cells}):
            vals={}
            for policy in ('conservative','fullcall'):
                own=[r for r in items if (r['mode'],r['source_id'],r['policy'])==(mode,sid,policy)]
                need(len(own)==2 and {r['repeat'] for r in own}=={0,1},'source posterior repeats missing')
                vals[policy]=combine(own)
            speaker=next(c['speaker_id'] for c in cells if c['source_id']==sid)
            source_pairs.append(dict(mode=mode,source_id=sid,speaker_id=speaker,timing_repeats=2,**pair_content(vals['conservative'],vals['fullcall'])))
    csvout(pathlib.Path(out)/'POSTERIOR_ALL32_BY_MODE.csv',items)
    csvout(pathlib.Path(out)/'POSTERIOR_POLICIES_BY_MODE.csv',policies)
    csvout(pathlib.Path(out)/'POSTERIOR_SOURCE8_PAIRED_BY_MODE.csv',source_pairs)
    return dict(modes=list(MODES),all_cells=CELLS,independent_speakers=SPEAKERS,per_cell_modes=items,policies=policies,source_pairs=source_pairs,
        definition='original4f posterior agreement of whole first actual Consumer text at its own actual frontier G with later selected text at the same G',
        credited_partition='only original D2/C8 credited audio is partitioned supported/mismatching/unknown; all-offered denominator and deadline-missed mass stay unchanged',
        counts_scope='all-offered frontiers including EOS; these counts are not audio durations, characters or independent sources',
        raw_and_whitespace_modes_separate=True,unknown_never_folded_into_mismatching=True,negative_paired_differences_preserved=True,
        quality_and_primary_bootstrap_unchanged=True,new_content_bootstrap_or_normalizer=False,
        limits='posterior model agreement, not online SUP certification, human correctness, prefix truncation, token/audio alignment or new character volume',
        original_metric_sources=dict(resilience_metrics_sha256='1e3f7fbf50d4f621d51700f44ef4fb80cc335e3439e6e43e190aca9275cf121e',content_endpoints_sha256='07d16f211cbc4320b3df109049083285863d0ae709d8ac008c75eb78a2776b52'))

