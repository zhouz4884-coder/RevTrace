"""Action-level checks over the unchanged v3 finite executable specification.

This adds obligations; it does not change the model's transitions or claim
mechanical correspondence with the neural runtime. Durable and installed
positions deliberately differ in the successful-sync/pre-install crash gap.
"""
from collections import Counter, deque
from dataclasses import replace
import model as m


def check(s):
    m.check(s)
    m.need(len(s.jobs) == len(s.dispatch_evidence),
           'every_job_has_exactly_one_immutable_dispatch_evidence')
    lag = len(s.records) - s.canonical_index
    m.need(lag in (0, 1), 'serial_owner_can_lag_at_most_one_synced_fact')
    if s.owner_alive and not s.writes_blocked:
        if s.transaction is not None and s.transaction[1] == 'synced':
            m.need(lag == 1, 'successful_sync_has_one_pending_install')
            m.need(s.records[-1].job_id == s.transaction[0],
                   'pending_install_is_last_durable_fact')
        else:
            m.need(lag == 0, 'writable_idle_or_prepared_owner_matches_durable_tail')
    return True


def check_action(before, action, after):
    """Establish the prefix invariant from each enabled protocol action."""
    check(before); check(after)
    sync = action == 'sync_original_transition'
    if sync:
        m.need(after.records[:-1] == before.records
               and len(after.records) == len(before.records) + 1,
               'sync_extends_exactly_one_existing_durable_prefix')
        m.need(after.records[-1].start == before.canonical
               and before.canonical_index == len(before.records),
               'new_fact_binds_preceding_durable_cut_before_append')
        m.need(after.canonical == before.canonical
               and after.canonical_index == before.canonical_index,
               'sync_alone_does_not_install_owner_parent')
    else:
        m.need(after.records == before.records,
               'non_append_action_created_or_changed_selected_fact')
    m.need(after.accepted == before.accepted
           and after.original_clocks == before.original_clocks
           and after.clocks == before.clocks,
           'action_changed_surviving_accepted_input_or_original_clock')
    if action == 'install_durable_transition':
        m.need(before.transaction is not None
               and before.transaction[1] == 'synced'
               and after.canonical_index == before.canonical_index + 1
               and after.canonical == before.records[-1].end,
               'install_must_consume_exact_synced_pending_fact')
    elif action == 'recover_durable_facts_without_new_neural_work':
        m.need(after.canonical_index == len(before.records)
               and after.canonical == (before.records[-1].end if before.records else m.Cut(0, 0)),
               'recovery_restores_existing_durable_tail')
        m.need(tuple((j.job_id, j.choice, j.result) for j in after.jobs)
               == tuple((j.job_id, j.choice, j.result) for j in before.jobs),
               'recovery_created_new_neural_result')
        m.need(after.epoch == before.epoch + 1,
               'recovery_requires_new_owner_namespace')
    elif action != 'sync_original_transition':
        m.need(after.canonical_index == before.canonical_index
               and after.canonical == before.canonical,
               'non_install_or_recover_action_changed_installed_parent')
    return True


def explore_profile(*, frontiers=2, max_issued=3, max_depth=12,
                    max_faults=0, state_cap=150000):
    initial = replace(m.State(), accepted=frontiers,
                      original_clocks=tuple(range(frontiers + 1)),
                      clocks=tuple(range(frontiers + 1)))
    queue = deque([(initial, 0)]); seen = {initial}
    edges = 0; depth_cutoffs = 0; terminals = 0
    actions = Counter(); phases = Counter(); gap_examples = []
    while queue:
        s, depth = queue.popleft(); check(s)
        phase = ('crashed' if not s.owner_alive else
                 s.transaction[1] if s.transaction else 'idle')
        phases[phase] += 1
        if s.canonical_index < len(s.records) and len(gap_examples) < 3:
            gap_examples.append(dict(depth=depth,phase=phase,
                durable_facts=len(s.records),installed_index=s.canonical_index,
                owner_alive=s.owner_alive,
                durable_tail=vars(s.records[-1].end),installed_cut=vars(s.canonical)))
        if s.canonical.frontier == frontiers: terminals += 1
        if depth == max_depth:
            depth_cutoffs += 1; continue
        for action, out in m.successors(s, max_issued, max_faults):
            check_action(s, action, out); edges += 1
            actions[action.split(':')[0]] += 1
            if out not in seen:
                m.need(len(seen) < state_cap, 'declared_state_cap_reached')
                seen.add(out); queue.append((out, depth + 1))
    return dict(states=len(seen),edges=edges,depth_cutoffs=depth_cutoffs,
        terminal_states=terminals,max_depth=max_depth,frontiers=frontiers,
        max_issued=max_issued,max_faults=max_faults,
        checked_action_edges=dict(sorted(actions.items())),phase_state_counts=dict(phases),
        legal_durable_install_gap_examples=gap_examples,
        guarantee='additional state and action obligations over unchanged hand-written v3 finite specification; not runtime extraction or unbounded proof')
