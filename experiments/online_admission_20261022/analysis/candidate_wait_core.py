"""Timing bounds, not a claim of uniquely identified causal wait fractions."""


def availability_bounds(*, audio_ready, parent_ready, candidate_gpu_done,
                        candidate_owner_received, render_checked,
                        provisional_published, target_enqueued):
    assert candidate_gpu_done <= candidate_owner_received <= render_checked <= provisional_published <= target_enqueued
    eligible = max(audio_ready, parent_ready)
    assert eligible <= target_enqueued
    # Dict insertion happens after render-checked and before provisional publish
    # in the frozen successful proposal path. Both events precede attachment.
    return {'without_candidate_eligible_perf': eligible,
            'candidate_available_lower_perf': render_checked,
            'candidate_available_upper_perf': provisional_published,
            'candidate_readiness_debt_lower_s': max(0., render_checked - eligible),
            'candidate_readiness_debt_upper_s': max(0., provisional_published - eligible),
            'post_eligibility_candidate_enqueue_residual_lower_s': target_enqueued - max(eligible, provisional_published),
            'post_eligibility_candidate_enqueue_residual_upper_s': target_enqueued - max(eligible, render_checked),
            'parent_readiness_after_audio_s': max(0., parent_ready - audio_ready),
            'audio_ready_to_enqueue_s': target_enqueued - audio_ready}
