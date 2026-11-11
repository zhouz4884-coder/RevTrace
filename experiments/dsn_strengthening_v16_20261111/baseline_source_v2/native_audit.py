"""Independent reread of actual native jobs, Consumer and trusted histories."""
import argparse,json,pathlib,collections
from feedback_contract import FeedbackCut
from native_service import paired_metrics
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def meaningful_selection(selection):
    previous=selection['previous_transcription'].rstrip('\ufffd').strip();before=selection['candidates'][0].rstrip('\ufffd').strip()
    after=(selection['previous_transcription']+selection['corrected_appended_text']).strip()
    continuation=before[len(previous):].strip() if before.startswith(previous) else None
    return dict(changed=selection['candidates'][0]!=after,
        nonempty_content=bool(continuation) or bool(selection['corrected_appended_text'].strip()),
        candidate_continuation=continuation,selected_continuation=selection['corrected_appended_text'])
def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        new=[i]
        for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=new
    return row[-1]
def audit_cell(out):
    out=pathlib.Path(out);config=read(out/'CONFIG.json');source={s['source_id']:s for s in config['settings']['sources']}
    jobs=lines(out/'native_jobs.jsonl');consumer=lines(out/'consumer.jsonl');hist=read(out/'CANONICAL_HISTORIES.json')
    nodes={};canon={};ids=set();correction=[]
    for j in jobs:
        if j['job_id'] in ids:raise ValueError('duplicate actual model completion')
        ids.add(j['job_id']);a,b=FeedbackCut(j['start']),FeedbackCut(j['end']);r=j['record'];sid=j['source_id']
        if r['start_state']!=a.sha256 or r['end_state']!=b.sha256 or a.frontier!=r['start'] or b.frontier!=r['end']:raise ValueError('actual native state binding mismatch')
        if b.state['contract']['source_sha']!=source[sid]['audio_sha256'] or a.state['contract']!=b.state['contract']:raise ValueError('cross-source/contract model completion')
        if b.frontier<=a.frontier or b.frontier>source[sid]['frames']:raise ValueError('native input interval')
        if r['model_end']<r['model_start'] or not r['physical_early_exit'] is False:raise ValueError('invalid native execution lifetime')
        nodes[j['job_id']]=dict(start=a,end=b,role=r['role'],source_id=sid,record=r)
        if r['role']=='authority':
            if sid in canon and not a.same(canon[sid][-1]):raise ValueError('trusted native history discontinuity')
            canon.setdefault(sid,[]).append(b)
            c=r['selected_correction']
            if c is not None:
                if c.get('private_identity_prediction'):raise ValueError('Authority used identity prediction')
                before=c['candidates'][0];after=(c['previous_transcription']+c['corrected_appended_text']).strip()
                if (before!=after)!=r['selection_changed']:raise ValueError('correction classification mismatch')
                correction.append(dict(source_id=sid,frontier=b.frontier,**meaningful_selection(c)))
    for sid,s in source.items():
        actual=canon.get(sid,[])
        if not actual or actual[-1].frontier!=s['frames']:raise ValueError('full offered source not consumed by Authority')
        if [x.sha256 for x in actual]!=[x['state_sha256'] for x in hist[sid]]:raise ValueError('recorded canonical history differs from actual native jobs')
    installed={x.sha256:x for xs in canon.values() for x in xs};private_applied=0
    ready=read(out/'READY.json');primary=next(v for k,v in ready.items() if k.startswith('authority'))
    for s in primary['initials'].values():
        c=FeedbackCut(s);installed[c.sha256]=c
    by_end=collections.defaultdict(list)
    for node in nodes.values():
        if node['role']=='private':by_end[node['end'].sha256].append(node)
    for row in consumer:
        if row['canonical_sha'] not in installed:raise ValueError('Consumer claims nonexecuted trusted state')
        c=installed[row['canonical_sha']]
        if row['certified_frontier']>c.frontier or row['visible_frontier']<0:raise ValueError('Consumer frontier contract')
        if row['private_job'] is None:
            if row['text']!=c.transcript:raise ValueError('Consumer canonical text not actually selected')
        else:
            node=nodes.get(row['private_job'])
            if not node or node['role']!='private' or node['source_id']!=row['source_id']:raise ValueError('Consumer private result not actually executed')
            end=node['end']
            if row['text']!=end.transcript or row['visible_frontier']!=end.frontier:raise ValueError('actual private output differs from display')
            # Follow full native state links back to this exact trusted cut.
            seen=set();pending=[node];found=False
            while pending:
                node=pending.pop()
                if node['start'].same(c):found=True;break
                key=node['start'].sha256
                if key in seen:continue
                seen.add(key);pending.extend(by_end[key])
            if not found:raise ValueError('Consumer private branch lacks compatible complete trusted ancestry')
            private_applied+=1
    origin=read(out/'ORIGIN.json')['origin_perf'];old=read(out/'SERVICE_METRICS.json')
    metrics=paired_metrics(list(source.values()),consumer,origin,origin+old['service_wall_seconds'])
    if metrics!=old:raise ValueError('independent actual Consumer service recount differs')
    canonical_at={(sid,c.frontier):c for sid,seq in canon.items() for c in seq}
    agreeing_credit=0.;different_credit=0.;unmatched_credit=0.
    for f in metrics['frontier_rows']:
        if not f['dual_met']:continue
        sid=f['source_id'];F=f['frontier'];offered=f['offered']
        first=next(r for r in consumer if r['source_id']==sid and r['observed']>=offered and r['visible_frontier']>=F)
        target=canonical_at.get((sid,first['visible_frontier']))
        if target is None:unmatched_credit+=f['seconds']
        elif first['text']==target.transcript:agreeing_credit+=f['seconds']
        else:different_credit+=f['seconds']
    quality=[]
    for sid,s in source.items():
        reference=''.join(s['reference'].split());hypothesis=''.join(canon[sid][-1].transcript.split())
        if not reference:raise ValueError('complete reference denominator missing')
        quality.append(dict(source_id=sid,reference_characters=len(reference),character_edits=distance(reference,hypothesis)))
    recons={(x['source_id'],x['frontier']):x for x in read(out/'RECONCILIATION.json')}
    meaningful=[]
    for x in correction:
        if not x['nonempty_content']:continue
        r=recons[(x['source_id'],x['frontier'])]
        pending=nodes.get(r['pending_job']) if r['private_pending_ahead'] else None
        actual_work_started=bool(pending and pending['record']['native_model_evaluated'] and pending['record']['model_start']<=r['time'])
        physical_inflight=bool(actual_work_started and pending['record']['model_end']>=r['time'])
        completed_unconsumed=bool(actual_work_started and pending['record']['model_end']<r['time'])
        meaningful.append(dict(**x,private_ahead=r['ahead'],private_inflight_ahead=physical_inflight,
            private_completed_unconsumed_ahead=completed_unconsumed,
            compatible=r['compatible'],retained_steps=r['retained_steps']))
    return dict(source_ids=sorted(source),native_completions=len(jobs),private_consumer_applications=private_applied,
        corrected_updates=sum(x['changed'] for x in correction),unchanged_updates=sum(not x['changed'] for x in correction),
        native_correction_updates=len(correction),canonical_history_sha={sid:[x.sha256 for x in seq] for sid,seq in canon.items()},
        meaningful_feedback_updates=meaningful,
        nonempty_corrected_updates=sum(x['changed'] for x in meaningful),
        nonempty_unchanged_updates=sum(not x['changed'] for x in meaningful),
        nonempty_corrected_interleavings=sum(x['changed'] and (x['private_ahead'] or x['private_inflight_ahead'] or x['private_completed_unconsumed_ahead']) for x in meaningful),
        nonempty_unchanged_interleavings=sum(not x['changed'] and (x['private_ahead'] or x['private_inflight_ahead'] or x['private_completed_unconsumed_ahead']) for x in meaningful),
        nonempty_unchanged_retained_ahead=sum(not x['changed'] and x['private_ahead'] and x['compatible'] and x['retained_steps']>0 for x in meaningful),
        final_transcripts={sid:seq[-1].transcript for sid,seq in canon.items()},
        quality=dict(normalization='remove whitespace only; controlled-adaptation CER, not the paper CER protocol',
            sources=quality,reference_characters=sum(x['reference_characters'] for x in quality),
            character_edits=sum(x['character_edits'] for x in quality)),
        retrospective_content=dict(scope='selected native model agreement at the actual displayed frontier; not ground truth or an online controller test',
            raw_agreeing_dual_deadline_audio_seconds=agreeing_credit,raw_different_dual_deadline_audio_seconds=different_credit,
            unmatched_dual_deadline_audio_seconds=unmatched_credit),
        metrics={k:v for k,v in metrics.items() if k!='frontier_rows'})
def audit_campaign(plan):
    result=[];groups=collections.defaultdict(list);failed=[]
    for cell in plan['cells']:
        if cell.get('stage')!='formal':continue
        try:
            a=audit_cell(cell['out']);a.update(cell_id=cell['cell_id'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat']);result.append(a);groups[cell['cohort']].append(a)
        except Exception as e:failed.append(dict(cell_id=cell['cell_id'],error=type(e).__name__+': '+str(e)))
    histories=[]
    for cohort,rows in groups.items():
        first=rows[0]['canonical_history_sha'];same=all(x['canonical_history_sha']==first for x in rows)
        histories.append(dict(cohort=cohort,observed_cells=len(rows),expected_cells=6,complete_exact_native_history_equal=same))
    ok=not failed and len(result)==12 and len(histories)==2 and all(x['observed_cells']==6 and x['complete_exact_native_history_equal'] for x in histories)
    return dict(status='PASS_TWELVE_ACTUAL_NATIVE_CELLS_AND_FULL_HISTORY_EQUIVALENCE' if ok else 'INCOMPLETE_OR_MISMATCH_PRESERVED',cells=result,failures=failed,canonical_history_groups=histories)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r=audit_campaign(read(a.plan));a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='cells'},indent=2))
