from dataclasses import replace
from copy import deepcopy
import math,random
from revtrace.ces_closed_loop import _row_probability,choose_closed_loop,PlannerConfig,ClosedLoopState
from revtrace.ces_v5_policy import BatchOutcome
from test_closed_loop_independent import calibration,target,context

def test_probability_cache_is_exact_at_all_boundaries_and_reused_outcomes():
    rng=random.Random(20261025);cache={}
    for n in [1,2,8,16]:
        values=tuple(sorted(rng.random()*2 for _ in range(n)))
        o=BatchOutcome(.25,2.,.2,1.4,.3,'fixture',values,values)
        for now in [0.,1e6,4660000.123]:
            for v in values:
                for bound in [v,math.nextafter(v,math.inf),math.nextafter(v,-math.inf)]:
                    due=now+.08+bound
                    assert _row_probability(o,due,now,.08,cache)==_row_probability(o,due,now,.08)
    assert cache['row_probability_queries']

def test_all_planner_output_fields_are_identical_with_cache():
    for n in [1,2,4,8,16]:
        rows=[target(sid=i,release=float(i%3),candidate_ready=i%2==0,display_expired=False) for i in range(n)]
        cs={r.sid:context(r) for r in rows}
        for mode in ['service_cost','reserved_progress','inherit','causal']:
            kw=dict(now=2.,mode=mode,cal=calibration(),limit=16,observed_credit_audio=2.,elapsed_seconds=4.,display_slo=2.)
            original=choose_closed_loop(rows,cs,state=ClosedLoopState(),config=PlannerConfig(),**kw)
            fast=choose_closed_loop(rows,cs,state=ClosedLoopState(),config=PlannerConfig(cache_mode='memoized'),**kw)
            assert original==fast

def test_soft_guard_keeps_aging_without_authorization_or_dropped_work():
    rows=[target(sid=0,release=-6.5,display_expired=True),target(sid=1,release=-1.5,candidate_ready=True,display_expired=False)]
    cs={r.sid:context(r) for r in rows};book=ClosedLoopState();book.observe(cs,0.)
    book.records[cs[0].identity].promised_finish=1.4
    kw=dict(now=0.,mode='causal',cal=calibration(single=1.4),limit=16,observed_credit_audio=0.,elapsed_seconds=1.,display_slo=2.)
    before=deepcopy(book.to_audit())
    hard=choose_closed_loop(rows,cs,state=deepcopy(book),config=PlannerConfig(),**kw)
    soft=choose_closed_loop(rows,cs,state=deepcopy(book),config=PlannerConfig(guard_mode='soft'),**kw)
    assert hard['sids']==[0] and soft['sids']==[1]
    book.records[cs[0].identity].deferrals=2
    for g in ['hard','soft','aging']:
        choice=choose_closed_loop(rows,cs,state=deepcopy(book),config=PlannerConfig(guard_mode=g),**kw)
        assert 0 in choice['sids']
        assert sorted(s for p in choice['plan'] for s in p['sids'])==[0,1]
    assert not before['authorization_state']
