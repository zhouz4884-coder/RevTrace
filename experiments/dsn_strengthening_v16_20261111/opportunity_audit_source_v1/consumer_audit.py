"""Replay only actually applied Consumer rows against original full publications."""
from collections import Counter
from definitions import loss_window,sha_state

def provisional_registry(dispatches,worker_rows):
    from resilience_inbound import semantic_fingerprint
    jobs={r['job']['job_id']:r['job'] for r in dispatches};registry={jid:dict(job=j,asr_ends={},full_ends={}) for jid,j in jobs.items()}
    if len(jobs)!=len(dispatches):raise ValueError('duplicate provisional registry job')
    for row in worker_rows:
        e=row['event'];kind=e.get('kind');jid=e.get('job_id')
        if kind not in ('asr_early','completed'):continue
        if jid not in jobs:raise ValueError('provisional source message has no dispatch')
        j=jobs[jid]
        if e['source_id']!=j['source_id'] or e['worker']!=j['worker'] or row['physical_slot']!=j['worker'] or row['physical_incarnation']!=j['worker_incarnation'] or e['worker_incarnation']!=j['worker_incarnation'] or e['dispatch_epoch']!=j['dispatch_epoch']:
            raise ValueError('provisional source physical/job identity changed')
        start=e['start_state'] if kind=='asr_early' else e['start']
        if sha_state(start)!=sha_state(j['start']):raise ValueError('provisional source complete input changed')
        if kind=='asr_early':
            p=e['projection'];end=p['end']
            if e['start_state_sha']!=sha_state(start) or e['end_frontier']!=j['end'] or e['producer_role']!='authority' or e.get('candidate_wire') is not None or p['kind']!='typed_ASR_stage_identity_feedback_projection' or p['learned_C_executed'] is not False or p['original_full_infer_completed'] is not False or p['end_state_sha']!=sha_state(end):raise ValueError('not an actual protected ASR projection')
            family='asr_ends';time=e['produced_perf']
        else:
            p=e['record'];end=e['end']
            if p['role']!='authority' or p['candidate_handoff'] is not False or type(p.get('native_model_evaluated')) is not bool or p['start_state']!=sha_state(start) or p['end_state']!=sha_state(end):raise ValueError('not an actual complete original full result')
            family='full_ends';time=p['model_end']
        if end['frontier']!=j['end'] or end['contract']!=start['contract']:raise ValueError('provisional source target/contract changed')
        fingerprints=registry[jid].setdefault('phase_fingerprints',{})
        fingerprint=semantic_fingerprint(e)
        if kind in fingerprints and fingerprints[kind]!=fingerprint:raise ValueError('contradictory same-phase protected receipt')
        fingerprints[kind]=fingerprint
        previous=registry[jid][family].get(sha_state(end),{})
        dequeues=[x for x in (previous.get('owner_dequeued_perf'),row.get('owner_dequeued_perf')) if x is not None]
        registry[jid][family][sha_state(end)]=dict(available_lower_bound=min(previous.get('available_lower_bound',time),time),owner_dequeued_perf=min(dequeues) if dequeues else None)
    return registry

def audit_consumer(rows,publications,facts,initials,registry):
    from feedback_contract import FeedbackCut,BranchStep,Reconciler
    states={sid:Reconciler(FeedbackCut(cut),True) for sid,cut in initials.items()}
    processed={sid:0 for sid in initials};byseq={f['sequence']:f for f in facts}
    pubs={}
    for p in publications:
        e=p['event'];key=p['bound_owner_epoch'],e['publication_id']
        if key in pubs and pubs[key]['event']!=e:raise ValueError('changed publication identity')
        pubs[key]=dict(event=e,received_perf=p.get('received_perf'))
    counts=Counter();events=[]
    for index,row in enumerate(rows):
        sid=row['source_id'];r=states[sid];before=r.visible();previous_tail=r.tail
        publication=pubs.get((row['owner_epoch'],row.get('publication_id')))
        event=publication['event'] if publication else None
        if row['kind']=='canonical':
            f=byseq[row['journal_sequence']];body=f['body'];target=FeedbackCut(body['next_state'])
            if not r.canonical.same(FeedbackCut(body['parent_state'])):raise ValueError('Consumer fact parent gap')
            if event is not None and (event['kind']!='canonical' or event['state']!=body['next_state']):raise ValueError('canonical publication changed complete fact')
            if event is not None:
                receipt=event['durable_receipt']
                for key in ('sequence','record_sha256','offset','end_offset'):
                    if receipt[key]!=f['receipt'][key]:raise ValueError('applied publication durable receipt mismatch')
            if event is None and not row.get('recovery_replay'):raise ValueError('missing applied canonical publication')
            reconciliation=r.install(target)
            if body['record']['native_model_evaluated']:processed[sid]=target.frontier
            ahead=previous_tail.frontier>target.frontier
            nonempty=bool(before['text']) and before['visible_frontier']>target.frontier
            if ahead:counts['internal_ahead_canonical_applications']+=1
            if nonempty:
                compatible=reconciliation['compatible'];counts['nonempty_ahead_canonical_applications']+=1
                counts['compatible_ahead_applications' if compatible else 'incompatible_ahead_applications']+=1
                preserved=r.tail.same(previous_tail)
                counts[('compatible_ahead_preserved' if preserved else 'compatible_ahead_changed') if compatible else 'necessary_incompatible_changes']+=1
                before_f=before['visible_frontier'];after_f=row['visible_frontier']
                loss=after_f<before_f
                if loss:
                    counts['avoidable_supported_view_losses' if compatible else 'necessary_incompatible_withdrawals']+=1
                window=loss_window(rows,index,sid,before_f,after_f) if loss else None
                if window:counts['supported_loss_area' if compatible else 'necessary_loss_area']+=window['area_audio_seconds_x_wall_seconds']
                events.append(dict(source_id=sid,row_index=index,owner_epoch=row['owner_epoch'],
                    observed=row['observed'],new_canonical_frontier=target.frontier,compatible=compatible,
                    preserved_complete_tip=preserved,actual_frontier_loss=loss,window=window))
        elif row['kind']=='private':
            if event is None or event['kind']!='private' or event['canonical_sha']!=r.canonical.sha256:
                raise ValueError('missing/stale actually applied private publication')
            previous=r.canonical;steps=[]
            for step in event['steps']:
                a,b=FeedbackCut(step['start']),FeedbackCut(step['end'])
                if not a.same(previous):raise ValueError('whole actual private chain is not contiguous')
                item=registry.get(step['job_id'])
                if item is None or item['job']['source_id']!=sid or sha_state(item['job']['start'])!=a.sha256 or item['job']['end']!=b.frontier:raise ValueError('private view step lacks its actual complete dispatch')
                if step.get('kind')=='typed_ASR_projection':
                    if step.get('actual_full_C_U_completed') is True:raise ValueError('ASR projection contradictorily claims completed full C/U')
                    family='asr_ends'
                elif step.get('kind')=='actual_original_full_conditional_closed_node' and step.get('actual_full_C_U_completed') is True:family='full_ends'
                else:raise ValueError('private step kind is not an actual protected receipt type')
                source=item[family].get(b.sha256)
                if source is None:raise ValueError('private complete step/end is not the actual bound ASR/full receipt')
                upper=publication['received_perf'] if publication and publication['received_perf'] is not None else row['observed']
                if source['available_lower_bound']>upper or (source['owner_dequeued_perf'] is not None and source['owner_dequeued_perf']>upper):raise ValueError('view source was not available by actual publication')
                steps.append(BranchStep(step['job_id'],a.sha256,a,b));previous=b
            if previous.frontier>=r.tail.frontier:r.steps=steps
        else:raise ValueError('unknown observed Consumer row kind')
        expected=r.visible();expected['certified_frontier']=processed[sid]
        if not expected['text']:expected['visible_frontier']=0
        for name in ('canonical_sha','text','visible_frontier','certified_frontier','private_job'):
            if row[name]!=expected[name]:raise ValueError('actual Consumer/full-support mismatch: '+name)
        counts['actual_consumer_rows_checked']+=1
    return dict(counts=dict(counts),events=events,
        scope='Actual full-chain support replay at Consumer application; fixed SUP across arms, no isolated SUP treatment effect')
