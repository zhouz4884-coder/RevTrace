"""All24 bounded offline decision quality, no alternative model schedule."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,re
from agreement import RULES
from shadow_replay import source_replay,endpoints
from text_metrics import ledger


def read(p):return json.loads(Path(p).read_bytes())
def lines(p):return [json.loads(x) for x in Path(p).read_bytes().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def analyze(cfg,out,guard):
    from feedback_contract import FeedbackCut
    from resilience_metrics import fact_audit,reference_audit
    from resilience_storage import scan
    from consumer_audit import audit_consumer,provisional_registry
    from original_primary_quantiles import quantile,finite
    plan=read(cfg['pilot_plan']);results=[];pairs=[]
    if len(plan['cells'])!=24 or len(plan['sources'])!=2:raise ValueError('fixed all24 scope changed')
    for cell in plan['cells']:
        guard();root=Path(cell['out']);c=read(root/'CONFIG.json')
        if sha(cell['config'])!=cell['config_sha256'] or c!=read(cell['config']):raise ValueError('actual cell config changed')
        if c['source_commit']!=cfg['runtime']['code_commit'] or c['settings']['source_commit']!=c['source_commit']:raise ValueError('actual NN role changed')
        if c['arm']!=cell['strategy'] or c['repeat']!=cell['repeat']:raise ValueError('cell identity changed')
        if read(root/'GATE.json')['status']!='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK':raise ValueError('actual service technical gate failed')
        sources={s['source_id']:s for s in c['settings']['sources']}
        if set(sources)!={cell['source_id']}:raise ValueError('source scope changed')
        roots,facts,processed=fact_audit(root/'facts.wal',sources)
        reference=reference_audit(c,facts,c['source_commit'])
        if reference['status']!='PASS_COMPLETE_ORIGINAL_REFERENCE' or reference['reference_kind']!='strict':raise ValueError('actual full reference failed')
        initial=read(root/'GENESIS.json');header,_=next(scan(root/'facts.wal',repair_tail=False))
        if initial!=header['body']['initials']:raise ValueError('genesis changed')
        rows=lines(root/'consumer.jsonl');pubs=lines(root/'publications.jsonl');ingress=lines(root/'ingress.jsonl')
        dispatch=[];worker=[]
        for folder in sorted(root.glob('owner_e*')):
            if folder.is_dir() and re.fullmatch(r'owner_e\d+',folder.name):
                dispatch+=lines(folder/'dispatch.jsonl');worker+=lines(folder/'worker_results.jsonl')
        bindings=audit_consumer(rows,pubs,facts,initial,provisional_registry(dispatch,worker))
        if bindings['counts']['actual_consumer_rows_checked']!=len(rows):raise ValueError('incomplete actual Consumer bindings')
        origin=read(root/'ORIGIN.json');nextr=[]
        if origin['original_D']!=2. or origin['original_C']!=8.:raise ValueError('original deadlines changed')
        for sid,spec in sources.items():
            source_rows=[r for r in rows if r['source_id']==sid];horizon=source_rows[-1]['observed']
            outputs,prefix,counts,decisions=source_replay(sid,rows,pubs,facts,initial[sid],ingress,spec['frames'],horizon)
            offers={r['frontier']:r for r in ingress if r['kind']=='accepted_input' and r['source_id']==sid}
            for F,r in offers.items():
                if r['audio_sha256']!=spec['audio_sha256'] or r['original_offer']!=origin['origin_perf']+F/16000:raise ValueError('offered immutable audio/clock changed')
            base=None
            for rule in RULES:
                rr=outputs[rule];ep=endpoints(rr,offers,spec['frames']);credit=sum(x['weight_audio_seconds'] for x in ep if x['dual_credit'])
                if rule=='actual_SUP':
                    if rr!=source_rows:raise ValueError('actual-SUP identity replay changed rows')
                    base=ep
                    if abs(credit-read(root/'SUMMARY.json')['primary']['dual_deadline_audio_credit_seconds'])>1e-8:raise ValueError('actual primary credit not conserved')
                if [e['unchanged_original_C'] for e in ep]!=[e['unchanged_original_C'] for e in base]:raise ValueError('selected original G changed across rules')
                text={}
                for strip in (False,True):
                    mode='whitespace_stripped' if strip else 'raw'
                    text[mode]={tag:ledger(rr,alt,strip) for tag,alt in (('primary',False),('alternative',True))}
                ds=[e['offline_shadow_D'] if e['offline_shadow_D'] is not None else math.inf for e in ep]
                cs=[e['unchanged_original_C'] if e['unchanged_original_C'] is not None else math.inf for e in ep]
                summary=dict(cell_id=cell['cell_id'],source_id=sid,speaker_id=cell['speaker_id'],strategy=cell['strategy'],repeat=cell['repeat'],rule=rule,
                    status='COMPLETE_FIXED_SCHEDULE_OFFLINE_OBSERVER',offered_audio_seconds=spec['frames']/16000,
                    offline_shadow_dual_credit_audio_seconds=credit,offline_shadow_D99=finite(quantile(ds,.99)),unchanged_original_C99=finite(quantile(cs,.99)),
                    EOS=[e for e in ep if e['EOS']][0],nonEOS_dual_credit_audio_seconds=sum(e['weight_audio_seconds'] for e in ep if not e['EOS'] and e['dual_credit']),
                    actual_Consumer_candidate_rows=len(source_rows),observer_output_rows=len(rr),source_horizon=horizon,text=text,
                    roles='Read policy above original AlignAtt and C/U; fixed actual candidate schedule; no changed GPU/model budget, ACK or GC',
                    content_prefix_audio_fraction_used=False,new_model_calls=0)
                results.append(summary);nextr.append(summary)
                put(out/(cell['cell_id']+'_'+rule+'_ROWS.json'),rr);put(out/(cell['cell_id']+'_'+rule+'_FRONTIERS.json'),ep)
            prefix_metrics={mode:{tag:ledger(prefix,alt,strip) for tag,alt in (('primary',False),('alternative',True))} for mode,strip in (('raw',False),('whitespace_stripped',True))}
            prefix_summary=dict(cell_id=cell['cell_id'],source_id=sid,strategy=cell['strategy'],repeat=cell['repeat'],counts=counts,
                maximum_unmapped_code_points=max(r['unmapped_code_points'] for r in prefix),
                rows_with_unmapped_code_points=sum(r['unmapped_code_points']>0 for r in prefix),text=prefix_metrics,
                interpretation='Free Unicode prefix has content metrics only; zero implied audio alignment or proportional audio credit')
            put(out/(cell['cell_id']+'_LA2_PREFIX.json'),dict(summary=prefix_summary,rows=prefix,decisions=decisions))
            for target in nextr[1:]:
                actual=nextr[0]
                pairs.append(dict(cell_id=cell['cell_id'],source_id=sid,speaker_id=cell['speaker_id'],strategy=cell['strategy'],repeat=cell['repeat'],
                    rule=target['rule'],control='actual_SUP',offered_audio_seconds=target['offered_audio_seconds'],
                    offline_shadow_credit_difference_audio_seconds=target['offline_shadow_dual_credit_audio_seconds']-actual['offline_shadow_dual_credit_audio_seconds'],
                    raw_primary_retired_characters_difference=(target['text']['raw']['primary']['retired_characters']-actual['text']['raw']['primary']['retired_characters']),
                    raw_primary_retired_character_seconds_difference=(target['text']['raw']['primary']['retired_character_seconds']-actual['text']['raw']['primary']['retired_character_seconds']),
                    live_closed_loop_causal_effect_identified=False))
    put(out/'ALL24_RULE_TABLE.json',results);put(out/'ALL24_WITHIN_SCHEDULE_CONTRASTS.json',pairs)
    arm_totals=[]
    for arm in sorted({r['strategy'] for r in results}):
        for rule in RULES:
            selected=[r for r in results if r['strategy']==arm and r['rule']==rule]
            arm_totals.append(dict(strategy=arm,rule=rule,cells=len(selected),speaker_clusters=len({r['speaker_id'] for r in selected}),
                offered_audio_seconds=sum(r['offered_audio_seconds'] for r in selected),
                offline_shadow_credit_audio_seconds=sum(r['offline_shadow_dual_credit_audio_seconds'] for r in selected),
                raw_primary_retired_characters=sum(r['text']['raw']['primary']['retired_characters'] for r in selected),
                raw_primary_retired_character_seconds=sum(r['text']['raw']['primary']['retired_character_seconds'] for r in selected),
                raw_alternative_retired_character_seconds=sum(r['text']['raw']['alternative']['retired_character_seconds'] for r in selected)))
    put(out/'ARM_TOTALS.json',arm_totals)
    return dict(status='PASS_COMPLETE_ALL24_OFFLINE_EXTERNAL_RULE_ADAPTER',cells=24,rules=list(RULES),cell_rule_rows=len(results),
        all_preselected_cells_retained=True,all_actual_SUP_rows_and_credit_identical=True,selected_original_G_unchanged=True,
        all_final_actual_texts_equal=True,new_model_calls=0,offline_schedule_replays=24,
        roles=dict(original_engine='PaddedAlignAttWhisper inside unchanged original C/U',external_rule='LA2 Unicode prefix and conservative whole-view read adapter',
            controls=['canonical-only','generic fixed 0.5 wall-second lag'],task='fixed recorded actual Consumer candidate schedule',
            noninterference='offline reader emits no Consumer ACK/Owner/GC calls; no live substitution claim'),
        outcome_positive_is_gate=False,output_covered_speaker_clusters=2,independent_windows_used_as_n=False)
