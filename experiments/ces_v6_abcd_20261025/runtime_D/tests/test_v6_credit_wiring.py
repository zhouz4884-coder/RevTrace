from collections import deque
from types import SimpleNamespace
from revtrace.ces_v6_owner import V6OwnerMixin
from test_closed_loop_independent import target

def test_anchor_refreshes_actual_credit_before_calling_policy(monkeypatch):
    observed=[];calls=[]
    def choose(rows,**kw):
        observed.append(kw['observed_rate'])
        return {'operation':'generate','sids':[r.sid for r in rows],'chosen_index':0}
    monkeypatch.setattr('revtrace.ces_v6_owner.choose_anchor',choose)
    owner=SimpleNamespace(v6={'policy':'anchor_cost'},sessions={0:SimpleNamespace(state=SimpleNamespace(contract_epoch=1,checkpoint_id=2))},
        _v6_ages={},_v6_times=deque(),_v6_profile=None,contract_digest='fixed',cal={},t0=10.,clock=lambda:12.001,
        _closed_credit={},_closed_observed_credit=lambda:(calls.append('refresh') or 3.))
    result=V6OwnerMixin._v6_choose(owner,[target(sid=0)],12.,16)
    assert calls==['refresh'] and observed==[1.5]
    assert result['v6_observed_credit_rate']==1.5

def test_old_empty_book_expression_did_not_refresh_credit():
    # Explicit pre-fix witness: _closed_installed records commits elsewhere;
    # reading the initially empty credit dict does not derive qualifying audio.
    old={};assert sum(old.values())/2.==0.
