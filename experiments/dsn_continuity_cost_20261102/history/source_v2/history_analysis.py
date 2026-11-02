"""H1 original-Consumer-clock registered-view opportunity analysis (CPU only).

This holds the original producer/dispatch/model history fixed.  It is not an
online scheduler counterfactual and does not measure deployed service gains.
Only original Consumer applications register candidate publications.  Future,
unpublished, retired, or ambiguous evidence never becomes an authorized tip.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict, deque
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

from reference_view import EnvelopeView, digest_tokens, text_sha
from reference_kernel import State, step


class AuditFailure(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise AuditFailure(message)


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_rows(path):
    """Keep incomplete-tail censoring explicit; corrupt complete rows fail."""
    data = Path(path).read_bytes()
    out, incomplete = [], 0
    lines = data.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except (ValueError, UnicodeDecodeError):
            require(index == len(lines) - 1 and not line.endswith(b'\n'),
                    f'corrupt complete JSONL frame: {path}:{index + 1}')
            incomplete = len(line)
    return out, incomplete


def event_key(event):
    return (event['kind'], event.get('session_id'),
            event.get('displayed', event.get('time')))


def row_key(row):
    return (row['source_kind'], row['session_id'], row['server_time'])


def native_compatible(state, tip, fine):
    """Independent transcription of published whole-path eligibility."""
    root = state.get('Psha')
    if not root:
        return False
    node, seen = tip, set()
    while node['job_id'] not in seen:
        seen.add(node['job_id'])
        start, inp = node.get('chunk_id'), node.get('input_projection_sha256')
        if start is None or inp is None:
            return False
        if start == round(state['F'] / fine) and inp == root:
            return True
        parents = [other for other in state['nodes'].values()
                   if other.get('end_window') == start
                   and other.get('output_projection_sha256') == inp
                   and state['F'] <= other['audio_end_sample'] < node['audio_end_sample']
                   and other.get('branch_generation') == node.get('branch_generation')]
        if len(parents) != 1:
            return False
        node = parents[0]
        if node['audio_end_sample'] == state['F']:
            return node.get('output_projection_sha256') == root
    return False


def native_support_keys(state, tip, fine):
    """Ordinary reverse-query keys, used only as an equality control."""
    node, seen, keys = tip, set(), set()
    while node['job_id'] not in seen:
        seen.add(node['job_id'])
        start, inp = node.get('chunk_id'), node.get('input_projection_sha256')
        if start is None or inp is None:
            break
        keys.add((start * fine, inp))
        keys.add((node['audio_end_sample'], node.get('output_projection_sha256')))
        parents = [other for other in state['nodes'].values()
                   if other.get('end_window') == start
                   and other.get('output_projection_sha256') == inp
                   and other['audio_end_sample'] < node['audio_end_sample']
                   and other.get('branch_generation') == node.get('branch_generation')]
        if len(parents) != 1:
            break
        node = parents[0]
    return keys


def core_compatible(root_frontier, root_projection, tip_job, jobs):
    """Unchanged generic core relation: all matching actual parents count.

    jobs contains only already host-received complete rows at the evaluated
    original cut.  It is a proof universe, never a source of candidate tips.
    """
    node = jobs.get(tip_job)
    if not node or not node.get('result'):
        return False
    sid, seen = node['sid'], set()
    while not ((node['rootF'] == root_frontier and node['inputP'] == root_projection)
               or (node['end'] == root_frontier and node['result']['P'] == root_projection)):
        if node['id'] in seen:
            return False
        seen.add(node['id'])
        parents = [other for other in jobs.values()
                   if other['sid'] == sid and other['role'] == 'proposal' and other.get('result')
                   and other['end'] == node['rootF']
                   and other['result']['P'] == node['inputP']
                   and other['end'] < node['end']]
        if len(parents) != 1:
            return False
        node = parents[0]
    return True


def rank(tip):
    return (tip['audio_end_sample'], tip.get('display_revision', 0), tip['job_id'])


def allowed_tip(tip, state, contract, mode, floor, revoked, generation_floor):
    return (mode not in ('CERTIFIED-ONLY', 'RECOVERY')
            and tip['audio_end_sample'] > state['F']
            and tip.get('contract_epoch') == state.get('epoch')
            and tip.get('contract_digest') == contract
            and tip.get('display_revision', 0) > floor
            and tip['job_id'] not in revoked
            and tip.get('branch_generation', 0) >= generation_floor)


def select_views(state, contract, mode, floor, revoked, generation_floor, fine, jobs):
    eligible = [tip for tip in state['nodes'].values()
                if allowed_tip(tip, state, contract, mode, floor, revoked, generation_floor)]
    native = [tip for tip in eligible if native_compatible(state, tip, fine)]
    joint = [tip for tip in native
             if core_compatible(state['F'], state.get('Psha'), tip['job_id'], jobs)]
    indexed = defaultdict(list)
    for tip in eligible:
        for key in native_support_keys(state, tip, fine):
            indexed[key].append(tip)
    indexed_joint = [tip for tip in indexed.get((state['F'], state.get('Psha')), [])
                     if native_compatible(state, tip, fine)
                     and core_compatible(state['F'], state.get('Psha'), tip['job_id'], jobs)]
    native_winner = max(native, key=rank, default=None)
    joint_winner = max(joint, key=rank, default=None)
    indexed_winner = max(indexed_joint, key=rank, default=None)
    require((joint_winner or {}).get('job_id') == (indexed_winner or {}).get('job_id'),
            'ordinary index and full joint scan disagree')
    best_f = joint_winner['audio_end_sample'] if joint_winner else state['F']
    tied = [tip for tip in joint if tip['audio_end_sample'] == best_f]
    return native_winner, joint_winner, dict(
        eligible=len(eligible), native_legal=len(native), joint_legal=len(joint),
        best_frontier_ties=len(tied), best_frontier_distinct_texts=len({tip['text'] for tip in tied}))


def core_apply_check(actual, state, tip, jobs, owner, contract):
    """Execute the verbatim original core, not a caller-supplied legal flag."""
    sid, version = actual['session_id'], actual['canonical_version']
    fact = dict(v=version, F=actual['certified_frontier'], P=state.get('Psha'),
                textsha=actual.get('certified_text_sha256'), Z=actual.get('certified_Z_sha256'),
                txn=actual.get('certified_transaction'))
    kernel = State(contract, actual['canonical_epoch'], owner)
    kernel.C = {sid: fact}
    kernel.D = {sid: {version: fact} if version else {}}
    kernel.V = {sid: dict(v=0, F=0, visible=0, revision=0)}
    kernel.J = jobs
    kernel.publications = {(sid, 1): dict(_sid=sid, canonical=True, fact=fact)}
    view = dict(v=version, F=fact['F'], P=fact['P'], visible=tip['audio_end_sample'],
                private=tip['job_id'], text=tip['text'], revision=1)
    next_state, effects = step(kernel, 'apply-request', dict(
        sid=sid, view=view, key=(sid, 1), operation='h1-conditional-apply'))
    require(effects == ['apply-view'], 'core did not approve positive candidate')
    step(next_state, 'view-applied', dict(operation='h1-conditional-apply'))


def interval_union_length(intervals):
    if not intervals:
        return 0
    length = 0
    left, right = sorted(intervals)[0]
    for start, end in sorted(intervals)[1:]:
        if start <= right:
            right = max(right, end)
        else:
            length += right - left
            left, right = start, end
    return length + right - left


def edit_erasure(before, after):
    common = 0
    for a, b in zip(before, after):
        if a != b:
            break
        common += 1
    return len(before) - common


def normalize_worker(row, fine):
    job, result = row['job'], row['result']
    if job.get('role') != 'proposal' or 'received_perf' not in result:
        return None
    return dict(id=job['job_id'], sid=job['session_id'], role='proposal',
                rootF=job['chunk_id'] * fine, end=job['audio_end_sample'],
                inputP=digest_tokens(job['prompt_tokens']), received=float(result['received_perf']),
                generation=job.get('branch_generation', 0), epoch=job.get('contract_epoch'),
                result=dict(P=digest_tokens(result['state_tokens']),
                            Z=digest_tokens(result['token_ids']), textsha=text_sha(result['text'])))


def generation_at(retirements, cut):
    return max([0] + [generation for when, generation in retirements if when <= cut])


def merge_positive_segments(segments):
    """Merge repeated cut observations without duplicating time/audio credit."""
    out = []
    by_session = defaultdict(list)
    for segment in segments:
        by_session[segment['session_id']].append(segment)
    for sid, rows in by_session.items():
        rows.sort(key=lambda r: (r['start_perf'], r['end_perf']))
        for row in rows:
            keys = ('selected_job', 'actual_frontier', 'selected_frontier', 'category', 'canonical_version')
            if out and out[-1]['session_id'] == sid and out[-1]['end_perf'] == row['start_perf'] and all(
                    out[-1][key] == row[key] for key in keys):
                out[-1]['end_perf'] = row['end_perf']
                out[-1]['duration_seconds'] += row['duration_seconds']
                out[-1]['area_audio_seconds_x_wall_seconds'] += row['area_audio_seconds_x_wall_seconds']
                out[-1]['original_consumer_cut_count'] += row['original_consumer_cut_count']
                out[-1]['right_censored'] = row['right_censored']
            else:
                out.append(dict(row))
    return out


def analyze_attempt(entry, raw_paths, config):
    cfg = read_json(raw_paths['config.json'])
    sessions = read_json(raw_paths['sessions.json'])
    events, event_tail = read_rows(raw_paths['events.jsonl'])
    consumer_name = 'consumer.jsonl' if 'consumer.jsonl' in raw_paths else 'consumer-live.jsonl'
    actual, consumer_tail = read_rows(raw_paths[consumer_name])
    workers, worker_tail = read_rows(raw_paths['worker_records.jsonl'])
    rate = int(cfg.get('sample_rate', 16000))
    fine = round(cfg.get('fine_seconds', 2) * rate)
    starts = [event for event in events if event['kind'] == 'run-start']
    require(len(starts) == 1, 'attempt must have exactly one recorded owner stream')
    owner = float(starts[0]['t0_perf'])
    require(all(float(actual[i]['observed_perf']) <= float(actual[i + 1]['observed_perf'])
                for i in range(len(actual) - 1)), 'original Consumer FIFO clock regressed')
    require(all('observed_perf' in row and 'consumer_received_perf' in row for row in actual),
            'missing original application/receive timestamps')
    require(all(math.isfinite(float(row['observed_perf'])) and math.isfinite(float(row['consumer_received_perf']))
                for row in actual), 'nonfinite original Consumer timestamps')
    lookup = defaultdict(deque)
    next_session_cut = {}
    for index, row in enumerate(actual):
        lookup[row_key(row)].append((index, row))
    for index in range(len(actual) - 1, -1, -1):
        sid = actual[index]['session_id']
        actual[index]['_next_session_cut'] = next_session_cut.get(sid)
        next_session_cut[sid] = index
    if not actual:
        return dict(status='CENSORED_EMPTY_ACTUAL_CONSUMER', attempt=entry['attempt'],
                    original_rows=0, original_tail_bytes=dict(events=event_tail, consumer=consumer_tail, worker=worker_tail)), [], []
    global_end = float(actual[-1]['observed_perf'])
    worker_by_id = {row['job']['job_id']: row for row in workers}
    require(len(worker_by_id) == len(workers), 'duplicate worker row identities require separate adjudication')
    normalized = [normalized for row in workers if (normalized := normalize_worker(row, fine))]
    normalized.sort(key=lambda row: (row['received'], row['id']))
    job_receipts = defaultdict(list)
    for job in normalized:
        job_receipts[job['sid']].append(job)
    retirements = defaultdict(list)
    for event in events:
        if event['kind'] == 'private-generation-retired':
            require('generation' in event, 'retirement requires actual incremented generation field')
            retirements[event['session_id']].append((owner + event['time'], event['generation']))
    policy = entry.get('reference_policy', 'two_lane')
    view = EnvelopeView(policy=policy, fine_samples=fine, strict_bound=True)
    floor, revoked = defaultdict(int), defaultdict(set)
    seen_actual_nodes = defaultdict(set)
    actual_ever_frontier = defaultdict(int)
    checked, counts = 0, Counter()
    segments, cuts = [], []
    previous_selected_text = defaultdict(str)
    aggregate = Counter()
    audio_intervals = defaultdict(list)
    observation_states = defaultdict(list)
    for event in events:
        if checked == len(actual):
            break  # unobserved Owner tail never registers a publication
        key = event_key(event)
        matched = lookup.get(key)
        observed = float(matched[0][1]['observed_perf']) if matched else None
        row = view.consume(event, observed)
        if row is None:
            continue
        require(bool(matched), f'native replay generated unobserved application: {key}')
        index, original = matched.popleft()
        require(index == checked, f'original FIFO sequence differs from Owner event replay: {index}/{checked}')
        for name in ['canonical_version', 'certified_frontier', 'valid_visible_frontier', 'visible_text']:
            require(row[name] == original[name], f'native replay mismatch {name} at Consumer row {index}')
        for name in ['contract_digest', 'owner_incarnation', 'canonical_epoch', 'certified_P_sha256',
                     'certified_Z_sha256', 'certified_text_sha256', 'certified_transaction', 'envelope_mode']:
            if name in original:
                require(name in row and row[name] == original[name],
                        f'native replay identity/mode mismatch {name} at Consumer row {index}')
                counts['baseline_field_checked_' + name] += 1
            else:
                counts['baseline_field_absent_' + name] += 1
        checked += 1
        sid = original['session_id']
        # The reference baseline must remain byte-semantically faithful to the
        # original Consumer. A genesis query needs an empty projection, but the
        # original uncommitted view intentionally records Psha=None. Never write
        # query conveniences into the mutable reference replay state.
        state = dict(view.states[sid])
        if not state['version']:
            state['Psha'] = digest_tokens(())
        if event['kind'] == 'view-mode':
            revoked[sid].update(event.get('revoked_job_ids', []))
            if event['mode'] in ('CERTIFIED-ONLY', 'RECOVERY'):
                floor[sid] = max(floor[sid], event['display_revision'])
        mode = view.modes.get(sid, 'NORMAL')
        current_tip = state.get('tentative')
        if current_tip and original['valid_visible_frontier'] > original['certified_frontier']:
            seen_actual_nodes[sid].add(current_tip['job_id'])
        actual_ever_frontier[sid] = max(actual_ever_frontier[sid], original['valid_visible_frontier'])
        # Existing publications alone register candidates; actual Worker rows
        # bind immutable P/Z/text and host receipt, never bypass publication.
        for tip in state['nodes'].values():
            worker = worker_by_id.get(tip['job_id'])
            require(worker is not None, f'published job absent from actual Worker records: {tip["job_id"]}')
            job, result = worker['job'], worker['result']
            require(result['received_perf'] <= original['consumer_received_perf'], 'candidate before host receipt')
            require(tip['input_projection_sha256'] == digest_tokens(job['prompt_tokens'])
                    and tip['output_projection_sha256'] == digest_tokens(result['state_tokens'])
                    and tip['text'] == result['text']
                    and tip.get('text_sha256') == text_sha(result['text']), 'publication changed immutable result binding')
        end_index = original['_next_session_cut']
        end = float(actual[end_index]['observed_perf']) if end_index is not None else global_end
        start = float(original['observed_perf'])
        # Explicit Owner retirement can invalidate a tip before its queued mode
        # withdrawal is applied; split there instead of crediting stale time.
        boundaries = sorted({start, end} | {when for when, _ in retirements[sid] if start < when < end}
                            | {job['received'] for job in job_receipts[sid] if start < job['received'] < end})
        # Point-cut reproduction remains separate from duration.  The old
        # historical scanner used Consumer-applied mode/revision fences; the
        # strengthened owner-generation fence below may only remove tips.
        if event['kind'] == 'canonical-display' and state['version'] and mode not in ('CERTIFIED-ONLY', 'RECOVERY'):
            legacy = [tip for tip in state['nodes'].values()
                      if allowed_tip(tip, state, view.contract, mode, floor[sid], revoked[sid], 0)
                      and native_compatible(state, tip, fine)]
            old_best = max(legacy, key=rank, default=None)
            if old_best and old_best['audio_end_sample'] > original['valid_visible_frontier']:
                counts['legacy_registered_canonical_point_opportunities'] += 1
        # Every actual application gets a point snapshot, even when its next
        # row has the same timestamp or it is the final global EOS application.
        # The support universe is conservative at actual APPLY, not RECEIVE:
        # receipt->apply arrivals must not evade the all-parent ambiguity check.
        point_jobs = {job['id']: job for job in job_receipts[sid] if job['received'] <= start}
        _, point_selected, point_detail = select_views(state, view.contract, mode, floor[sid], revoked[sid],
            generation_at(retirements[sid], start), fine, point_jobs)
        point_f = point_selected['audio_end_sample'] if point_selected else state['F']
        point_baseline_joint_legal = (original['valid_visible_frontier'] == state['F'] or bool(
            current_tip and allowed_tip(current_tip, state, view.contract, mode, floor[sid], revoked[sid], generation_at(retirements[sid], start))
            and core_compatible(state['F'], state.get('Psha'), current_tip['job_id'], point_jobs)))
        observation_states[sid].append(dict(time=start, actual=original['valid_visible_frontier'],
            selected=point_f, certified=state['F'], baseline_joint_legal=point_baseline_joint_legal))
        point_text = point_selected['text'] if point_selected else state['text']
        aggregate['selected_erased_characters_at_original_apply_cuts'] += edit_erasure(previous_selected_text[sid], point_text)
        previous_selected_text[sid] = point_text
        counts['equal_frontier_multiple_text_apply_cuts'] += point_detail['best_frontier_distinct_texts'] > 1
        if len(boundaries) == 1:
            counts['zero_following_observation_duration_applications'] += 1
        primary_cut_recorded = False
        for start_piece, end_piece in zip(boundaries, boundaries[1:]):
            if end_piece <= start_piece:
                continue
            # New complete host rows can remove ambiguous support, never enter
            # the already-registered tip universe. Every piece uses <= APPLY.
            proof_cut = start_piece
            jobs = {job['id']: job for job in job_receipts[sid] if job['received'] <= proof_cut}
            generation_floor = generation_at(retirements[sid], start_piece)
            native, selected, detail = select_views(state, view.contract, mode, floor[sid], revoked[sid],
                                                   generation_floor, fine, jobs)
            for tip in state['nodes'].values():
                require(native_compatible(state, tip, fine) == view._compatible(state, tip, state.get('Psha')),
                        'independent native compatibility differs from frozen reference')
            baseline_joint_legal = (original['valid_visible_frontier'] == state['F'] or bool(
                current_tip and allowed_tip(current_tip, state, view.contract, mode, floor[sid], revoked[sid], generation_floor)
                and core_compatible(state['F'], state.get('Psha'), current_tip['job_id'], jobs)))
            selected_f = selected['audio_end_sample'] if selected else state['F']
            native_f = native['audio_end_sample'] if native else state['F']
            original_f = original['valid_visible_frontier']
            duration = end_piece - start_piece
            aggregate['native_gap_area_audio_seconds_x_wall_seconds'] += max(0, native_f - original_f) / rate * duration
            if not baseline_joint_legal:
                aggregate['baseline_native_only_seconds'] += duration
            counts['evaluated_clock_segments'] += 1
            counts['equal_frontier_multiple_text_segments'] += detail['best_frontier_distinct_texts'] > 1
            if not selected or selected_f <= original_f or not baseline_joint_legal:
                continue
            core_apply_check(original, state, selected, jobs, owner, view.contract)
            if selected['job_id'] in seen_actual_nodes[sid]:
                category = 'restore_originally_visible_same_node'
            elif actual_ever_frontier[sid] >= selected_f:
                category = 'new_legal_node_for_previously_visible_audio'
            else:
                category = 'registered_old_publication_newly_visible_audio'
            area = (selected_f - original_f) / rate * duration
            segment = dict(session_id=sid, source_id=worker_by_id[selected['job_id']]['job']['source_id'],
                original_consumer_row=index, trigger=event['kind'], start_perf=start_piece, end_perf=end_piece,
                duration_seconds=duration, actual_frontier=original_f, selected_frontier=selected_f,
                canonical_frontier=state['F'], canonical_version=state['version'], selected_job=selected['job_id'],
                selected_publication_revision=selected.get('display_revision'), category=category,
                area_audio_seconds_x_wall_seconds=area, extra_audio_seconds=(selected_f-original_f)/rate,
                original_consumer_cut_count=1 if start_piece == start else 0,
                right_censored=end_index is None and end_piece == global_end,
                global_prefix_extension_after_session_last_apply=end_index is None,
                original_apply_perf=start, host_received=worker_by_id[selected['job_id']]['result']['received_perf'],
                generic_core_apply_pass=True, selection_detail=detail)
            segments.append(segment)
            audio_intervals[sid].append((original_f, selected_f))
            aggregate['joint_gap_area_audio_seconds_x_wall_seconds'] += area
            aggregate['joint_gap_session_wall_seconds'] += duration
            if end_index is None:
                aggregate['joint_gap_area_global_prefix_extension'] += area
                aggregate['joint_gap_wall_global_prefix_extension'] += duration
            else:
                aggregate['joint_gap_area_within_session_observation'] += area
                aggregate['joint_gap_wall_within_session_observation'] += duration
            counts['positive_clock_segments'] += 1
            counts['positive_core_apply_checks'] += 1
            counts['category_' + category] += 1
            if start_piece == start and not primary_cut_recorded:
                cuts.append(dict(segment))
                counts['positive_consumer_cuts'] += 1
                counts['trigger_' + event['kind']] += 1
                counts['positive_canonical_cuts'] += event['kind'] == 'canonical-display'
                primary_cut_recorded = True
    require(checked == len(actual), f'unreplayed original Consumer rows: {checked}/{len(actual)}')
    require(not any(queue for queue in lookup.values()), 'unmatched original Consumer applications')
    merged = merge_positive_segments(segments)
    summary = dict(status='PASS_ORIGINAL_CONSUMER_CLOCK_OFFLINE_OPPORTUNITY', attempt=entry['attempt'],
        bank=entry['bank'], stage=entry['stage'], controlled=entry.get('controlled'), cell=entry.get('cell'),
        actual_execution_commit=cfg.get('authority_runtime', {}).get('code_commit', cfg.get('code_commit')),
        original_consumer_rows=len(actual), original_clock_start=float(actual[0]['observed_perf']),
        original_clock_end=global_end, original_canonical_updates=sum(r['source_kind']=='canonical-display' and r['canonical_version']>0 for r in actual),
        sample_rate=rate, fine_samples=fine, counts=dict(counts), metrics=dict(aggregate),
        distinct_deficient_audio_seconds=sum(interval_union_length(value)/rate for value in audio_intervals.values()),
        gap_segments=len(merged), right_censored_gap_segments=sum(r['right_censored'] for r in merged),
        original_tail_bytes=dict(events=event_tail, consumer=consumer_tail, worker=worker_tail),
        first_deadline_analysis=deadline_metrics(sessions, cfg, owner, fine, rate, observation_states),
        text_metric_scope='Fixed original apply-cut selection sequence only; intermediate eligibility-piece text switches are not simulated displays',
        support_time_scope='All complete host rows received <= original actual apply/piece time, conservatively including receive-to-apply arrivals',
        scope='Fixed original producer history; zero-extra-application-delay offline opportunity, not deployed gain',
        no_new_model_calls=True, no_new_FIFO_replay_clock=True)
    return summary, merged, cuts


def deadline_metrics(sessions, cfg, owner, fine, rate, observations):
    if isinstance(sessions, dict):
        sessions = sessions.get('sessions', list(sessions.values()))
    origin = float(cfg.get('episode_origin_perf', owner))
    results = Counter()
    for session in sessions:
        sid = session['session_id']
        total = round(session['duration'] * rate)
        rows = observations.get(sid, [])
        for begin in range(0, total, fine):
            end = min(total, begin + fine)
            weight = (end - begin) / rate
            eos = end - begin < fine
            ready = origin + session['offset'] + end / rate
            d = next((r['time'] for r in rows if r['actual'] >= end), math.inf)
            c = next((r['time'] for r in rows if r['certified'] >= end), math.inf)
            s = next((r['time'] for r in rows if r['baseline_joint_legal'] and r['selected'] >= end), math.inf)
            results['offered_audio_seconds'] += weight
            results['offered_intervals'] += 1
            results['partial_EOS_intervals'] += eos
            if d <= ready + 2 and c <= ready + 8:
                results['actual_joint_D2_C8_audio_seconds'] += weight
            if s <= ready + 2 and c <= ready + 8:
                results['registered_zero_apply_delay_joint_D2_C8_audio_seconds'] += weight
            if d > ready + 2 and s <= ready + 2 and c <= ready + 8:
                results['new_first_D2_C8_audio_seconds'] += weight
                results['new_first_D2_C8_partial_EOS_audio_seconds'] += weight if eos else 0
    return dict(results)


def resolve_paths(entry, remap=None):
    paths = {}
    for item in entry.get('trace_identity', []):
        path = item['path']
        if remap:
            old, new = remap
            require(path.startswith(old), 'raw remap does not cover frozen path')
            path = new + path[len(old):]
        paths[Path(item['path']).name] = Path(path)
    return paths


def verify_inputs(entry, paths):
    verified = []
    for item in entry.get('trace_identity', []):
        path = paths[Path(item['path']).name]
        require(path.is_file(), f'original frozen raw file missing: {path}')
        require(path.stat().st_size == item['bytes'], f'raw bytes mismatch: {path}')
        digest = file_sha(path)
        require(digest == item['sha256'], f'raw SHA mismatch: {path}')
        verified.append(dict(path=str(path), bytes=item['bytes'], sha256=digest))
    return verified


def verify_execution_source(manifest_path, requested_commit):
    manifest = read_json(manifest_path)
    source = Path(__file__).resolve().parent
    actual_commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    require(actual_commit == requested_commit == manifest.get('code_commit', manifest.get('source_commit')),
            'actual source HEAD, argv commit, and full source manifest disagree')
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all'], text=True)
    require(not dirty.strip(), 'execution source checkout is not clean')
    expected = {row['path']: row for row in manifest['files']}
    tracked = subprocess.check_output(['git', '-C', str(source), 'ls-files'], text=True).splitlines()
    require(set(tracked) == set(expected), 'complete tracked source manifest file set mismatch')
    for name in tracked:
        path = source / name
        require(path.is_file() and not path.is_symlink(), f'invalid source path: {name}')
        row = expected[name]
        require(path.stat().st_size == row['bytes'] and file_sha(path) == row['sha256'], f'source bytes/hash mismatch: {name}')
    return dict(code_commit=actual_commit, source_manifest=str(manifest_path),
                source_manifest_sha256=file_sha(manifest_path), source_files=len(expected))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--selection', choices=['positive3', 'all'], default='all')
    parser.add_argument('--remap', nargs=2)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    args = parser.parse_args()
    source_identity = verify_execution_source(args.source_manifest, args.source_commit)
    require(not args.output.exists(), 'refusing to overwrite any existing experiment output')
    args.output.mkdir(parents=True)
    manifest, config = read_json(args.manifest), read_json(args.config)
    entries = manifest['attempts']
    if args.selection == 'positive3':
        entries = [row for row in entries if row['bank']=='n5' and row['original_point_opportunities'] > 0]
        require(len(entries) == 3, 'frozen historical positive3 denominator changed')
    environment = dict(python=sys.version, executable=sys.executable, platform=platform.platform())
    environment_path = args.output/'ENVIRONMENT.json'
    environment_path.write_text(json.dumps(environment, indent=2)+'\n')
    record = dict(experiment_id=config['experiment_id'], selection=args.selection, **source_identity,
        source_commit=args.source_commit, config_sha256=file_sha(args.config), manifest_sha256=file_sha(args.manifest),
        environment_path=str(environment_path), environment_sha256=file_sha(environment_path),
        intended_raw_root=manifest['raw_root'], raw_result_location=str(args.output),
        intended_summary=str(args.output/'SUMMARY.json'), intended_gate=str(args.output/'GATE.json'), model_calls=0)
    (args.output/'RUN_RECORD.json').write_text(json.dumps(record, indent=2)+'\n')
    summaries, failures = [], []
    for number, entry in enumerate(entries):
        tag = f'{entry["bank"]}-{entry["ordinal"]:03d}'
        out = args.output/tag
        out.mkdir()
        began = time.process_time()
        try:
            paths = resolve_paths(entry, args.remap)
            before = verify_inputs(entry, paths)
            needed = {'events.jsonl','worker_records.jsonl','config.json','sessions.json'}
            consumer_available = 'consumer.jsonl' in paths or 'consumer-live.jsonl' in paths
            if not needed <= set(paths) or not consumer_available:
                summary = dict(status='CENSORED_FROZEN_INPUT_SET_INCOMPLETE', attempt=entry['attempt'],
                               bank=entry['bank'], original_status=entry['original_status'],
                               absent_roles=sorted(needed-set(paths)), consumer_role_present=consumer_available)
                segments, cuts = [], []
            else:
                summary, segments, cuts = analyze_attempt(entry, paths, config)
            after = verify_inputs(entry, paths)
            require(before == after, 'original raw inputs changed during CPU analysis')
            summary.update(analysis_CPU_seconds=time.process_time()-began, input_identity_before_after_equal=True,
                           source_commit=args.source_commit)
            (out/'SUMMARY.json').write_text(json.dumps(summary, indent=2)+'\n')
            (out/'INPUTS.json').write_text(json.dumps(before, indent=2)+'\n')
            (out/'GAPS.json').write_text(json.dumps(segments, indent=2)+'\n')
            (out/'CUTS.json').write_text(json.dumps(cuts, indent=2)+'\n')
            summaries.append(summary)
        except Exception as exc:
            failure = dict(status='FAIL_PRESERVED_ORIGINAL_ATTEMPT', bank=entry['bank'], attempt=entry['attempt'],
                           error=repr(exc), traceback=traceback.format_exc())
            (out/'STOP.json').write_text(json.dumps(failure, indent=2)+'\n')
            failures.append(failure)
        progress = dict(completed_attempts=number+1, planned_attempts=len(entries), passing_or_censored=len(summaries), failures=len(failures))
        (args.output/'PROGRESS.json').write_text(json.dumps(progress, indent=2)+'\n')
        print(json.dumps(dict(tag=tag, **progress)), flush=True)
    status_counts = dict(Counter(row['status'] for row in summaries))
    final = dict(status='COMPLETE' if not failures else 'COMPLETE_WITH_PRESERVED_FAILURES',
        experiment_id=config['experiment_id'], selection=args.selection, planned_attempts=len(entries),
        completed_attempts=len(summaries)+len(failures), status_counts=status_counts,
        failed_attempts=len(failures), source_commit=args.source_commit, model_calls=0,
        input_manifest_sha256=file_sha(args.manifest), config_sha256=file_sha(args.config),
        decision='READ_ALL_RECORDED_GAPS_AND_BOUNDARIES' if not failures else 'NO_CLAIM_PENDING_FAIL_TRIAGE',
        runs=summaries, failures=failures)
    (args.output/'SUMMARY.json').write_text(json.dumps(final, indent=2)+'\n')
    (args.output/'GATE.json').write_text(json.dumps(dict(
        status='PASS_COMPLETENESS_AND_RECORDED_INPUT_GATES' if not failures else 'FAIL_RETAIN_ALL_ATTEMPTS_FOR_TRIAGE',
        scientific_decision='PENDING_INDEPENDENT_RECOUNT_AND_ALL_SCOPE_INTERPRETATION',
        experiment_id=config['experiment_id'], code_commit=args.source_commit,
        config_sha256=file_sha(args.config), environment_sha256=file_sha(environment_path),
        summary_sha256=file_sha(args.output/'SUMMARY.json'), planned_attempts=len(entries),
        completed_attempts=len(summaries)+len(failures), failures=len(failures)), indent=2)+'\n')
    print(json.dumps({key:value for key,value in final.items() if key not in ['runs','failures']}), flush=True)
    return 0 if not failures else 2


if __name__ == '__main__':
    raise SystemExit(main())
