"""CPU-only timer fixtures; never model or serving observations."""
import pytest
from candidate_wait_core import availability_bounds


def test_already_ready_candidate_is_not_artificially_charged():
    r = availability_bounds(audio_ready=2., parent_ready=1.5, candidate_gpu_done=.5,
        candidate_owner_received=.6, render_checked=.8, provisional_published=1., target_enqueued=3.)
    assert r['candidate_readiness_debt_upper_s'] == 0
    assert r['post_eligibility_candidate_enqueue_residual_lower_s'] == 1.


def test_slow_parent_masks_earlier_candidate_delay():
    r = availability_bounds(audio_ready=1., parent_ready=4., candidate_gpu_done=2.,
        candidate_owner_received=2.1, render_checked=2.2, provisional_published=2.3, target_enqueued=4.5)
    assert r['candidate_readiness_debt_upper_s'] == 0
    assert r['parent_readiness_after_audio_s'] == 3.


def test_only_a_bounded_nonexclusive_readiness_debt_is_reported():
    r = availability_bounds(audio_ready=1., parent_ready=1.5, candidate_gpu_done=2.,
        candidate_owner_received=2.1, render_checked=2.2, provisional_published=2.3, target_enqueued=3.)
    assert abs(r['candidate_readiness_debt_lower_s'] - .7) < 1e-9
    assert abs(r['candidate_readiness_debt_upper_s'] - .8) < 1e-9
    assert abs(r['post_eligibility_candidate_enqueue_residual_lower_s'] - .7) < 1e-9
    assert r['audio_ready_to_enqueue_s'] == 2.


def test_noncausal_observation_is_not_clipped_to_zero():
    with pytest.raises(AssertionError):
        availability_bounds(audio_ready=1., parent_ready=1., candidate_gpu_done=2.,
            candidate_owner_received=2.1, render_checked=2.2, provisional_published=3.5, target_enqueued=3.)
