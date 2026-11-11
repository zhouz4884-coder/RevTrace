"""Safe no-early-cancellation control; input/selection/support guards stay live.

UIR retains computation, not authority. Calling inherited invalidations still
classifies complete inputs. Only forwarding cooperative C-entry skip hints is
disabled. A full returned result must pass unchanged actual-parent AU, durable
installation and independent whole-view SUP before it can affect selected state.
"""
from resilience_policy import ResilientFullSpecCoordinator
from versioned_policy import is_policy_fence


class UnconditionalInflightCoordinator(ResilientFullSpecCoordinator):
    policy_name = "unconditional_inflight_retention_with_original_use_guards"
    early_cancellation_enabled = False

    def history_stats(self):
        return dict(super().history_stats(),policy_name=self.policy_name,
                    early_cancellation_enabled=False,
                    original_input_selection_and_support_guards_enabled=True)


def process_c_entry_hints(policy,workers,observed_reasons,log):
    """Apply one shared hint path; UIR changes forwarding, never classification.

    observed_reasons is a bounded job-ID set pruned by Owner against live jobs.
    It records both sent and deliberately suppressed hints, without claiming
    that suppressed work was semantically eligible or selected.
    """
    for job_id,proof in policy.invalidations().items():
        if job_id in observed_reasons:
            continue
        job=policy.jobs[job_id]
        enabled=getattr(policy,'early_cancellation_enabled',True)
        if enabled:
            workers[job['worker']]['hints'].send(dict(job_id=job_id,
                source_id=job['source_id'],dispatch_epoch=job['dispatch_epoch'],proof=proof))
        observed_reasons.add(job_id)
        kind=('policy_C_entry_skip_hint' if is_policy_fence(proof) else 'known_invalid_C_skip_hint') if enabled else 'input_or_coverage_reason_observed_without_C_entry_skip'
        log(kind,job_id=job_id,proof=proof,c_entry_skip_hint_sent=enabled,
            reason_class='retention_policy' if is_policy_fence(proof) else 'actual_input_or_coverage',
            complete_input_refuted=proof['kind']=='actual_canonical_disagrees_with_complete_start')
