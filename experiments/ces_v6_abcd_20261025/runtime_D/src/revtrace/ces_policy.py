"""Bounded causal evidence planning; predictions never authorize an install.

All times are in the current owner's monotonic clock. Features contain no
injected-fault annotations, generated future outputs or counterfactual labels.
"""
from dataclasses import dataclass,asdict
import itertools,math

@dataclass(frozen=True)
class Target:
    sid:int
    window:int
    ready:float
    deadline:float
    candidate_ready:bool
    same_birth:bool
    previous_reject:bool
    candidate_tokens:int
    descendant_count:int
    descendant_seconds:float
    candidate_eta:float|None
    projection_compatible:bool=False
    audio_seconds:float=0.
    interval_seconds:float=0.
    prompt_tokens:int=0

def cost(cal,mode,n,rows=None):
    if not n:return 0.
    model=cal.get('contextual_cost_models',{}).get(mode)
    if model is not None and rows:
        a=max(t.audio_seconds for t in rows)
        x=[1.,float(n),sum(t.audio_seconds for t in rows)/len(rows)*n/10.,n*a*a/100.,
          n*max(t.prompt_tokens for t in rows)/256.,n*max(t.interval_seconds for t in rows)/2.,
          n*max(t.candidate_tokens for t in rows)/32. if mode=='verify' else 0.]
        predicted=sum(v*c for v,c in zip(x,model['coefficients']))
        return min(model.get('prediction_ceiling_s',float('inf')),max(model['prediction_floor_s'],predicted))
    table=cal['cost_seconds'][mode];b=min(map(int,table),key=lambda b:abs(b-n))
    return max(1e-4,float(table[str(b)]))

def rejection(cal,t,causal=True):
    if not causal:return cal['global_reject']
    k=('same' if t.same_birth else 'mismatch')+('-prev-reject' if t.previous_reject else '-prev-ok')
    return cal['causal_reject'].get(k,{}).get('p',cal['global_reject'])

def verify_cost(cal,rows,causal):
    if not rows:return 0.
    # Verification is one homogeneous batch. Fallback is an additional paid
    # invocation, not free per-row work. Estimate probability any row rejects.
    ps=[rejection(cal,t,causal) for t in rows]
    any_bad=1-math.prod(1-p for p in ps)
    expected_failed=max(1,math.ceil(sum(ps)))
    return cost(cal,'verify',len(rows),rows)+any_bad*cost(cal,'fallback',expected_failed,rows)

def choose(targets,*,now,mode,cal,limit,display_slo=2.,wait_cap=.15):
    """Return one physical homogeneous batch, or a bounded wait.

    Cost-only is a strong myopic expected-work rule using the same empirical
    physical cost curves. CES additionally evaluates alternative joint batch
    partitions/orders, deadlines, observed birth/rejection and issued children.
    It does not assume a stale candidate must be rejected.
    """
    ts=sorted(targets,key=lambda t:(t.deadline,t.sid))[:limit]
    if not ts:return {'operation':None,'sids':[],'reason':'no-released-target'}
    if mode in ['fine','standard']:
        return {'operation':'generate','sids':[t.sid for t in ts],'reason':'fixed-independent'}
    if mode=='strict':
        rows=[t for t in ts if t.candidate_ready]
        return {'operation':'verify' if rows else None,'sids':[t.sid for t in rows],'reason':'fixed-strict-readiness'}
    if mode in ['readiness','ready_any']:
        rows=[t for t in ts if t.candidate_ready and (mode=='ready_any' or t.same_birth)]
        if rows:return {'operation':'verify','sids':[t.sid for t in rows],'reason':'birth-ready-gate'}
        return {'operation':'generate','sids':[t.sid for t in ts],'reason':'gate-independent'}
    if mode=='causal_only':
        singles=[(t,choose([t],now=now,mode='ces',cal=cal,limit=1,display_slo=display_slo,wait_cap=wait_cap)) for t in ts]
        ready_decisions=[(t,d) for t,d in singles if d['operation'] is not None]
        if ready_decisions:
            first=ready_decisions[0][1]['operation']
            return {'operation':first,'sids':[t.sid for t,d in ready_decisions if d['operation']==first],'reason':'causal-rowwise-no-joint-plan'}
        waits=[d.get('wait_seconds',wait_cap) for _,d in singles]
        return {'operation':None,'sids':[],'reason':'causal-rowwise-wait','wait_seconds':min(waits)}
    if mode not in ['cost_gate','cost','ces']:raise ValueError('undeclared CES policy')
    if mode=='cost_gate':
        vs=[t for t in ts if t.candidate_ready]
        # Joint physical costs are supplied even to this noncausal ablation;
        # full CES cannot claim mere batch-cost awareness as its new feature.
        if vs and verify_cost(cal,vs,False)/len(vs)<cost(cal,'generate',len(ts),ts)/len(ts):
            return {'operation':'verify','sids':[t.sid for t in vs],'reason':'global-expected-cost'}
        return {'operation':'generate','sids':[t.sid for t in ts],'reason':'global-expected-cost'}
    causal=mode=='ces'
    ready=[t for t in ts if t.candidate_ready]
    # Enumerate causal benefit-sorted partitions and orders, not 2^16 masks.
    ranked=sorted(ready,key=lambda t:(rejection(cal,t,causal),t.deadline,t.sid))
    plans=[]
    for k in range(len(ranked)+1):
        vr=ranked[:k];ids={t.sid for t in vr};dr=[t for t in ts if t.sid not in ids]
        orders=[(('verify',vr),('generate',dr)),(('generate',dr),('verify',vr))] if vr and dr else [(('verify',vr),('generate',dr))]
        for order in orders:
            cursor=now;score=0.;first=None;work=0.
            for op,rows in order:
                if not rows:continue
                duration=verify_cost(cal,rows,causal) if op=='verify' else cost(cal,'generate',len(rows),rows)
                if first is None:first=(op,rows)
                started=cursor;cursor+=duration;work+=duration
                for t in rows:
                    # Accepted rows complete at verification, not after a
                    # peer's fallback. Physical occupancy still includes it.
                    p=rejection(cal,t,causal)
                    if op=='verify':
                        failure_count=max(1,math.ceil(sum(rejection(cal,x,causal) for x in rows)))
                        finish=started+cost(cal,'verify',len(rows),rows)+p*cost(cal,'fallback',failure_count,rows)
                    else:
                        table=cal.get('generation_row_fraction',{})
                        b=min(map(int,table),key=lambda b:abs(b-len(rows))) if table else None
                        finish=started+duration*(table[str(b)] if b else 1.)
                    age=finish-t.ready
                    score+=max(0.,finish-t.deadline)*4.+max(0.,age-display_slo)
                    # Verification acceptance alone does not imply Exact-P
                    # preservation. A deterministic target render previews only
                    # conditional compatibility; it is never generation proof.
                    loss=p if t.projection_compatible else 1.
                    # Both evidence modes can select the same legal P. Do not
                    # invent an operation-specific preservation advantage.
                    if causal:score+=.25*loss*(t.descendant_seconds+max(0.,finish-now)*t.descendant_count)
            score+=work
            plans.append((score,first,work))
    score,(op,rows),work=min(plans,key=lambda p:(p[0],p[1][0]!='generate'))
    waiting=[t for t in ts if not t.candidate_ready and t.candidate_eta is not None]
    # Only wait for an already dispatched actual candidate with a bounded ETA;
    # wait does not reserve/release a physical lease or advance any frontier.
    if waiting and len(waiting)==len(ts):
        delay=max(t.candidate_eta for t in waiting)
        hypothetical=[Target(**dict(asdict(t),candidate_ready=True)) for t in ts]
        after=verify_cost(cal,hypothetical,causal)
        direct=cost(cal,'generate',len(ts),ts)
        if 0<delay<=wait_cap and delay+after<direct and now+delay+after<min(t.deadline for t in ts):
            return {'operation':None,'sids':[],'reason':'bounded-inflight-candidate-wait','wait_seconds':delay,'score':score}
    return {'operation':op,'sids':[t.sid for t in rows],'reason':'causal-joint-plan','score':score,'planned_seconds':work,
      'partitions_evaluated':len(plans)}
