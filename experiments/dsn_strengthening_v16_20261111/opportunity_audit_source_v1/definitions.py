"""Fixed v5 estimands on actual states; no alternative schedule or neural call."""
import hashlib,json

def sha_state(state):
    return hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def input_profile(job,canonical,witnesses,session_epoch,sticky_ancestor_fence=None):
    """Mirror actual FullSpec/DependencyVersioned reason priority, never AU.

    witnesses is an ACTUAL prefix, not later facts. sticky records the first
    ancestor-only disagreement while this actual job was tracked. Applying this
    predicate does not assert the job would exist in an alternate execution.
    """
    start=job['start'];start_f=start['frontier'];current=sha_state(start)==sha_state(canonical)
    semantic=None
    if job['dispatch_epoch']!=session_epoch:semantic='session_epoch_changed'
    elif not current:
        actual=witnesses.get(start_f)
        if actual is not None and sha_state(actual)!=sha_state(start):semantic='actual_canonical_disagrees_with_complete_start'
        elif job['end']<=canonical['frontier']:semantic='covered_by_actual_canonical'
    mismatches=[]
    for dep in job.get('frozen_dependencies',[]):
        actual=witnesses.get(dep['frontier'])
        if dep['frontier']<start_f and actual is not None and sha_state(dep)!=sha_state(actual):
            mismatches.append(dict(frontier=dep['frontier'],expected_sha=sha_state(dep),actual_sha=sha_state(actual)))
    fresh_fence=(mismatches[0] if mismatches and semantic is None else None)
    fence=sticky_ancestor_fence or fresh_fence
    full_keep=semantic is None
    dependency_keep=full_keep and fence is None
    state=('different_epoch' if semantic=='session_epoch_changed' else
           'complete_start_refuted' if semantic=='actual_canonical_disagrees_with_complete_start' else
           'covered' if semantic=='covered_by_actual_canonical' else
           'currently_confirmed' if current else 'future_complete_input_unresolved')
    return dict(input_status=state,fullcall_reason=semantic,fullcall_retains=full_keep,
                dependency_versioned_retains=dependency_keep,
                ancestor_refutations=mismatches,ancestor_fence=fence,
                treatment_disagreement=full_keep and not dependency_keep,
                direct_compatible_retained_by_both=current and full_keep and dependency_keep,
                pending_retained_by_both=state=='future_complete_input_unresolved' and full_keep and dependency_keep,
                shadow_only=True,does_not_grant_output_selection_authority=True)

def execution_state(record,terminal,instant,owner_ready=False):
    if owner_ready:return 'owner_admitted_complete_ready'
    r=record or {};t=terminal or {}
    begin=r.get('worker_job_begin_perf',t.get('worker_job_begin_perf'))
    end=r.get('worker_job_end_perf',t.get('worker_job_end_perf'))
    if begin is not None and instant<begin:return 'queued_before_worker_begin'
    model_begin,model_end=r.get('model_start'),r.get('model_end')
    if model_begin is not None and model_end is not None:
        if model_begin<=instant<model_end:
            return 'native_model_active' if r.get('native_model_evaluated') is True else 'infer_interval_without_native_model_evaluation'
        if instant<model_begin:return 'worker_pre_infer'
        if end is not None and instant<end:return 'worker_post_infer'
        return 'physical_full_complete_owner_unadmitted'
    if begin is not None and end is not None:
        return 'physical_terminal_owner_unadmitted' if instant>=end else 'worker_active_infer_timer_missing'
    return 'missing_execution_interval'

def ready_before(receipt_order,install_order,was_buffered):
    return bool(was_buffered and receipt_order is not None and
                receipt_order['sequence']<install_order['sequence'])

def loss_window(rows,index,source_id,old_frontier,new_frontier):
    """Actual deficit, truncated at the next canonical/support boundary."""
    start=rows[index]['observed'];end=start;censored=True;previous_time=start;previous_frontier=new_frontier;area=0.0
    for row in rows[index+1:]:
        if row['source_id']!=source_id:continue
        end=row['observed']
        if end<previous_time:raise ValueError('same-source loss-window clock decreases')
        area+=max(0,old_frontier-previous_frontier)/16000*(end-previous_time)
        if row['visible_frontier']>=old_frontier:censored=False;break
        if row['kind']=='canonical':break
        previous_time=end;previous_frontier=row['visible_frontier']
    deficit=max(0,old_frontier-new_frontier)/16000
    return dict(start=start,end=end,right_censored=censored,
                initial_lost_audio_seconds=deficit,area_audio_seconds_x_wall_seconds=area,
                integration='piecewise actual visible-frontier deficit; partial PRIVATE recovery included')

def final_outcome(job_id,selected,discarded,abandoned,lifecycle,owner_installed=(),consumer_applied=()):
    if job_id in selected:
        if job_id in owner_installed:return 'later_selected_original_full_result_owner_installed'
        if job_id in consumer_applied:return 'later_selected_durable_fact_consumer_applied'
        return 'later_durable_selected_application_unobserved'
    if job_id in discarded:return 'later_full_result_refused'
    if job_id in abandoned:return 'later_before_C_exit'
    if job_id in lifecycle:return 'later_lifecycle_termination'
    return 'pending_or_missing_terminal'
