import itertools,math
from revtrace.ces_anchor import fixed_count_marginals,choose_anchor,ConditionalRiskModel,conditional_batch
from test_closed_loop_independent import calibration,target

def test_fixed_count_model_retains_batch_correlation_and_exact_count():
    ps=[.1,.3,.8,.6]
    for k in range(5):
        marginal=fixed_count_marginals(ps,k)
        assert all(0<=p<=1 for p in marginal)
        assert abs(sum(marginal)-k)<1e-10
        odds=[p/(1-p) for p in ps]
        sets=list(itertools.combinations(range(4),k));weights=[math.prod(odds[i] for i in s) for s in sets]
        for i in range(4):assert abs(marginal[i]-sum(w for s,w in zip(sets,weights) if i in s)/sum(weights))<1e-10

def test_missing_candidates_immediately_use_fine_without_cost_model():
    rows=[target(sid=i,candidate_ready=False) for i in range(16)]
    out=choose_anchor(rows,now=2.,cal={},options={})
    assert out['operation']=='generate' and out['sids']==list(range(16))

def test_sparse_risk_never_creates_a_supported_deviation():
    rows=[target(sid=i,candidate_ready=True,display_expired=False) for i in range(4)]
    out=choose_anchor(rows,now=2.,cal=calibration(),options={})
    assert out['chosen_index']==0
    assert sorted(s for p in out['plan'] for s in p['sids'])==[0,1,2,3]

def test_row_identity_conditions_completion_without_future_lengths():
    rows=[target(sid=0,candidate_ready=True,candidate_tokens=1,display_expired=False),
          target(sid=1,candidate_ready=True,candidate_tokens=200,display_expired=False)]
    from revtrace.ces_anchor import features
    bank=[]
    for _ in range(8):
        bank.append({'n':2,'x':features(rows),'K':0,'lease':1.,'verify_start':0.,'verify_time':1.,'fallback_start':1.,'fallback_time':0.,
         'rows':[{'x':[0.,0.,1/256.,0.,0.],'fraction':.1,'failed':False},
                 {'x':[0.,0.,200/256.,0.,0.],'fraction':1.,'failed':False}]})
    ds,ok,_=conditional_batch({'v6_joint_risk':{'verify':bank}},'verify',rows,{'minimum_support':8})
    assert ok
    # This fixture needs nearest support tight enough to distinguish identities;
    # both rows still retain uncertainty rather than receiving a known EOS time.
    assert all(abs(sum(w for w,_ in d['rows'][r.sid])-1)<1e-9 for d in ds for r in rows)
    assert sum(w for w,t in ds[0]['rows'][0] if t<=.5)>sum(w for w,t in ds[0]['rows'][1] if t<=.5)

def test_hold_does_not_block_unrelated_result_or_event_loop():
    from types import SimpleNamespace
    from revtrace.ces_v6_owner import V6OwnerMixin
    obj=SimpleNamespace(v6={'authority_hold_seconds':1.5,'hold_at_window':5},_v6_holds={},
        jobs={'a':{'job_id':'a','end_window':5},'b':{'job_id':'b','end_window':6}},clock=lambda:10.,_event=lambda *a,**k:None)
    a=SimpleNamespace(sid=0,auth_result={'job_id':'a','received_perf':9.})
    b=SimpleNamespace(sid=1,auth_result={'job_id':'b','received_perf':9.})
    obj.sessions={0:a,1:b};held=V6OwnerMixin._v6_held_results(obj)
    assert held==[(a,{'job_id':'a','received_perf':9.})] and a.auth_result is None and b.auth_result is not None
