"""Causal observers over a fixed already completed Consumer candidate schedule.

All computation, original C/U and selected G are inherited unchanged. ACK/GC
effects of replacing the deployed Consumer are outside this offline estimand.
"""
from collections import Counter
from dataclasses import asdict
import heapq
from agreement import RULES, LocalAgreement2
from support import WholeView, pick, rebase_all


def source_replay(sid, rows, publications, facts, initial, ingress, frames, horizon):
    from feedback_contract import FeedbackCut, BranchStep, Reconciler
    r = Reconciler(FeedbackCut(initial), True)
    pubs = {(p['bound_owner_epoch'], p['event']['publication_id']): p['event'] for p in publications}
    byseq = {f['sequence']: f for f in facts}
    accepted = {}
    for x in ingress:
        if x['kind'] != 'accepted_input' or x['source_id'] != sid: continue
        F=x['frontier']
        if F in accepted: raise ValueError('duplicate original offered frontier')
        accepted[F]=x
    expected=list(range(8000,frames,8000))+[frames]
    if sorted(accepted)!=expected: raise ValueError('all original offered frontiers required')
    seq = [x for x in rows if x['source_id'] == sid]
    if not seq or any(b['observed']<a['observed'] for a,b in zip(seq,seq[1:])): raise ValueError('Consumer time order')
    la=LocalAgreement2(); pool=[]; proof_pair=[]; prior_update=None; timers=[]; outputs={k:[] for k in RULES}
    prefix=[]; decisions=[]; counts=Counter(); processed=0; last_time=None; terminated=False
    canonical=WholeView('genesis',sid,seq[0]['observed'],r.canonical,(),r.canonical,r.canonical.transcript)
    genesis=canonical;canonical_history=[canonical]

    def emit(t, kind, actual=None):
        nonlocal last_time
        if t>horizon or (last_time is not None and t<last_time): raise ValueError('shadow causal horizon/order')
        chosen={'canonical_only':canonical,
                # Historical C/U views are immutable delivered facts, not private
                # paths. They may remain displayed during a read-policy delay.
                'fixed_lag_0p5':canonical if terminated else pick(pool+canonical_history,genesis,t,lag=.5),
                'LA2_CP':pick(pool,canonical,t,confirmed=la.confirmed)}
        for rule,c in chosen.items():
            outputs[rule].append(dict(source_id=sid,observed=t,kind=kind,text=c.text,
                visible_frontier=c.visible_frontier,certified_frontier=processed,
                candidate_identity=c.identity,actual_candidate_received=c.received,
                offline_observer=True))
        if actual is not None:
            outputs['actual_SUP'].append(dict(actual))
        mapped=chosen['LA2_CP']
        prefix.append(dict(source_id=sid,observed=t,kind=kind,text=la.confirmed,
            # Deliberately no invented audio frontier for the free character prefix.
            mapped_whole_view_code_points=len(mapped.text),unmapped_code_points=max(0,len(la.confirmed)-len(mapped.text)),
            text_prefix_audio_alignment_available=False))
        last_time=t

    for index,row in enumerate(seq):
        now=row['observed']
        while timers and timers[0][0]<now:
            t,identity=heapq.heappop(timers)
            emit(t,'offline_fixed_lag_timer')
        event=pubs.get((row['owner_epoch'],row.get('publication_id')))
        reset=False
        if row['kind']=='canonical':
            fact=byseq[row['journal_sequence']]['body']; target=FeedbackCut(fact['next_state'])
            if fact['source_id']!=sid: raise ValueError('fact source changed')
            r.install(target)
            if fact['record']['native_model_evaluated']: processed=target.frontier
            pool, classes = rebase_all(pool,target); counts.update({'support_'+k:v for k,v in classes.items()})
            new_proof=[]; incompatible=False
            for p in proof_pair:
                status,updated=p.rebase(target)
                incompatible |= status=='refuted'
                if updated is not None:new_proof.append(updated)
            proof_pair=new_proof
            if prior_update is not None:
                status,updated=prior_update.rebase(target)
                if status=='refuted': incompatible=True; prior_update=None
                elif status=='covered': prior_update=None;la.previous=None
                elif updated is not None: prior_update=updated
            # A free text prefix has no frontier of its own. If all of its
            # proving views have become covered and C/U does not contain that
            # prefix, it cannot inherit support merely from matching text.
            unsupported_tail=bool(la.confirmed and not proof_pair and
                la.confirmed.startswith(target.transcript) and la.confirmed!=target.transcript)
            reset=la.canonical(target.transcript,incompatible or unsupported_tail)
            if reset: proof_pair=[]; prior_update=None
            canonical=WholeView('canonical:'+str(row['journal_sequence']),sid,now,target,(),target,target.transcript)
            canonical_history.append(canonical)
            if target.frontier==frames:
                if terminated: raise ValueError('duplicate terminal canonical')
                la.terminal(target.transcript); terminated=True; counts['terminal_actual_C_U_releases']+=1
        elif row['kind']=='private':
            if event is None or event['canonical_sha']!=r.canonical.sha256: raise ValueError('private publication/root missing')
            previous=r.canonical; steps=[]
            for s in event['steps']:
                a,b=FeedbackCut(s['start']),FeedbackCut(s['end'])
                if not a.same(previous): raise ValueError('private complete path gap')
                steps.append(BranchStep(s['job_id'],a.sha256,a,b)); previous=b
            if previous.frontier>=r.tail.frontier:r.steps=steps
        else: raise ValueError('unknown applied Consumer row')
        visible=r.visible()
        if not visible['text']: visible['visible_frontier']=0
        for key in ('text','visible_frontier','canonical_sha','private_job'):
            if row[key]!=visible[key]: raise ValueError('replayed actual Consumer view mismatch: '+key)
        if row['certified_frontier']!=processed: raise ValueError('selected original G changed')
        identity=f"{row['owner_epoch']}:{row.get('publication_id','replay:'+str(row.get('journal_sequence')))}:{index}"
        current=WholeView(identity,sid,now,r.canonical,tuple(r.steps),r.tail,row['text'])
        pool.append(current); counts['actual_delivered_whole_views']+=1
        if now+.5<=horizon:heapq.heappush(timers,(now+.5,identity))
        F=current.visible_frontier
        if F>0:
            if F not in accepted or accepted[F]['observed']>now or accepted[F]['original_offer']>now:
                raise ValueError('candidate precedes its actual accepted audio obligation')
            if F>la.max_audio_frontier:
                if terminated:
                    # The source terminal C/U is a distinct flush, not LA sample 2.
                    la.max_audio_frontier=F; counts['new_audio_seen_only_at_terminal']+=1
                else:
                    extended=la.update(current.text,F)
                    if extended: proof_pair=[p for p in (prior_update,current) if p is not None]
                    prior_update=current
            else:
                la.ignored_same_or_older_frontier+=1
        emit(now,'actual_Consumer_delivery',row)
        decisions.append(dict(source_id=sid,row_index=index,observed=now,kind=row['kind'],
            actual_frontier=F,new_audio_updates_so_far=la.updates,LA2_confirmed_code_points=len(la.confirmed),
            canonical_support_reset=reset,terminal_actual_C_U=terminated,canonical_frontier=r.canonical.frontier))
    while timers:
        t,identity=heapq.heappop(timers)
        if t<=horizon: emit(t,'offline_fixed_lag_timer')
    if not terminated: raise ValueError('actual final C/U absent')
    for rule in RULES:
        if outputs[rule][-1]['text']!=r.canonical.transcript: raise ValueError('final text differs: '+rule)
    if prefix[-1]['text']!=r.canonical.transcript: raise ValueError('final prefix text differs')
    return outputs,prefix,dict(counts,agreement=asdict(la)),decisions


def endpoints(rows, accepted, frames):
    result=[]; past=0
    horizon=rows[-1]['observed']
    for F in list(range(8000,frames,8000))+[frames]:
        offer=accepted[F]['original_offer']
        v=next((r for r in rows if r['observed']>=offer and r['visible_frontier']>=F),None)
        g=next((r for r in rows if r['observed']>=offer and r['certified_frontier']>=F),None)
        D=v['observed']-offer if v else None; C=g['observed']-offer if g else None
        stop=min(offer+2.,horizon)
        points=sorted({offer,stop}|{r['observed'] for r in rows if offer<r['observed']<stop})
        covered=0.;after_first_gap=False
        for left,right in zip(points,points[1:]):
            at=next((r for r in reversed(rows) if r['observed']<=left),None)
            holds=at is not None and at['visible_frontier']>=F
            if holds:covered+=right-left
            if v is not None and left>=v['observed'] and not holds and right>left:after_first_gap=True
        censored=max(0.,offer+2.-horizon)
        at_deadline=next((r for r in reversed(rows) if r['observed']<=offer+2.),None) if horizon>=offer+2. else None
        result.append(dict(frontier=F,weight_audio_seconds=(F-past)/16000,EOS=F==frames,
            offline_shadow_D=D,unchanged_original_C=C,dual_credit=D is not None and C is not None and D<=2 and C<=8,
            within_D_window_observed_covered_wall_seconds=covered,
            within_D_window_unobserved_right_censored_wall_seconds=censored,
            within_D_window_coverage_wall_seconds_lower_bound=covered,
            within_D_window_coverage_wall_seconds_upper_bound=covered+censored,
            covered_at_D_deadline=(at_deadline['visible_frontier']>=F) if at_deadline is not None else None,
            actual_retreat_after_first_cover_within_observed_D_window=after_first_gap,
            continuity_interval='[original_offer, min(original_offer+2,last actual same-source Consumer time)); no extrapolation'))
        past=F
    return result


def frontier_retreats(rows):
    previous=0;events=[]
    for i,r in enumerate(rows):
        F=r['visible_frontier']
        if F<previous:events.append(dict(row_index=i,observed=r['observed'],before_frontier=previous,after_frontier=F,
            lost_audio_seconds=(previous-F)/16000))
        previous=F
    return dict(events=events,count=len(events),sum_event_retreat_audio_seconds=sum(r['lost_audio_seconds'] for r in events),
        scope='Observed frontier retreats on this offline trajectory; sum may revisit the same audio, not unique lost audio or causal delay')
