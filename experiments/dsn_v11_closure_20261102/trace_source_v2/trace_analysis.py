"""Observed event paths; no inferred stage time, counterfactual speed or repair."""
from __future__ import annotations
from collections import Counter
import math
from trace_common import need, close, digest, NN4F, TraceError

STATE_FIELDS = ('audio_segments', 'tokens', 'context', 'last_attend_frame',
                'detected_language', 'initial_tokens', 'initial_token_length',
                'sot_index', 'decoder_type', 'contract', 'frontier', 'transcript')


def cut(value):
    need(isinstance(value, dict) and set(value) == set(STATE_FIELDS), 'incomplete/extra full-state field')
    need(type(value['frontier']) is int and value['frontier'] >= 0, 'invalid full-state frontier')
    return digest(value)


def same(a, b):
    return cut(a) == cut(b)


def stamp(value, label):
    if value is None:
        return None
    need(type(value) in (int, float) and math.isfinite(value), 'invalid timestamp: ' + label)
    return float(value)


def delta(end, begin):
    return None if end is None or begin is None else end - begin


def quantile(values, q):
    values = sorted(math.inf if value is None else value for value in values)
    need(bool(values), 'empty endpoint distribution')
    position = (len(values) - 1) * q
    i = int(position)
    j = min(i + 1, len(values) - 1)
    return None if math.isinf(values[j]) else values[i] + (values[j] - values[i]) * (position - i)


def validate_scope(cells, archive):
    need(len(cells) == 32 and len({row['cell_id'] for row in cells}) == 32,
         'complete fixed 32-cell scope required')
    sources = {row['source_id'] for row in cells}
    need(len(sources) == 8, 'eight independent source IDs required')
    speakers = {}
    for row in cells:
        sid = row['source_id']
        need(row['policy'] in ('conservative', 'fullcall') and row['repeat'] in (0, 1),
             'policy/repeat outside frozen matrix')
        need(sid not in speakers or speakers[sid] == row['speaker_id'], 'speaker identity changed')
        speakers[sid] = row['speaker_id']
    need(len(set(speakers.values())) == 8, 'speakers are not disjoint')
    actual = {(row['source_id'], row['policy'], row['repeat']) for row in cells}
    need(actual == {(sid, policy, repeat) for sid in sources
                    for policy in ('conservative', 'fullcall') for repeat in (0, 1)},
         'source/policy/repeat scope differs')
    need(archive['status'] == 'COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS'
         and archive['completed_trials'] == 32 and archive['independent_speakers'] == 8,
         'original completed archive scope differs')
    rows = archive['cells']
    need(len(rows) == 32 and {row['cell_id'] for row in rows} == {row['cell_id'] for row in cells},
         'archive cell identities differ')
    return {row['cell_id']: row for row in rows}


def endpoints(rows, source, origin):
    sid = source['source_id']
    need(type(source['frames']) is int and source['frames'] > 0, 'bad source frames')
    origin = stamp(origin, 'origin')
    need(origin is not None, 'missing original origin')
    own = [(index, row) for index, row in enumerate(rows) if row['source_id'] == sid]
    need(own, 'source has no actual Consumer rows')
    times = [stamp(row['observed'], 'Consumer observed') for _, row in own]
    need(all(value is not None for value in times)
         and all(b >= a for a, b in zip(times, times[1:])), 'actual Consumer order differs')
    result = []
    previous = 0
    for frontier in list(range(8000, source['frames'], 8000)) + [source['frames']]:
        offer = origin + frontier / 16000
        d = next(((i, r) for i, r in own if r['observed'] >= offer
                  and r['visible_frontier'] >= frontier), None)
        c = next(((i, r) for i, r in own if r['observed'] >= offer
                  and r['certified_frontier'] >= frontier), None)
        D = d[1]['observed'] - offer if d else None
        C = c[1]['observed'] - offer if c else None
        result.append(dict(source_id=sid, frontier=frontier, is_EOS=frontier == source['frames'],
                           offer=offer, audio_seconds=(frontier - previous) / 16000,
                           D=D, C=C, D2=D is not None and D <= 2., C8=C is not None and C <= 8.,
                           first_D_row_index=d[0] if d else None, first_C_row_index=c[0] if c else None,
                           first_D_actual_G=d[1]['visible_frontier'] if d else None))
        previous = frontier
    D99 = quantile([row['D'] for row in result], .99)
    C99 = quantile([row['C'] for row in result], .99)
    no_missing = all(row['D'] is not None and row['C'] is not None for row in result)
    primary = dict(offered_frontiers=len(result), offered_audio_seconds=sum(r['audio_seconds'] for r in result),
                   dual_deadline_audio_credit_seconds=sum(r['audio_seconds'] for r in result if r['D2'] and r['C8']),
                   primary_linear_all_offered_D99=D99, primary_linear_all_offered_C99=C99,
                   original_quantile_test_pass=D99 is not None and C99 is not None and D99 <= 2. and C99 <= 8.,
                   complete_coverage_and_original_quantile_pass=no_missing and D99 is not None
                   and C99 is not None and D99 <= 2. and C99 <= 8.,
                   D2_misses_all_offered=sum(not r['D2'] for r in result),
                   C8_misses_all_offered=sum(not r['C8'] for r in result),
                   EOS_D2_misses=sum(r['is_EOS'] and not r['D2'] for r in result),
                   missing_D_frontiers=sum(r['D'] is None for r in result),
                   missing_C_frontiers=sum(r['C'] is None for r in result))
    close(primary['offered_audio_seconds'], source['frames'] / 16000, 'all-offered/EOS denominator')
    close(primary['dual_deadline_audio_credit_seconds']
          + sum(r['audio_seconds'] for r in result if not (r['D2'] and r['C8'])),
          primary['offered_audio_seconds'], 'credit plus missed-audio conservation')
    return primary, result


def compare_endpoints(primary, frontiers, original, archive):
    for label, expected in (('original NN', original), ('archived a13', archive)):
        for key, value in primary.items():
            if key in expected:
                close(value, expected[key], label + ' primary.' + key)
        for key in ('offered_frontiers', 'offered_audio_seconds', 'dual_deadline_audio_credit_seconds',
                    'primary_linear_all_offered_D99', 'primary_linear_all_offered_C99',
                    'complete_coverage_and_original_quantile_pass'):
            need(key in expected, label + ' required primary field absent: ' + key)
    frozen = archive['frontiers']
    need(len(frozen) == len(frontiers), 'archive frontier count differs')
    for current, prior in zip(frontiers, frozen):
        for key in ('source_id', 'frontier', 'is_EOS', 'offer', 'audio_seconds', 'D', 'C', 'D2', 'C8'):
            close(current[key], prior[key], 'archive per-frontier.' + key)


def key(epoch, job_id):
    need(type(epoch) is int and isinstance(job_id, str) and job_id, 'missing owned job identity')
    return epoch, job_id


def unique_add(mapping, identity, value, label):
    need(identity not in mapping, 'duplicate ' + label)
    mapping[identity] = value


def build_context(data):
    config = data['config']
    source = config['settings']['sources'][0]
    need(len(config['settings']['sources']) == 1 and config['settings']['source_commit'] == NN4F,
         'expected one-source actual4f trial')
    need(config.get('fault', {}).get('kind') == 'none', 'normal32 trace scope only')
    jobs = {}
    for row in data['dispatch']:
        job = row['job']
        identity = key(row['owner_epoch'], job['job_id'])
        need(job['source_id'] == source['source_id'] and job['kind'] == 'full', 'dispatch source/kind differs')
        cut(job['start'])
        need(job['end'] == min(source['frames'], job['start']['frontier'] + 8000), 'dispatch cadence differs')
        need(type(job['started_on_canonical']) is bool, 'canonical-start status absent')
        unique_add(jobs, identity, dict(dispatch=row, asr=None, terminal=None, fact=None,
                                       sync=None, install=None, promotions=[], policy_outcomes=[]), 'dispatch UID')
    for row in data['results']:
        event = row['event']
        if event['kind'] not in ('asr_early', 'completed', 'abandoned'):
            continue
        identity = key(row['owner_epoch'], event['job_id'])
        need(identity in jobs, 'worker event lacks original dispatch')
        entry = jobs[identity]
        job = entry['dispatch']['job']
        need(event['source_id'] == job['source_id'] and event['worker'] == job['worker']
             and event['worker_incarnation'] == job['worker_incarnation']
             and event['dispatch_epoch'] == job['dispatch_epoch'], 'worker event identity differs')
        if event['kind'] == 'asr_early':
            need(entry['asr'] is None, 'duplicate ASR event in normal trace')
            need(same(event['start_state'], job['start']) and event['start_state_sha'] == cut(job['start'])
                 and event['end_frontier'] == job['end'], 'ASR full input differs')
            need(cut(event['projection']['end']) == event['projection']['end_state_sha']
                 and event['projection']['end']['frontier'] == job['end'], 'ASR projection binding differs')
            entry['asr'] = event
        else:
            need(entry['terminal'] is None, 'duplicate terminal event in normal trace')
            need(same(event['start'], job['start']), 'terminal frozen input differs')
            if event['kind'] == 'completed':
                need(event['end']['frontier'] == job['end']
                     and event['record']['start_state'] == cut(job['start'])
                     and event['record']['end_state'] == cut(event['end']), 'full result state differs')
            else:
                need(event['target_end'] == job['end'], 'abandon target differs')
            entry['terminal'] = event
    frames = data['frames']
    need(frames and frames[0][0]['kind'] == 'genesis', 'original durable genesis missing')
    genesis = frames[0][0]['body']
    need(genesis['metadata']['config_sha256'] == digest(config), 'genesis original config binding differs')
    sid = source['source_id']
    initial = genesis['initials'][sid]
    cut(initial)
    selected = {(sid, initial['frontier']): dict(state=initial, fact=None)}
    facts = {}
    transitions = {}
    state_facts = {cut(initial): None}
    prior = initial
    for obj, receipt in frames[1:]:
        need(obj['kind'] == 'canonical', 'unexpected durable frame kind')
        body = obj['body']
        need(body['source_id'] == sid and same(body['parent_state'], prior), 'durable actual parent chain differs')
        need(body['parent_state_sha256'] == cut(prior)
             and body['next_state_sha256'] == cut(body['next_state']), 'durable full-state digest differs')
        identity = key(body['owner_epoch'], body['job']['job_id'])
        need(identity in jobs and jobs[identity]['fact'] is None, 'durable UID missing/duplicated')
        entry = jobs[identity]
        job = entry['dispatch']['job']
        need(same(body['job']['start'], job['start']) and same(job['start'], prior)
             and body['job']['end'] == job['end'],
             'durable full input changed')
        terminal = entry['terminal']
        need(terminal is not None and terminal['kind'] == 'completed'
             and same(terminal['end'], body['next_state']) and digest(terminal['record']) == digest(body['record']),
             'durable result not bound to original complete receipt')
        fact = dict(body=body, receipt=receipt, identity=identity)
        unique_add(facts, receipt['sequence'], fact, 'durable sequence')
        unique_add(transitions, body['transition_id'], fact, 'durable transition')
        unique_add(selected, (sid, body['next_state']['frontier']),
                   dict(state=body['next_state'], fact=fact), 'selected frontier')
        unique_add(state_facts, cut(body['next_state']), fact, 'selected state digest')
        entry['fact'] = fact
        prior = body['next_state']
    for row in data['events']:
        if row['kind'] not in ('durable_sync', 'canonical_install'):
            continue
        identity = key(row['owner_epoch'], row['job_id'])
        need(identity in jobs and jobs[identity]['fact'] is not None, 'Owner event lacks durable UID')
        entry = jobs[identity]
        fact = entry['fact']
        need(row['receipt']['sequence'] == fact['receipt']['sequence']
             and row['receipt']['record_sha256'] == fact['receipt']['record_sha256'], 'Owner receipt identity differs')
        name = 'sync' if row['kind'] == 'durable_sync' else 'install'
        need(entry[name] is None, 'duplicate Owner ' + name)
        if name == 'install':
            need(row['parent_state_sha'] == cut(fact['body']['parent_state'])
                 and row['next_state_sha'] == cut(fact['body']['next_state']), 'Owner install cut differs')
        entry[name] = row
    for row in data['audit']:
        kind = row['kind']
        if kind not in ('promotion', 'abandoned_full', 'discarded_full'):
            continue
        body = row['body']
        jid = body['job_id'] if kind == 'promotion' else body['job']['job_id']
        identity = key(row['owner_epoch'], jid)
        need(identity in jobs, 'policy outcome lacks dispatch UID')
        entry = jobs[identity]
        if kind == 'promotion':
            need(same(body['owned_job']['start'], entry['dispatch']['job']['start'])
                 and same(body['owned_job']['start'], body['actual_parent_state']), 'promotion full parent mismatch')
            entry['promotions'].append(row)
        else:
            entry['policy_outcomes'].append(row)
    pubs = {}
    for row in data['publications']:
        event = row['event']
        identity = row['bound_owner_epoch'], event['publication_id']
        unique_add(pubs, identity, row, 'publication identity')
    return dict(source=source, jobs=jobs, selected=selected, facts=facts,
                transitions=transitions, state_facts=state_facts, publications=pubs)


def canonical_binding(row, pub, context):
    candidates = []
    if row.get('journal_sequence') is not None:
        need(row['journal_sequence'] in context['facts'], 'Consumer journal sequence absent')
        candidates.append(context['facts'][row['journal_sequence']])
    if row.get('transition_id') is not None:
        need(row['transition_id'] in context['transitions'], 'Consumer transition absent')
        candidates.append(context['transitions'][row['transition_id']])
    if pub is not None and pub['event']['kind'] == 'canonical':
        sequence = pub['event']['durable_receipt']['sequence']
        need(sequence in context['facts'], 'canonical publication receipt absent')
        candidates.append(context['facts'][sequence])
    if not candidates and pub is not None and pub['event']['kind'] == 'private':
        need(pub['event']['canonical_sha'] == row['canonical_sha'], 'private fallback canonical binding differs')
        need(row['canonical_sha'] in context['state_facts'], 'private fallback lacks durable root')
        fact = context['state_facts'][row['canonical_sha']]
        if fact is not None:
            candidates.append(fact)
    if not candidates and row['visible_frontier'] == 0:
        return None
    need(candidates, 'no durable canonical fallback witness')
    fact = candidates[0]
    need(all(other['identity'] == fact['identity'] for other in candidates), 'canonical witnesses disagree')
    need(cut(fact['body']['next_state']) == row['canonical_sha'], 'Consumer canonical digest differs')
    end = fact['body']['next_state']
    need(row['text'] == end['transcript']
         and row['visible_frontier'] == (end['frontier'] if row['text'] else 0),
         'canonical first-view text/frontier differs from its durable fact')
    return fact


def view_bindings(rows, context, cell_id='<synthetic>'):
    result = []
    held = {}
    for row_index, row in enumerate(rows):
        location = ('cell=' + cell_id + ' consumer_row_index0=' + str(row_index)
                    + ' publication_id=' + str(row.get('publication_id'))
                    + ' private_job=' + str(row.get('private_job')) + ': ')

        def require(ok, message):
            need(ok, location + message)

        pub = None
        if row.get('publication_id') is not None:
            pkey = row['owner_epoch'], row['publication_id']
            require(pkey in context['publications'], 'actual Consumer publication absent')
            pub = context['publications'][pkey]
            require(pub['event']['source_id'] == row['source_id'], 'Consumer/publication source differs')
        private = row.get('private_job')
        if private:
            identity = key(row['owner_epoch'], private)
            require(identity in context['jobs'], 'actual private view lacks dispatch')
            signature = identity, row['visible_frontier'], row['text']
            direct = None
            if pub is not None and pub['event']['kind'] == 'private' and pub['event']['steps']:
                tip = pub['event']['steps'][-1]
                # SurvivorConsumer.snapshot preserves the actual tip/job but
                # exposes zero audio coverage while its whole text is empty.
                # The frozen job target and complete end-state binding remain
                # the internal frontier; zero is never substituted for either.
                visible = tip['end']['frontier'] if tip['end']['transcript'] else 0
                if (tip['job_id'] == private and visible == row['visible_frontier']
                        and tip['end']['transcript'] == row['text']):
                    entry = context['jobs'][identity]
                    job = entry['dispatch']['job']
                    require(same(tip['start'], job['start']) and tip['end']['frontier'] == job['end'],
                            'actual private publication frozen job differs')
                    ends = []
                    if entry['asr'] is not None:
                        ends.append(entry['asr']['projection']['end'])
                    if entry['terminal'] is not None and entry['terminal']['kind'] == 'completed':
                        ends.append(entry['terminal']['end'])
                    require(ends and any(same(tip['end'], end) for end in ends),
                            'actual private publication end lacks original full-state receipt')
                    direct = dict(kind='actual_private_job', identity=identity, view_publication=pub,
                                  view_publication_id=pub['event']['publication_id'],
                                  view_publication_owner_epoch=pub['bound_owner_epoch'],
                                  view_tip_internal_frontier=tip['end']['frontier'],
                                  view_tip_full_state_sha256=cut(tip['end']))
            if direct is None:
                previous = held.get(row['source_id'])
                require(previous is not None and previous[0] == signature,
                        'retained actual view lacks prior applied publication')
                direct = dict(previous[1])
                direct['kind'] = 'retained_actual_private_job'
            held[row['source_id']] = signature, direct
            binding = direct
        else:
            try:
                fact = canonical_binding(row, pub, context)
            except TraceError as error:
                raise TraceError(location + str(error)) from error
            binding = dict(kind='canonical_fact_fallback' if fact is not None else 'genesis_without_audio',
                           identity=fact['identity'] if fact is not None else None,
                           view_publication=pub, view_publication_id=row.get('publication_id'),
                           view_publication_owner_epoch=row['owner_epoch'],
                           view_tip_internal_frontier=fact['body']['next_state']['frontier'] if fact is not None else None,
                           view_tip_full_state_sha256=cut(fact['body']['next_state']) if fact is not None else None)
            held.pop(row['source_id'], None)
        result.append(dict(binding, actual_publication=pub))
    return result


def job_timelines(data, context):
    rows = []
    for identity, entry in sorted(context['jobs'].items()):
        job = entry['dispatch']['job']
        terminal, asr = entry['terminal'], entry['asr']
        completed = terminal if terminal is not None and terminal['kind'] == 'completed' else None
        record = completed['record'] if completed is not None else terminal or {}
        selected = context['selected'].get((job['source_id'], job['start']['frontier']))
        actual_parent = selected['state'] if selected is not None else None
        parent_fact = selected['fact'] if selected is not None else None
        parent_entry = context['jobs'][parent_fact['identity']] if parent_fact is not None else None
        parent_install = (stamp(parent_entry['install'].get('observed'), 'parent install')
                          if parent_entry is not None and parent_entry['install'] is not None else None)
        dispatch = stamp(job.get('dispatched_perf'), 'dispatch')
        sync = entry['sync']
        install = entry['install']
        fact = entry['fact']
        own_projection = asr['projection']['end'] if asr is not None else None
        selected_end = context['selected'].get((job['source_id'], job['end']))
        selected_end = selected_end['state'] if selected_end is not None else None
        actual_parent_equal = None if actual_parent is None else same(job['start'], actual_parent)
        if job['started_on_canonical']:
            need(actual_parent_equal is True, 'canonical-start input differs from actual selected parent')
        start_gap = delta(dispatch, parent_install) if job['started_on_canonical'] else None
        start_gap_status = ('NOT_CANONICAL_START' if not job['started_on_canonical'] else
                            'GENESIS_INSTALL_NOT_TIMESTAMPED' if job['start']['frontier'] == 0 else
                            'MISSING_INSTALL_OR_DISPATCH_TIME' if start_gap is None else
                            'NEGATIVE_RECORDED_INTERVAL' if start_gap < 0 else 'RECORDED_INTERVAL')
        first_private = next((r['observed'] for r in data['consumer']
                              if r.get('private_job') == identity[1] and r['owner_epoch'] == identity[0]), None)
        first_certified = next((r['observed'] for r in data['consumer'] if fact is not None
                                and r.get('journal_sequence') == fact['receipt']['sequence']), None)
        output = dict(owner_epoch=identity[0], job_id=identity[1], source_id=job['source_id'],
                      worker=job['worker'], worker_incarnation=job['worker_incarnation'],
                      start_frontier=job['start']['frontier'], target_frontier=job['end'],
                      is_EOS=job['end'] == context['source']['frames'],
                      started_on_canonical=job['started_on_canonical'], input_state_sha256=cut(job['start']),
                      actual_parent_state_sha256=cut(actual_parent) if actual_parent is not None else None,
                      actual_parent_full_state_equal=actual_parent_equal,
                      terminal_kind=terminal['kind'] if terminal is not None else None,
                      execution_evidence='terminal_receipt' if terminal is not None else
                      'ASR_receipt_only' if asr is not None else 'dispatch_only_not_proven_executed',
                      dispatched_perf=dispatch,
                      worker_job_begin_perf=stamp(record.get('worker_job_begin_perf'), 'worker begin'),
                      model_start_perf=stamp(record.get('model_start'), 'model start'),
                      ASR_produced_perf=stamp(asr.get('produced_perf'), 'ASR produced') if asr is not None else None,
                      ASR_sent_perf=stamp(asr.get('sent_perf'), 'ASR sent') if asr is not None else None,
                      model_end_perf=stamp(record.get('model_end'), 'model end'),
                      worker_job_end_perf=stamp(record.get('worker_job_end_perf'), 'worker end'),
                      completed_sent_perf=stamp(completed.get('sent_perf'), 'complete sent') if completed is not None else None,
                      abandoned_sent_perf=stamp(terminal.get('sent_perf'), 'abandoned sent')
                      if terminal is not None and terminal['kind'] == 'abandoned' else None,
                      durable_sync_perf=stamp(sync['receipt'].get('synced_perf'), 'durable synced') if sync else None,
                      durable_sync_log_observed_perf=stamp(sync.get('observed'), 'sync log') if sync else None,
                      canonical_install_log_observed_perf=stamp(install.get('observed'), 'install log') if install else None,
                      parent_install_log_observed_perf=parent_install,
                      canonical_parent_install_to_dispatch_seconds=start_gap,
                      canonical_parent_install_to_dispatch_status=start_gap_status,
                      dispatch_relative_to_parent_install_seconds=delta(dispatch, parent_install),
                      first_actual_private_view_perf=stamp(first_private, 'first private Consumer'),
                      first_actual_fact_application_perf=stamp(first_certified, 'first fact Consumer'),
                      promotion_count=len(entry['promotions']),
                      promotion_observed_perfs=[stamp(r.get('observed'), 'promotion') for r in entry['promotions']],
                      policy_terminal_outcomes=[r['kind'] for r in entry['policy_outcomes']],
                      policy_proofs=[r['body'].get('proof') for r in entry['policy_outcomes']],
                      selection_changed=record.get('selection_changed'),
                      native_model_evaluated=record.get('native_model_evaluated'),
                      own_projection_vs_complete_full_state_equal=None if own_projection is None or completed is None
                      else same(own_projection, completed['end']),
                      projection_vs_selected_full_state_equal=None if own_projection is None or selected_end is None
                      else same(own_projection, selected_end),
                      completed_vs_selected_full_state_equal=None if completed is None or selected_end is None
                      else same(completed['end'], selected_end),
                      durable_selected=fact is not None,
                      journal_sequence=fact['receipt']['sequence'] if fact is not None else None,
                      transition_id=fact['body']['transition_id'] if fact is not None else None)
        for label, end, begin in (
                ('worker_begin_minus_dispatch_seconds', output['worker_job_begin_perf'], dispatch),
                ('model_host_seconds', output['model_end_perf'], output['model_start_perf']),
                ('ASR_to_model_end_seconds', output['model_end_perf'], output['ASR_produced_perf']),
                ('complete_sent_to_durable_sync_seconds', output['durable_sync_perf'], output['completed_sent_perf'])):
            output[label] = delta(end, begin)
        rows.append(output)
    return rows


def display_chain(frontier, actual_row, binding, timeline):
    result = dict(first_D_actual_G=None, first_D_actual_observed_perf=None,
                  first_D_row_kind=None, first_D_private_job=None,
                  actual_event_publication_id=None, actual_event_publication_received_perf=None,
                  view_origin_publication_id=None, view_origin_publication_owner_epoch=None,
                  view_origin_publication_received_perf=None, view_binding=None,
                  view_tip_internal_frontier=None, view_tip_full_state_sha256=None,
                  view_job_id=None, view_job_owner_epoch=None,
                  decomposition_status='NO_ACTUAL_DISPLAY', dispatch_minus_offer_seconds=None,
                  ASR_minus_dispatch_seconds=None, Consumer_minus_ASR_seconds=None,
                  publication_receive_minus_ASR_seconds=None,
                  Consumer_minus_publication_receive_seconds=None, decomposition_sum_seconds=None)
    if actual_row is None:
        return result
    observed = stamp(actual_row['observed'], 'first actual display')
    close(observed - frontier['offer'], frontier['D'], 'D must equal original first actual row minus offer')
    result.update(first_D_actual_G=actual_row['visible_frontier'], first_D_actual_observed_perf=observed,
                  first_D_row_kind=actual_row['kind'], first_D_private_job=actual_row.get('private_job'),
                  actual_event_publication_id=actual_row.get('publication_id'), view_binding=binding['kind'],
                  view_origin_publication_id=binding['view_publication_id'],
                  view_origin_publication_owner_epoch=binding['view_publication_owner_epoch'],
                  view_tip_internal_frontier=binding.get('view_tip_internal_frontier'),
                  view_tip_full_state_sha256=binding.get('view_tip_full_state_sha256'))
    current_pub, view_pub = binding['actual_publication'], binding['view_publication']
    for field, pub in (('actual_event_publication_received_perf', current_pub),
                       ('view_origin_publication_received_perf', view_pub)):
        result[field] = stamp(pub.get('received_perf'), field) if pub is not None else None
    identity = binding['identity']
    if identity is not None:
        result.update(view_job_owner_epoch=identity[0], view_job_id=identity[1])
    if not actual_row.get('private_job'):
        result['decomposition_status'] = 'NOT_APPLICABLE_CANONICAL_FACT_FALLBACK'
        return result
    dispatch, asr = timeline['dispatched_perf'], timeline['ASR_produced_perf']
    received = result['view_origin_publication_received_perf']
    if dispatch is None or asr is None:
        result['decomposition_status'] = 'NOT_APPLICABLE_MISSING_SAME_JOB_DISPATCH_OR_ASR_TIME'
        return result
    if not (dispatch <= asr <= observed):
        result['decomposition_status'] = 'NOT_APPLICABLE_RECORDED_CLOCK_ORDER'
        return result
    parts = dispatch - frontier['offer'], asr - dispatch, observed - asr
    result.update(dispatch_minus_offer_seconds=parts[0], ASR_minus_dispatch_seconds=parts[1],
                  Consumer_minus_ASR_seconds=parts[2], decomposition_sum_seconds=sum(parts),
                  decomposition_status='RECORDED_SAME_PRIVATE_JOB_PATH')
    close(sum(parts), frontier['D'], 'recorded D decomposition conservation')
    if received is not None:
        result['publication_receive_minus_ASR_seconds'] = received - asr
        result['Consumer_minus_publication_receive_seconds'] = observed - received
        close((received - asr) + (observed - received), observed - asr,
              'publication receipt/Consumer split conservation')
        if not asr <= received <= observed:
            result['decomposition_status'] = 'RECORDED_D_PATH_WITH_NONMONOTONIC_PUBLICATION_TIMESTAMPS'
    return result


def _analyze_cell(cell, data, archived):
    config = data['config']
    need(config['cell_id'] == cell['cell_id'] and config['arm'] == cell['policy']
         and config['repeat'] == cell['repeat'], 'original cell identity differs')
    origin = data['origin']
    need(origin['original_D'] == 2. and origin['original_C'] == 8., 'original deadlines changed')
    context = build_context(data)
    need(context['source']['source_id'] == cell['source_id'], 'configured source identity differs')
    primary, frontiers = endpoints(data['consumer'], context['source'], origin['origin_perf'])
    compare_endpoints(primary, frontiers, data['summary']['primary'], archived['primary'])
    close(data['summary']['content']['original_dual_credit_audio_seconds'],
          primary['dual_deadline_audio_credit_seconds'], 'original NN content credit')
    close(len(context['facts']), archived['semantic']['checked_steps'], 'all original selected steps')
    timelines = job_timelines(data, context)
    by_job = {(r['owner_epoch'], r['job_id']): r for r in timelines}
    bindings = view_bindings(data['consumer'], context, cell['cell_id'])
    endpoint_rows, misses = [], []
    metadata = {k: cell[k] for k in ('cell_id', 'source_id', 'speaker_id', 'policy', 'repeat')}
    for frontier in frontiers:
        index = frontier['first_D_row_index']
        actual = data['consumer'][index] if index is not None else None
        binding = bindings[index] if index is not None else None
        timeline = by_job[binding['identity']] if binding is not None and binding['identity'] is not None else None
        chain = display_chain(frontier, actual, binding, timeline)
        item = {**metadata, **frontier, **chain}
        if timeline is not None:
            item.update({'job_' + k: v for k, v in timeline.items() if k not in ('source_id',)})
        cindex = frontier['first_C_row_index']
        item['first_C_actual_observed_perf'] = data['consumer'][cindex]['observed'] if cindex is not None else None
        item['first_C_actual_processed_frontier'] = data['consumer'][cindex]['certified_frontier'] if cindex is not None else None
        endpoint_rows.append(item)
        if not frontier['D2']:
            misses.append(item)
    for row in timelines:
        row.update(metadata)
    missed = sum(r['audio_seconds'] for r in frontiers if not (r['D2'] and r['C8']))
    summary = dict(metadata, primary=primary, selected_steps=len(context['facts']), issued_jobs=len(timelines),
                   D2_missed_audio_s=sum(r['audio_seconds'] for r in frontiers if not r['D2']),
                   dual_deadline_missed_audio_s=missed,
                   job_status_counts=dict(Counter(r['terminal_kind'] or 'no_terminal_receipt' for r in timelines)),
                   promotion_events=sum(r['promotion_count'] for r in timelines),
                   abandoned_jobs=sum(r['terminal_kind'] == 'abandoned' for r in timelines),
                   selected_changed_jobs=sum(r['selection_changed'] is True for r in timelines),
                   selected_unchanged_jobs=sum(r['selection_changed'] is False for r in timelines),
                   selected_change_not_recorded_jobs=sum(r['selection_changed'] is None for r in timelines),
                   own_projection_state_mismatches=sum(r['own_projection_vs_complete_full_state_equal'] is False
                                                       for r in timelines),
                   frozen_parent_state_mismatches=sum(r['actual_parent_full_state_equal'] is False for r in timelines),
                   missing_phase_timestamps={field: sum(r[field] is None for r in timelines)
                                            for field in ('dispatched_perf', 'worker_job_begin_perf', 'model_start_perf',
                                                          'ASR_produced_perf', 'model_end_perf', 'worker_job_end_perf',
                                                          'completed_sent_perf', 'durable_sync_perf',
                                                          'canonical_install_log_observed_perf')},
                   quality=data['summary']['quality'])
    return summary, timelines, endpoint_rows, misses


def analyze_cell(cell, data, archived):
    try:
        return _analyze_cell(cell, data, archived)
    except TraceError as error:
        raise TraceError('cell=' + cell['cell_id'] + ': ' + str(error)) from error


def aggregate(cells):
    need(len(cells) == 32, 'partial cell result cannot pass complete accounting')
    policy = {}
    for arm in ('conservative', 'fullcall'):
        own = [r for r in cells if r['policy'] == arm]
        need(len(own) == 16, 'policy coverage missing')
        policy[arm] = dict(trials=len(own), offered_audio_s=sum(r['primary']['offered_audio_seconds'] for r in own),
                           original_credit_audio_s=sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in own),
                           D2_missed_audio_s=sum(r['D2_missed_audio_s'] for r in own),
                           dual_deadline_missed_audio_s=sum(r['dual_deadline_missed_audio_s'] for r in own),
                           passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in own))
        close(policy[arm]['original_credit_audio_s'] + policy[arm]['dual_deadline_missed_audio_s'],
              policy[arm]['offered_audio_s'], 'complete policy credit plus deficit conservation')
    sources = []
    denominator = policy['fullcall']['dual_deadline_missed_audio_s']
    for sid in sorted({row['source_id'] for row in cells}):
        own = [row for row in cells if row['source_id'] == sid and row['policy'] == 'fullcall']
        missed = sum(r['dual_deadline_missed_audio_s'] for r in own)
        quality = [q for r in cells if r['source_id'] == sid for q in r['quality']]
        need(quality and all(q == quality[0] for q in quality), 'quality/source identity changed across policies/repeats')
        sources.append(dict(source_id=sid, speaker_id=own[0]['speaker_id'], trials=len(own),
                            offered_audio_s=sum(r['primary']['offered_audio_seconds'] for r in own),
                            fullcall_credit_audio_s=sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in own),
                            fullcall_D2_missed_audio_s=sum(r['D2_missed_audio_s'] for r in own),
                            fullcall_dual_deadline_missed_audio_s=missed,
                            share_of_fullcall_missed_audio=None if denominator == 0 else missed / denominator,
                            failed_cell_ids=[r['cell_id'] for r in own if not r['primary']['complete_coverage_and_original_quantile_pass']],
                            character_edits=quality[0]['character_edits'],
                            reference_characters=quality[0]['reference_characters'], CER=quality[0]['CER']))
    close(sum(r['fullcall_dual_deadline_missed_audio_s'] for r in sources), denominator,
          'source deficit ledger conservation')
    return dict(status='PASS_COMPLETE32_RECORDED_TRACE_ACCOUNTING', policies=policy,
                failed_fullcall_cell_ids=[r['cell_id'] for r in cells if r['policy'] == 'fullcall'
                                         and not r['primary']['complete_coverage_and_original_quantile_pass']],
                source_deficit_ledger=sources, selected_steps=sum(r['selected_steps'] for r in cells),
                scope='Observed event paths on the original clocks. No counterfactual speed, pure guard tax, repair or deadline guarantee.',
                new_model_calls=0)
