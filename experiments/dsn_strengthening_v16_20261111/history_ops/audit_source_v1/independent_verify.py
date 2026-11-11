"""Independent event proof checker; imports no content/edit/statistics modules.

The literal event ledger is a replayable proof: operations transform the exact
original Consumer before-view into after-view at an independently recomputed
minimum distance. Ordered untouched units carry their actual birth identities.
"""
from collections import Counter,defaultdict
from functools import lru_cache
import hashlib,json
from fractions import Fraction
from itertools import product
from math import comb
from pathlib import Path


@lru_cache(maxsize=10000)
def distance(a,b):
    # Common-boundary trimming preserves Levenshtein distance; identity is NOT
    # inferred from the trimmed string and is checked separately below.
    k=0
    while k<min(len(a),len(b)) and a[k]==b[k]:k+=1
    a,b=a[k:],b[k:]
    k=0
    while k<min(len(a),len(b)) and a[-1-k]==b[-1-k]:k+=1
    if k:a,b=a[:-k],b[:-k]
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(row[j]+1,nxt[-1]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]


def check_bank(config_path,result_root):
    cfg=json.loads(Path(config_path).read_bytes());out=Path(result_root)
    checked_events=checked_operations=0;totals=Counter();per_group=defaultdict(Counter)
    source_summaries=json.loads((out/'SOURCE_SUMMARIES.json').read_bytes())
    for cell in cfg['cells']:
        raw=Path(cell['consumer_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==cell['consumer_sha256']
        rows=[json.loads(x) for x in raw.decode('utf8').splitlines() if x.strip()]
        if cell['schema']=='core':rows=[dict(source_id=cell['session_source_map'][str(r['session_id'])],
            observed=r['observed_perf'],text=r['visible_text']) for r in rows]
        events=json.loads((out/'cells'/cell['cell_id']/'ACTUAL_EDIT_EVENTS.json').read_bytes())
        spans=json.loads((out/'cells'/cell['cell_id']/'EDIT_AND_LCP_OCCURRENCE_LIFETIMES.json').read_bytes())
        states={};event_count=Counter()
        for e in events:
            key=e['source_id'],e['mode'],e['convention']
            state=states.setdefault(key,dict(text='',active=[],counts=Counter(),closed=[]))
            original=rows[e['row_index']];target=original['text']
            if e['mode']=='whitespace_stripped':target=''.join(x for x in target if not x.isspace())
            assert e['source_id']==original['source_id'] and e['observed']==original['observed']
            assert e['before']==state['text'] and e['after']==target
            old=state['active'];t=e['observed'];index=e['row_index'];new=[None]*len(target)
            common=0
            while common<min(len(state['text']),len(target)) and state['text'][common]==target[common]:common+=1
            assert e['lcp_suffix_closed']==len(state['text'])-common
            assert e['lcp_suffix_introduced']==len(target)-common
            state['counts']['lcp_suffix_closed']+=len(state['text'])-common
            state['counts']['lcp_suffix_introduced']+=len(target)-common
            if e['convention']=='LCP_suffix_identity':
                new=old[:common]+[dict(char=c,birth=t,id=f'{index}:{j}') for j,c in enumerate(target) if j>=common]
                removed=list(range(common,len(old)));ops=None
            else:
                assert e['distance']==distance(e['before'],target)
                removed=[];ops=Counter()
                for operation in e['edit_operations']:
                    kind=operation['op'];ops[kind]+=1;checked_operations+=1
                    oi,nj=operation.get('old_index'),operation.get('new_index')
                    if kind in ('D','S'):
                        assert oi not in removed;removed.append(oi)
                        assert old[oi]['char']==operation['old_code_point'] and old[oi]['id']==operation['occurrence_id']
                        assert abs((t-old[oi]['birth'])-operation['lifetime_seconds'])<1e-9
                    if kind in ('I','S'):
                        assert new[nj] is None
                        new[nj]=dict(char=operation['new_code_point'],birth=t,id=f'{index}:{nj}')
                survivors=[x for i,x in enumerate(old) if i not in removed]
                vacant=[j for j,x in enumerate(new) if x is None];assert len(survivors)==len(vacant)
                for j,x in zip(vacant,survivors):new[j]=x
                assert sum(ops.values())==e['distance']
                for k in ('I','D','S'):assert ops[k]==e['operation_counts'][k]
                assert e['operation_counts']['M']==len(survivors)
                state['counts'].update(ops);state['counts']['distance']+=e['distance']
            for i in removed:state['closed'].append(dict(char=old[i]['char'],id=old[i]['id'],birth=old[i]['birth'],closing=t,row=index))
            assert ''.join(x['char'] for x in new)==target
            state.update(text=target,active=new,last=t)
            checked_events+=1;event_count[key]+=1
        for key,state in states.items():
            sid,mode,convention=key
            summary=next(x for x in source_summaries if x['cell_id']==cell['cell_id'] and x['source_id']==sid and x['mode']==mode and x['convention']==convention)
            expected_rows=sum(r['source_id']==sid for r in rows);assert event_count[key]==expected_rows
            counts=state['counts'];closed=state['closed'];aged=sum(x['closing']-x['birth']>=cfg['age_threshold_seconds'] for x in closed)
            assert summary['final_visible_code_points']==len(state['text'])
            assert summary['right_censored_survivors']==len(state['active'])
            assert summary['right_censor_time_last_actual_source_observation']==state['last']
            ss=[s for s in spans if (s['source_id'],s['mode'],s['convention'])==key]
            dead=[s for s in ss if s['retracted']];live=[s for s in ss if not s['retracted']]
            assert len(dead)==len(closed) and len(live)==len(state['active'])
            for expected in closed:
                actual=next(x for x in dead if x['occurrence_id']==expected['id'])
                assert actual['first_observed']==expected['birth'] and actual['closing_observed']==expected['closing']
                assert actual['char']==expected['char'] and actual['closing_row']==expected['row']
                assert abs(actual['lifetime_seconds']-(expected['closing']-expected['birth']))<1e-9
            for expected in state['active']:
                actual=next(x for x in live if x['occurrence_id']==expected['id'])
                assert actual['first_observed']==expected['birth'] and actual['censor_observed']==state['last']
                assert actual['char']==expected['char'] and actual['right_censored'] is True
            for k in ('lcp_suffix_closed','lcp_suffix_introduced'):assert summary[k]==counts[k]
            if convention!='LCP_suffix_identity':
                for k in ('I','D','S','distance'):assert summary[k]==counts[k]
                assert summary['edit_retractions_age_ge_threshold']==aged
                assert summary['retracted_edit_occurrences']==len(closed)
                assert counts['I']-counts['D']==len(state['text'])
            else:assert summary['lcp_retractions_age_ge_threshold']==aged
            group=(cell['bank'],cell['stage'],cell['arm'],mode,convention)
            per_group[group].update(dict(counts,final_visible_code_points=len(state['text']),retracted_identity_occurrences=len(closed),identity_retractions_age_ge_threshold=aged))
            totals['sources']+=1
    # Independently recheck each published block contrast and source-level sign
    # numerator, using only the original frozen metadata, not primary modules.
    metadata={name:json.loads(Path(spec['path']).read_bytes()) for name,spec in cfg['metadata_inputs'].items()}
    runs={r['cell_id']:r for r in metadata['h3_runs']};op=defaultdict(Counter);op_source={}
    for r in metadata['h3_opportunities']:
        if r['clock_scope']=='consumer_apply':
            op_source[r['cell_id'],r['source_id']]=r
            for k,v in r.items():
                if type(v) is int and k not in ('rho','repeat','session_id'):op[r['cell_id']][k]+=v
    pair_result=json.loads((out/'H3_ALL110_PAIRED_RECOUNT.json').read_bytes())
    blocks={}
    for r in runs.values():blocks.setdefault(r['paired_block'],{})[r['arm']]=dict(r,**op[r['cell_id']])
    assert len(runs)==110 and len(blocks)==22 and len(pair_result['all220_paired_run_contrasts'])==220
    for pair in pair_result['all220_paired_run_contrasts']:
        arms=blocks[pair['paired_block']]
        for metric,observed in pair['differences'].items():
            a,b=arms[pair['left']].get(metric),arms[pair['right']].get(metric)
            if a is None or b is None:assert observed is None
            else:assert abs((b-a)-observed)<1e-8
    for factorial in pair_result['all22_factorials']:
        arms=blocks[factorial['paired_block']]
        for metric,observed in factorial['interactions'].items():
            values=[arms[a].get(metric) for a in ('R1_S1','R1_S0','R0_S1','R0_S0')]
            if None in values:assert observed is None
            else:assert abs(values[0]-values[1]-values[2]+values[3]-observed)<1e-8
    source_index={}
    for r in metadata['h3_sources']:
        source_index[runs[r['cell_id']]['paired_block'],r['source_id'],r['arm']]=dict(r,**op_source[r['cell_id'],r['source_id']])
    for item in pair_result['source_paired_conditional_sign_diagnostics']:
        for observation in item['observations']:
            key=observation['paired_block'],observation['source_id']
            left,right=source_index[key+(item['left'],)],source_index[key+(item['right'],)]
            assert abs(right[item['metric']]-left[item['metric']]-observation['difference'])<1e-8
        positive=sum(x['difference']>0 for x in item['observations']);negative=sum(x['difference']<0 for x in item['observations'])
        n=positive+negative;num=min(2*sum(comb(n,k) for k in range(min(positive,negative)+1)),2**n)
        expected=item['exact_sign_diagnostic'];assert (positive,negative,num,2**n)==(expected['positive'],expected['negative'],expected['two_sided_p_exact_numerator'],expected['two_sided_p_exact_denominator'])
    nr=metadata['new8_report'];sens=json.loads((out/'NEW8_EXACT_PAIRED_AND_LEAVE_OUT.json').read_bytes())
    gains=[Fraction(str(x['fullcall_credit_audio_s']))-Fraction(str(x['conservative_credit_audio_s'])) for x in nr['source_pairs']]
    extreme=sum(abs(sum(s*v for s,v in zip(signs,gains)))>=abs(sum(gains)) for signs in product((-1,1),repeat=8))
    assert len(gains)==8 and sens['exact_extreme_assignments']==extreme and sens['total_label_swaps']==256 and extreme>=2
    for subset in sens['all_leave_zero_one_two_out']:
        kept=[x for x in nr['source_pairs'] if x['speaker_id'] not in subset['excluded_speakers']]
        offers=sum(Fraction(str(x['offered_audio_s'])) for x in kept)
        gain=sum(Fraction(str(x['fullcall_credit_audio_s']))-Fraction(str(x['conservative_credit_audio_s'])) for x in kept)
        assert abs(float(100*gain/offers)-subset['coverage_gain_pp'])<1e-8
    return dict(status='PASS_INDEPENDENT_ALL_ORIGINAL_ROWS_MIN_DISTANCE_OPERATION_PROOF_AND_LIFETIMES',
        cells=len(cfg['cells']),source_mode_conventions=totals['sources'],checked_events=checked_events,
        checked_edit_operations=checked_operations,groups=[dict(bank=k[0],stage=k[1],arm=k[2],mode=k[3],convention=k[4],**dict(v)) for k,v in sorted(per_group.items())],
        H3_contrasts_checked=220,H3_factorials_checked=22,new8_exact_assignments_checked=256,
        scope='Independent literal raw-row, minimum-distance and emitted-operation replay, metadata contrasts and exact sign numerators; does not independently enumerate all-optimal alignment bounds or make semantic/serving claims',new_model_calls=0)
