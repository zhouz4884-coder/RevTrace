"""Version 2 model-free raw-event checks for the frozen closed-loop owner.

The existing certificate/receipt/WAL/Consumer audit remains separate. These
checks rebuild observation identities and replay the CPU-only service book and
deterministic planning decision. They make no model, SSH or GPU call.
"""
from __future__ import annotations
from collections import defaultdict
from dataclasses import fields
import json
import math


CLOSED = {'service_cost', 'reserved_progress', 'inherit', 'causal'}


def same(a, b, label):
    # Runtime dictionaries can have integer Session keys; JSONL realizes them
    # as strings. Normalize key types before sorting (important for n>=10).
    normalize = lambda value: json.dumps(json.loads(json.dumps(value, allow_nan=False)),
                                         sort_keys=True, allow_nan=False)
    assert normalize(a) == normalize(b), label


def finite_tree(value):
    if isinstance(value, float):
        assert math.isfinite(value), 'nonfinite online observation'
    elif isinstance(value, dict):
        for key, child in value.items():
            assert not any(word in str(key).lower() for word in
                ('fault_label', 'injection_label', 'future_output', 'actual_future_parent')), 'unobservable scheduling feature'
            finite_tree(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            finite_tree(child)


def distribution(value):
    assert isinstance(value, (list, tuple)), 'Private CDF must be explicitly discrete'
    if not value:
        return ()
    pairs = tuple(tuple(pair) for pair in value)
    assert all(len(pair) == 2 and all(math.isfinite(x) for x in pair)
               and pair[0] >= 0 and pair[1] >= 0 for pair in pairs)
    assert abs(sum(w for w, _ in pairs)-1.) < 1e-9, 'Private CDF mass is not normalized'
    return pairs


def restore_context(value):
    from revtrace.ces_closed_loop import Identity, TargetContext, SuccessorObligation
    value = dict(value)
    assert set(value) == {f.name for f in fields(TargetContext)}, 'Unknown/omitted TargetContext feature'
    value['identity'] = Identity(**value['identity'])
    value['private_delay_distribution'] = distribution(value['private_delay_distribution'])
    children = []
    for child in value['successors']:
        child = dict(child)
        assert set(child) == {f.name for f in fields(SuccessorObligation)}, 'Unknown/omitted successor feature'
        child['private_delay_distribution'] = distribution(child['private_delay_distribution'])
        children.append(SuccessorObligation(**child))
    value['successors'] = tuple(children)
    return TargetContext(**value)


def assert_chain(path, byid, *, sid, now, initial_projection, target_end):
    """Check completed conditional chain against actual immutable old results."""
    assert isinstance(path, (list, tuple)) and path, 'Eligible chain has no actual path'
    first = byid[path[0]]
    assert first['job']['role'] == 'proposal' and first['job']['session_id'] == sid
    assert first['job']['audio_end_sample'] == target_end
    assert first['result']['received_perf'] <= now
    assert list(first['result']['state_tokens']) == list(initial_projection)
    cursor = first['job']['end_window']
    projection = first['result']['state_tokens']
    generation = first['job']['branch_generation']
    for jid in path[1:]:
        rec = byid[jid]
        j, r = rec['job'], rec['result']
        assert j['role'] == 'proposal' and j['session_id'] == sid
        assert j['branch_generation'] == generation and r['received_perf'] <= now
        assert j['chunk_id'] == cursor and list(j['prompt_tokens']) == list(projection)
        cursor, projection = j['end_window'], r['state_tokens']


def check_context_record(record, feature, *, cfg, now, t0, spec, actual_state,
                         byid, events_before, trusted_render, digest_tokens, contract_digest):
    from revtrace.ces_closed_loop import TargetContext
    assert 'target_context' in record, 'Current CDF/legality must be traceable, not implicit'
    c = restore_context(record['target_context'])
    sid = feature['sid']
    k = c.identity
    same(record['identity'], record['target_context']['identity'], 'Duplicate context identity disagrees')
    total = round(spec['duration']*16000)
    expected_end = min(feature['window']*32000, total)
    assert k.sid == sid and k.epoch == actual_state['contract_epoch']
    assert k.parent_version == actual_state['checkpoint_id']
    assert k.parent_digest == digest_tokens(actual_state['prompt_tokens'])
    assert k.frontier_start == actual_state['audio_frontier_window'] and k.frontier_end == expected_end
    assert k.contract_digest == contract_digest
    assert feature['ready'] == t0+spec['offset']+expected_end/16000
    assert feature['deadline'] == feature['ready']+cfg['ces_study']['commit_slo']
    assert feature['ready'] <= now and k.frontier_end > k.frontier_start
    private = record['private_path']
    if private['status'] == 'pending-actual-job':
        rec = byid[private['job_id']]
        j, r = rec['job'], rec['result']
        assert j['role'] == 'proposal' and j['session_id'] == sid
        assert j['enqueue_perf'] <= now < r['received_perf'], 'Private forecast used an already-received/future job'
        assert j['audio_end_sample'] >= k.frontier_end and j['audio_ready_perf'] <= now
        assert private['current_path_legal'] == c.private_path_currently_legal
        starts = [e for e in events_before if e['kind'] == 'worker-status'
                  and e.get('status') == 'batch-started' and j['job_id'] in e['job_ids']]
        if private.get('age_clock') == 'observed-worker-start':
            assert starts, 'Unobserved Worker start was used as future knowledge'
            started = starts[-1]['started_perf']
            assert j['enqueue_perf'] <= started <= now
            assert abs(private['actual_lease_age_s']-(now-started)) < 1e-9
        elif private.get('age_clock') == 'start-not-yet-observed-age-zero':
            assert not starts and private['actual_lease_age_s'] == 0.
        else:
            raise AssertionError('Private age must name an actually observed worker clock')
        assert private['predicted_full_lease_s'] > 0
        assert c.private_delay_distribution, 'Pending actual Private row requires an explicit row CDF'
        assert private['private_delay_includes_delivery'] and c.private_delay_includes_delivery
        assert private['CDF_upper_endpoint_bins'] == len(c.private_delay_distribution) <= 32
        assert 0 <= private['CDF_one_sided_error_bound'] <= 1
        if c.private_path_currently_legal:
            # The old birth Parent need not equal the new Canonical Parent for
            # a retained in-flight row. Reconstruct actual frozen state edges,
            # not a false birth-equality shortcut.
            cursor = feature['window']-1
            P = list(actual_state['prompt_tokens'])
            obsolete = {e['job_id'] for e in events_before if e['kind'] == 'proposal-obsolete'}
            candidates = [v for v in byid.values() if v['job']['role'] == 'proposal'
                and v['job']['session_id'] == sid and v['job'].get('branch_generation') == j.get('branch_generation')
                and v['job']['job_id'] not in obsolete and v['result']['received_perf'] <= now]
            by_window = {}
            for node in sorted(candidates, key=lambda v: v['result']['received_perf']):
                by_window[node['job']['end_window']] = node
            for window in sorted(by_window):
                if not cursor < window <= j['chunk_id']:
                    continue
                node = by_window[window]
                assert node['job']['chunk_id'] == cursor and list(node['job']['prompt_tokens']) == P
                cursor, P = window, list(node['result']['state_tokens'])
            assert j['chunk_id'] == cursor and list(j['prompt_tokens']) == P, 'Unbacked actual Private input chain'
            assert 0 <= j['audio_start_sample'] <= k.frontier_start
    else:
        assert not c.private_delay_distribution and not c.private_path_currently_legal
    preview = record['chain_preview']
    if preview['status'] == 'conditional-exact-chain-preview':
        origin = byid[preview['candidate_job_id']]
        oj, result = origin['job'], origin['result']
        assert oj['session_id'] == sid and oj['role'] == 'proposal'
        assert oj['audio_end_sample'] == expected_end and result['received_perf'] <= now
        shadow = {'prompt_tokens': list(actual_state['prompt_tokens']),
                  'chunk_id': feature['window']-1, 'language': spec['language']}
        P, _ = trusted_render(shadow, result['token_ids'])
        assert preview['verify_success_projection_digest'] == digest_tokens(P)
        assert preview['verify_success_chain_eligible'] == c.verify_private_compatible
        if preview['verify_success_chain_eligible']:
            assert_chain(preview['verify_success_chain_proof'], byid, sid=sid, now=now,
                initial_projection=P, target_end=expected_end)
        if preview['structural_chain_if_boundary_matches']:
            assert_chain(preview['structural_chain_proof'], byid, sid=sid, now=now,
                initial_projection=result['state_tokens'], target_end=expected_end)
        assert 'requires actual' in preview['condition'], 'Conditional preview presented as authorization'
    else:
        assert c.verify_private_compatible is None
    for mode, field in (('direct', 'direct_private_probability'), ('fallback', 'fallback_private_probability')):
        metadata = record[mode+'_root_model']
        probability = getattr(c, field)
        if probability is not None:
            assert math.isfinite(probability) and 0 <= probability <= 1
        if metadata.get('probability') is not None:
            assert metadata['probability'] == probability
        if metadata['status'] == 'unknown-sparse':
            assert probability is None
    cursor, previous_window = k.frontier_end, feature['window']
    assert len(c.successors) <= cfg['ces_study']['closed_loop_config']['max_successors_per_session']
    same(record['released_successors'], record['target_context']['successors'], 'Successor trace disagrees')
    for child in c.successors:
        assert child.window == previous_window+1
        assert child.parent_frontier_start == cursor
        assert child.frontier_end == min(child.window*32000, total)
        assert child.release == t0+spec['offset']+child.frontier_end/16000
        assert child.release <= now, 'Unreleased successor entered planning'
        assert child.display_deadline == child.release+cfg['ces_study']['display_slo']
        assert child.commit_deadline == child.release+cfg['ces_study']['commit_slo']
        assert abs(child.audio_weight-(child.frontier_end-cursor)/16000) < 1e-12
        assert child.remaining_service_s > 0 and math.isfinite(child.remaining_service_s)
        assert child.unknown_private_probability is None, 'Production collapsed Direct/Fallback into one rate'
        if child.window == feature['window']+1:
            assert child.inherit_current_transition_model is True, 'First successor uses the actual current transition model'
            assert child.direct_private_probability == c.direct_private_probability
            assert child.fallback_private_probability == c.fallback_private_probability
        else:
            assert child.inherit_current_transition_model is False, 'Later unknown Parent cannot inherit the current transition'
            assert child.direct_private_probability is None and child.fallback_private_probability is None
        assert child.private_delay_includes_delivery
        # It is a model obligation, not a frozen future execution job.
        assert not hasattr(child, 'token_ids') and not hasattr(child, 'job_id')
        assert not hasattr(child, 'certificate')
        cursor, previous_window = child.frontier_end, child.window
    finite_tree(record)
    return c


def audit_closed_events(cfg, events, records, sessions, initial_states, *, trusted_render,
                        digest_tokens, fingerprint):
    from revtrace.ces_closed_loop import ClosedLoopState, PlannerConfig, choose_closed_loop
    from revtrace.ces_v5_policy import V5Target
    method = cfg['ces_study']['method']
    if method not in CLOSED:
        assert not any(e['kind'] in ('closed-loop-observation', 'closed-loop-service-dispatch',
            'closed-loop-service-retired') for e in events), 'Baseline secretly used extra planner service state'
        return {'scope': 'nonclosed_reference', 'closed_observations': 0}
    t0 = next(e['t0_perf'] for e in events if e['kind'] == 'run-start')
    cd = fingerprint(cfg)
    book = ClosedLoopState(scope=(t0, cd))
    actual = {row['session_id']: dict(row['state']) for row in initial_states}
    specs = {s['session_id']: s for s in sessions}
    byid = {r['job']['job_id']: r for r in records}
    commits = {}
    observations = decisions = dispatches = retired_count = 0
    pending_observation = None
    pending_decision = None
    pending_service_dispatch = None
    acks = {}
    previous = []
    for e in events:
        kind = e['kind']
        if kind == 'ces-consumer-ack':
            spec = specs[e['session_id']]
            for window in range(1, math.ceil(spec['duration']/2)+1):
                frontier = min(window*32000, round(spec['duration']*16000))
                if frontier <= e['valid_visible_frontier']:
                    key = e['session_id'], window
                    acks[key] = min(acks.get(key, math.inf), e['observed_perf'])
        elif kind == 'commit':
            job = byid[e['job_id']]['job']
            state = actual[e['session_id']]
            assert job['parent'] == state['checkpoint_id']
            state.update(checkpoint_id=e['version'], audio_frontier_window=e['audio_end_sample'],
                         prompt_tokens=e['next_prompt_tokens'])
            commits[e['session_id'], job['end_window']] = e
        elif kind == 'closed-loop-service-retired':
            sid = e['session_id']
            candidates = [v for (s, _), v in commits.items() if s == sid and t0+v['installed'] == e['installed_perf']]
            assert len(candidates) == 1 and e['actual_durable_install_observed']
            assert candidates[0]['audio_end_sample'] == actual[sid]['audio_frontier_window']
            retired = book.admitted(sid, epoch=actual[sid]['contract_epoch'],
                frontier=actual[sid]['audio_frontier_window'], now=e['installed_perf'])
            same(retired, e['retired'], 'Service debt retired without the actual WAL transition')
            same(book.to_audit(), e['service_book'], 'Post-install service book differs')
            retired_count += 1
        elif kind == 'closed-loop-observation':
            assert pending_observation is None and pending_decision is None
            assert e['prediction_not_authorization'] is True
            now = e['observed_perf']
            contexts = {}
            # The next actual CES decision has the same immutable observation
            # time. Reading its *features* is not reading its future outcome.
            following = next(v for v in events[len(previous)+1:] if v['kind'] == 'ces-decision')
            assert following['observed_perf'] == now
            features = {t['sid']: t for t in following['features']}
            assert set(map(int, e['contexts'])) == set(features)
            for sid, feature in features.items():
                c = check_context_record(e['contexts'][str(sid)], feature, cfg=cfg, now=now,
                    t0=t0, spec=specs[sid], actual_state=actual[sid], byid=byid,
                    events_before=previous, trusted_render=trusted_render,
                    digest_tokens=digest_tokens, contract_digest=cd)
                contexts[sid] = c
                for child in c.successors:
                    met = acks.get((sid, child.window), math.inf) <= child.display_deadline
                    assert child.display_met == met, 'Successor display credit is not backed by an actual ACK'
            book.observe(contexts, now)
            same(book.to_audit(), e['service_book'], 'Observation lost/created service debt')
            observed_credit = 0.
            for (sid, window), commit in commits.items():
                release = t0+commit['audio_ready']
                if acks.get((sid, window), math.inf) <= release+cfg['ces_study']['display_slo'] and t0+commit['installed'] <= release+cfg['ces_study']['commit_slo']:
                    observed_credit += (commit['audio_end_sample']-commit['audio_start_sample'])/16000
            assert abs(observed_credit-e['observed_credit_audio']) < 1e-9
            assert e['elapsed_seconds'] == now-t0
            pending_observation = (e, contexts)
            observations += 1
        elif kind == 'ces-decision':
            assert pending_observation is not None and pending_decision is None
            observation, contexts = pending_observation
            same(e['observed_perf'], observation['observed_perf'], 'Decision not bound to its observed clock')
            targets = [V5Target(**v) for v in e['features']]
            replay = choose_closed_loop(targets, contexts, now=e['observed_perf'], mode=method,
                cal=cfg['ces_study']['calibration'], limit=cfg['microbatch'],
                observed_credit_audio=observation['observed_credit_audio'],
                elapsed_seconds=observation['elapsed_seconds'], state=book,
                display_slo=cfg['ces_study']['display_slo'],
                config=PlannerConfig(**cfg['ces_study']['closed_loop_config']))
            for key, value in replay.items():
                same(value, e[key], 'Deterministic frozen planner replay differs: '+key)
            assert sorted(s for b in e['plan'] for s in b['sids']) == sorted(e['common_cut_sids'])
            assert len(e['common_cut_sids']) == len(set(e['common_cut_sids']))
            assert e['prediction_only_not_authorization'] and e['wait_seconds'] == 0
            pending_decision = (e, contexts)
            pending_observation = None
            decisions += 1
        elif kind == 'closed-loop-service-dispatch':
            assert pending_decision is not None and pending_service_dispatch is None
            decision, contexts = pending_decision
            assert e['decision_token'] == decision['decision_token']
            assert e['actual_dispatch_perf'] >= decision['observed_perf']
            receipt = book.record_dispatch(decision, contexts, now=e['actual_dispatch_perf'])
            for key, value in receipt.items():
                same(value, e[key], 'Service book changed without one real dispatch: '+key)
            pending_service_dispatch = (decision, contexts)
            dispatches += 1
        elif kind == 'batch-dispatched' and e['role'] == 'authority':
            assert pending_service_dispatch is not None and pending_decision is not None
            decision, contexts = pending_service_dispatch
            jobs = [byid[j]['job'] for j in e['job_ids']]
            assert {j['session_id'] for j in jobs} == set(decision['sids'])
            assert all(j['ces_operation'] == decision['operation'] for j in jobs)
            for j in jobs:
                k = contexts[j['session_id']].identity
                assert j['parent'] == k.parent_version and j['contract_epoch'] == k.epoch
                assert j['parent_prompt_digest'] == k.parent_digest
                assert j['contract_digest'] == k.contract_digest
                assert j['audio_start_sample'] == k.frontier_start and j['audio_end_sample'] == k.frontier_end
                assert j['enqueue_perf'] >= decision['observed_perf']
                assert j['audio_ready_perf'] <= j['enqueue_perf']
            pending_service_dispatch = pending_decision = None
        previous.append(e)
    assert pending_observation is None and pending_decision is None and pending_service_dispatch is None
    assert observations == decisions == dispatches
    assert retired_count == len(commits)
    assert book.dispatches == dispatches
    return {'scope': 'actual_observation_identity_and_CPU_service_planner_replay',
        'closed_observations': observations, 'physical_service_dispatches': dispatches,
        'actual_commit_retirements': retired_count, 'residual_service_records': len(book.records),
        'future_execution_permissions_created': 0,
        'unknown_Parent_predictions_not_installed': True,
        'TOKEN_LIMIT_BOUNDARY_is_not_admission_failure': True}


