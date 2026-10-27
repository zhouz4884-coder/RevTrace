"""CPU estimator controls; fixtures are not measured GPU latency samples."""
import pytest
from revtrace.dispatch_wait import DispatchWaitController


def controller(mode='conditional'):
    return DispatchWaitController(dict(policy='pending_eta',eta_mode=mode,eta_min_tail_samples=2,
        authority_cost_default_seconds=1.7,install_cost_default_seconds=.3))


def seed(c):
    c.history['authority',4].extend([.5,1.,1.5,2.,2.5,3.])
    c.install_history[4].extend([.05,.1,.15])


def test_conditional_residual_uses_only_surviving_past_samples_and_adds_install():
    c=controller();seed(c)
    p=c._remaining_authority(4,2.1)
    assert p['receipt_conditional_survivors']==2
    assert p['remaining_receipt_estimate_seconds']==pytest.approx(.85)
    assert p['remaining_installation_estimate_seconds']==pytest.approx(.14)
    assert p['remaining_estimate_seconds']==pytest.approx(.99)
    assert p['legacy_receipt_only_remaining_seconds']==pytest.approx(.65)
    assert p['eta_supported'] and not p['eta_unsupported_tail']


def test_past_maximum_exceeded_never_becomes_zero_timeout_estimate():
    c=controller();seed(c)
    p=c._remaining_authority(4,4.)
    assert p['receipt_conditional_survivors']==0 and p['eta_unsupported_tail']
    assert p['legacy_receipt_only_remaining_seconds']==.005
    assert p['remaining_estimate_seconds']==pytest.approx(2.89)
    p2=c._remaining_authority(4,100000.)
    assert p2['remaining_estimate_seconds']==p['remaining_estimate_seconds']


def test_single_survivor_is_declared_unsupported_and_uses_full_cost_fallback():
    c=controller();seed(c)
    p=c._remaining_authority(4,2.9)
    assert p['receipt_conditional_survivors']==1 and p['eta_unsupported_tail']
    assert p['remaining_receipt_estimate_seconds']==pytest.approx(2.75)


def test_empty_history_does_not_fabricate_distribution_from_default_scalar():
    c=controller();p=c._remaining_authority(16,10.)
    assert p['receipt_duration_observations']==0 and p['installation_duration_observations']==0
    assert p['eta_unsupported_tail'] and not p['eta_supported']
    assert p['remaining_estimate_seconds']==pytest.approx(2.)
    assert not c.history and not c.install_history


def test_role_pool_support_is_not_labelled_exact_batch_support():
    c=controller();c.history['authority',-1].extend([1.,2.,3.,4.]);c.install_history[-1].extend([.1,.2,.3])
    p=c._remaining_authority(16,1.)
    assert not p['receipt_exact_batch_size'] and not p['installation_exact_batch_size']
    assert p['receipt_conditional_survivors']==3 and p['eta_supported']


def test_already_received_row_pays_only_conditional_install_remainder():
    c=controller();c.install_history[4].extend([.1,.2,.3,.4])
    p=c._remaining_authority(4,100.,already_received=True,receipt_age=.15)
    assert p['remaining_receipt_estimate_seconds']==0.
    assert p['remaining_installation_estimate_seconds']==pytest.approx(.23)
    assert p['remaining_estimate_seconds']==pytest.approx(.23)
    assert p['legacy_receipt_only_remaining_seconds']==.005
    assert p['eta_supported']


def test_installation_history_is_updated_only_after_actual_commit_event():
    c=controller()
    for i in range(3):
        jid='a'+str(i)
        c.observe_event(dict(kind='batch-dispatched',job_ids=[jid]))
        c.observe_event(dict(kind='executor-complete',role='authority',job_id=jid,enqueue=i*3.,received=i*3.+1.))
        assert len(c.install_history.get(1,[]))==i
        c.observe_event(dict(kind='commit',job_id=jid,installed=i*3.+1.2))
        c.observe_event(dict(kind='commit',job_id=jid,installed=i*3.+1.2))
    assert len(c.install_history[1])==3 and list(c.install_history[1])==pytest.approx([.2]*3)


def test_missing_receipt_is_unknown_not_zero_install_sample():
    c=controller();c.observe_event(dict(kind='commit',job_id='missing',installed=10.))
    assert not c.install_history


def test_same_observations_log_both_estimators_with_frozen_mode_switch():
    old=controller('legacy');new=controller('conditional');seed(old);seed(new)
    a=old._remaining_authority(4,2.1);b=new._remaining_authority(4,2.1)
    assert a['remaining_estimate_seconds']==a['legacy_receipt_only_remaining_seconds']
    assert b['remaining_estimate_seconds']==b['conditional_remaining_including_install_seconds']
    for key in ['legacy_receipt_only_remaining_seconds','conditional_remaining_including_install_seconds',
                'receipt_conditional_survivors','installation_duration_observations']:
        assert a[key]==b[key]


@pytest.mark.parametrize('policy',['immediate','fixed','pending_eta','backpressure','recent_gain','state_aware'])
def test_every_policy_gets_same_estimator_information(policy):
    c=DispatchWaitController(dict(policy=policy,eta_min_tail_samples=2));seed(c)
    p=c._remaining_authority(4,2.1)
    assert p['conditional_remaining_including_install_seconds']==pytest.approx(.99)
