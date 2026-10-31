"""CPU-only content endpoints and actual full-path visibility continuity.

The imported c4 checker validates every supplied full receipt, durable fact and
Consumer application before the extra interval reader is allowed to run.
Intervals describe logical Consumer snapshots, never network/UI availability.
"""
from __future__ import annotations
import copy
import math
from collections import Counter
from pathlib import Path

from content_endpoints import analyze_cell
from resilience_metrics import posterior_support
from refinement_trace import audit, read_frames, wrapped_publication, same, digest, cut
from resident_analysis import audit_request_clocks
from endpoints import recount

FINAL = '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'

def need(ok, message):
    if not ok:
        raise ValueError(message)

def close(a, b, label='numeric conservation'):
    if isinstance(a, dict):
        need(isinstance(b, dict) and set(a) == set(b), label + ' keys')
        for k in a:
            close(a[k], b[k], label + '.' + str(k))
    elif isinstance(a, list):
        need(isinstance(b, list) and len(a) == len(b), label + ' list')
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, label + '.' + str(i))
    elif type(a) in (int, float) and type(b) in (int, float):
        need(math.isfinite(a) and math.isfinite(b) and abs(a-b) <= 1e-7, label)
    else:
        need(a == b, label)

def continuity(frames, publications, rows):
    """Called only after the complete c4 audit; independently verify snapshots.

    A view is identified by its complete tip, not its rendered text. Compatible
    boundary installation changes the path root while retaining the exact tip.
    Last observations are censored, with no hypothetical hold to service end.
    """
    roots = {sid: cut(value) for sid, value in frames[0][0]['body']['initials'].items()}
    states = {sid: dict(canonical=value, steps=[], processed=0) for sid, value in roots.items()}
    facts = {receipt['sequence']: obj['body'] for obj, receipt in frames[1:]}
    pubs = {wrapped_publication(r)[0:1] + (wrapped_publication(r)[1]['publication_id'],): wrapped_publication(r)[1] for r in publications}
    events, intervals, segments = [], [], []
    previous = {}; active = {}; counts = Counter()
    for index, row in enumerate(rows):
        sid = row['source_id']; s = states[sid]; t = row['observed']
        need(type(t) in (int, float) and math.isfinite(t), 'nonfinite Consumer clock')
        before_tip = s['steps'][-1]['end'] if s['steps'] else s['canonical']
        before_sha = digest(before_tip)
        if sid in previous:
            prev = previous[sid]
            need(t >= prev['observed'], 'same-source Consumer clock regressed')
            intervals.append(dict(source_id=sid, start_row=prev['row'], end_row=index,
                start_perf=prev['observed'], end_perf=t, seconds=t-prev['observed'],
                visible_frontier=prev['visible_frontier'], tip_sha256=prev['tip_sha256'],
                text_sha256=prev['text_sha256'], private_job=prev['private_job'],
                full_dependency_path_verified=True, right_censored=False,
                support_kind='actual_complete_dependency_path_not_posterior_text_agreement'))
        ev = None
        if row['kind'] == 'canonical':
            body = facts[row['journal_sequence']]; new = body['next_state']
            need(same(body['parent_state'], s['canonical']), 'continuity parent changed')
            boundary = next((i for i, step in enumerate(s['steps']) if step['end']['frontier'] == new['frontier']), None)
            compatible = boundary is not None and same(s['steps'][boundary]['end'], new)
            ahead = before_tip['frontier'] > new['frontier']
            s['steps'] = s['steps'][boundary+1:] if compatible else []
            s['canonical'] = new
            if body['record']['native_model_evaluated']:
                s['processed'] = new['frontier']
            after_tip = s['steps'][-1]['end'] if s['steps'] else s['canonical']
            if ahead:
                kind = 'compatible_ahead_preserved' if compatible else 'necessary_incompatible_withdrawal'
                retained = same(before_tip, after_tip)
                need(retained if compatible else not retained, 'actual full-tip retention contradicts full boundary')
                counts[kind] += 1
                counts[kind+'_nonempty_before'] += bool(before_tip['transcript'])
                ev = dict(source_id=sid, row_index=index, observed_perf=t, kind=kind,
                    full_boundary_compatible=compatible, before_tip_sha256=before_sha,
                    after_tip_sha256=digest(after_tip), before_frontier=before_tip['frontier'],
                    canonical_after_frontier=new['frontier'], after_frontier=after_tip['frontier'],
                    actual_visible_before_frontier=before_tip['frontier'] if before_tip['transcript'] else 0,
                    actual_visible_after_frontier=after_tip['frontier'] if after_tip['transcript'] else 0,
                    before_text_empty=not bool(before_tip['transcript']),after_text_empty=not bool(after_tip['transcript']),
                    actual_tip_preserved=retained, private_job_before=previous.get(sid,{}).get('private_job'),
                    private_job_after=s['steps'][-1]['job_id'] if s['steps'] else None)
                events.append(ev)
        elif row['kind'] == 'private':
            event = pubs[(row['owner_epoch'], row['publication_id'])]
            need(event['canonical_sha'] == digest(s['canonical']), 'private root not current')
            steps = event['steps']; parent = s['canonical']
            for step in steps:
                need(same(step['start'], parent), 'private full path gapped')
                parent = step['end']
            if parent['frontier'] >= before_tip['frontier']:
                s['steps'] = steps
        else:
            raise ValueError('undeclared Consumer application')
        tip = s['steps'][-1]['end'] if s['steps'] else s['canonical']; tip_sha = digest(tip)
        expected = dict(canonical_sha=digest(s['canonical']), certified_frontier=s['processed'],
            visible_frontier=tip['frontier'] if tip['transcript'] else 0, text=tip['transcript'],
            private_job=s['steps'][-1]['job_id'] if s['steps'] else None)
        for key, value in expected.items():
            need(row[key] == value, 'continuity actual snapshot mismatch: ' + key)
        # Merge an identical complete tip across intervening actual updates.
        # A different legal view is supersession, not an availability outage.
        if sid not in active or active[sid]['tip_sha256'] != tip_sha:
            if sid in active:
                old = active[sid]
                old.update(end_perf=t, end_row=index, observed_seconds=t-old['start_perf'],
                    close_kind='necessary_incompatible_withdrawal' if ev and ev['kind']=='necessary_incompatible_withdrawal' else 'legal_supersession',
                    right_censored=False)
                segments.append(old)
            active[sid] = dict(source_id=sid, tip_sha256=tip_sha, frontier=tip['frontier'],
                text_sha256=__import__('hashlib').sha256(tip['transcript'].encode()).hexdigest(),
                text_code_points=len(tip['transcript']),
                start_perf=t, start_row=index, compatible_updates_crossed=0,
                dependency_path_verified=True)
        if ev and ev['kind'] == 'compatible_ahead_preserved':
            active[sid]['compatible_updates_crossed'] += 1
        previous[sid] = dict(row=index, observed=t, tip_sha256=tip_sha,
            visible_frontier=expected['visible_frontier'], text_sha256=active[sid]['text_sha256'],
            private_job=expected['private_job'])
    for sid, old in active.items():
        last = previous[sid]
        old.update(end_perf=last['observed'], end_row=last['row'],
            observed_seconds=last['observed']-old['start_perf'],
            close_kind='last_actual_same_source_observation', right_censored=True)
        segments.append(old)
    summary = dict(status='VERIFIED_LOGICAL_CONSUMER_DEPENDENCY_PATH_CONTINUITY',
        compatible_ahead_applications=counts['compatible_ahead_preserved'],
        compatible_ahead_preserved=counts['compatible_ahead_preserved'],
        compatible_ahead_nonempty_views=counts['compatible_ahead_preserved_nonempty_before'],
        compatible_ahead_nonempty_preserved=counts['compatible_ahead_preserved_nonempty_before'],
        compatible_ahead_empty_tips=counts['compatible_ahead_preserved']-counts['compatible_ahead_preserved_nonempty_before'],
        necessary_incompatible_withdrawals=counts['necessary_incompatible_withdrawal'],
        necessary_nonempty_view_withdrawals=counts['necessary_incompatible_withdrawal_nonempty_before'],
        wrong_compatible_withdrawals=0, unknown_dependency_events=0,
        actual_Consumer_rows=len(rows), observed_intervals=len(intervals),
        observed_same_source_snapshot_seconds=sum(x['seconds'] for x in intervals),
        retained_tip_segments_crossing_compatible_updates=sum(x['compatible_updates_crossed']>0 for x in segments),
        observed_seconds_of_complete_tip_segments_crossing_compatible_updates=sum(x['observed_seconds'] for x in segments if x['compatible_updates_crossed']>0),
        retained_nonempty_tip_segments_crossing_compatible_updates=sum(x['compatible_updates_crossed']>0 and x['text_code_points']>0 for x in segments),
        observed_nonempty_seconds_of_tip_segments_crossing_compatible_updates=sum(x['observed_seconds'] for x in segments if x['compatible_updates_crossed']>0 and x['text_code_points']>0),
        time_scope='Logical Consumer state held between complete recorded actual applications; final same-source observation is right-censored. Not browser/network availability, human correctness, or online certification.',
        unknown_rule='Missing full dependency or snapshot mismatch fails this reader; no zero-error result is emitted for an unverified path.')
    return summary, events, intervals, segments

def analyze_trial(cell, io):
    root = Path(cell['raw_root']); config = io.json(root/'CONFIG.json')
    need(config['settings']['source_commit'] == FINAL, 'wrong NN source')
    need(config['cell_id'] == cell['cell_id'] and config['arm'] == cell['arm'] and config['repeat'] == cell['repeat'], 'trial identity changed')
    sources = {s['source_id']:s for s in config['settings']['sources']}
    need(set(sources)==set(cell['source_ids']), 'frozen acoustic source set changed')
    close([{k:sources[sid][k] for k in ('source_id','frames','audio_sha256')} for sid in sorted(sources)],cell['expected_sources'],'frozen original source identity')
    frames, frame_meta = read_frames(io.path(root/'facts.wal'), allow_incomplete_tail=False)
    from refinement_trace import wire
    import hashlib
    need(frames[0][0]['body']['metadata']['config_sha256'] == hashlib.sha256(wire(config)).hexdigest(), 'durable original config differs')
    rows = io.lines(root/'consumer.jsonl'); pubs = io.lines(root/'publications.jsonl')
    dispatch, completions = [], []
    actual_owners={p.name for p in root.iterdir() if p.is_dir() and p.name.startswith('owner_e')}
    need(actual_owners==set(cell['owner_directories']), 'frozen physical Owner attempt set differs')
    # Owner directory set is frozen in the input whitelist, not discovered by a
    # new unbounded recursive scan. A physical owner is never relabelled.
    for owner in cell['owner_directories']:
        epoch = int(Path(owner).name.removeprefix('owner_e'))
        for row in io.lines(root/owner/'dispatch.jsonl'):
            need(row['owner_epoch'] == epoch, 'dispatch owner directory binding')
            dispatch.append(row)
        for row in io.lines(root/owner/'worker_results.jsonl'):
            need('owner_epoch' not in row or row['owner_epoch'] == epoch, 'receipt owner binding')
            completions.append(dict(row, owner_epoch=epoch))
    structural = audit(frames=frames, dispatch_rows=dispatch, completion_rows=completions,
        publication_rows=pubs, consumer_rows=rows, expected_runtime_commit=FINAL,
        expected_final_frontiers={sid:s['frames'] for sid,s in sources.items()})
    origin_record = io.json(root/'ORIGIN.json')
    need(origin_record['original_D'] == 2. and origin_record['original_C'] == 8., 'original deadlines changed')
    ingress = io.lines(root/'ingress.jsonl')
    if cell['cohort'] == 'resident':
        origins = io.json(root/'REQUEST_ORIGINS.json'); ledger = io.lines(root/'request_ledger.jsonl')
        need(config['request_contract'] == 'closed_loop_single_outstanding_independent_EOS_v1', 'resident contract changed')
        clocks = audit_request_clocks(config, origins, ledger, ingress, rows)
    else:
        origins = {sid:origin_record['origin_perf'] for sid in sources}
        from refinement_trace import check_original_ingress
        clocks = check_original_ingress(origin=origin_record['origin_perf'], sources=list(sources.values()), ingress_rows=ingress)
    need(set(origins) == set(sources), 'origins differ from sources')
    # Complete Reader checks all dispatches against the appropriate per-request
    # original offer, including independent EOS, instead of c4's single origin.
    for row in dispatch:
        job = row['job']; stamp = job.get('dispatched_perf')
        need(type(stamp) in (int,float), 'actual dispatch clock absent')
        need(stamp >= origins[job['source_id']] + job['end']/16000, 'dispatch before original request offer')
    old_summary = io.json(root/'SUMMARY.json')
    all_primary = recount(rows, sources, origins)
    for key, value in old_summary['primary'].items():
        if key in all_primary:
            close(all_primary[key], value, 'original primary.'+key)
    facts = [dict(sequence=r['sequence'], body=obj['body'], receipt=r) for obj,r in frames[1:]]
    requests, first_rows = [], []
    for sid, source in sources.items():
        own = [r for r in rows if r['source_id']==sid]
        meta = dict(cell_id=cell['cell_id'], stage='final4f_existing20_CPU_recount',
            cohort=cell['cohort'], arm=cell['arm'], repeat=cell['repeat'])
        content, _, _, frontiers = analyze_cell(meta, own, {sid:source}, origins[sid])
        support = posterior_support(own, frontiers, facts)
        primary = recount(own, {sid:source}, {sid:origins[sid]})
        close(content['original_dual_credit_audio_seconds'], primary['dual_deadline_audio_credit_seconds'], 'content credit')
        for mode in ('raw','whitespace_stripped'):
            close(sum(support[mode][k] for k in ('original_credit_supported_seconds','original_credit_mismatching_seconds','original_credit_unknown_seconds')), content['original_dual_credit_audio_seconds'], 'support partition')
        if cell['cohort']=='paired':
            comparable=copy.deepcopy(content); comparable.update({k:old_summary['content'][k] for k in ('stage','cohort')})
            close(comparable, old_summary['content'], 'existing paired content')
            close(support, old_summary['posterior_whole_text_support'], 'existing paired posterior')
        else:
            old = next(x for x in old_summary['per_request'] if x['source_id']==sid)
            close(primary, old['primary'], 'original resident request endpoint')
        for f in frontiers:
            i=f['first_visible_row']; row=own[i] if i is not None else None
            expected=next((x['body']['next_state']['transcript'] for x in facts if x['body']['source_id']==sid and row is not None and x['body']['next_state']['frontier']==row['visible_frontier']),None)
            first_rows.append(dict(cell_id=cell['cell_id'],source_id=sid,frontier=f['frontier'],
                original_offer_perf=f['original_ready_perf'],G=row['visible_frontier'] if row else None,
                actual_first_G_observed_perf=row['observed'] if row else None,
                whole_text_support='unknown' if expected is None else 'supported' if row['text']==expected else 'mismatching',
                original_dual_credit=f['original_dual_credit'],audio_seconds=f['audio_seconds']))
        requests.append(dict(cell_id=cell['cell_id'],source_id=sid,cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],
            request_origin_perf=origins[sid],primary=primary,content=content,posterior_whole_text_support=support))
    continuous, events, intervals, segments = continuity(frames,pubs,rows)
    close(continuous['compatible_ahead_applications'], structural['counts']['compatible_ahead_applications'])
    close(continuous['compatible_ahead_preserved'], structural['counts']['compatible_ahead_preserved'])
    close(continuous['necessary_incompatible_withdrawals'], structural['counts']['incompatible_ahead_withdrawals'])
    for output in (events, intervals, segments):
        for r in output:
            r['cell_id']=cell['cell_id'];r['cohort']=cell['cohort'];r['arm']=cell['arm']
    return dict(cell_id=cell['cell_id'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],
        actual_NN_source_commit=FINAL, independent_frame_scan=frame_meta,structural=structural,
        request_clock=clocks,primary=all_primary,continuity=continuous),requests,first_rows,events,intervals,segments

def aggregate(requests, cells):
    result={}
    for cohort in ('paired','resident'):
        for arm in ('conservative','fullcall'):
            rr=[r for r in requests if r['cohort']==cohort and r['arm']==arm]
            cc=[r for r in cells if r['cohort']==cohort and r['arm']==arm]
            need(len(rr)==8, 'complete fixed group needs eight requests')
            group=dict(trials=len(cc),request_instances=len(rr),independent_acoustic_sources=4,
                offered_audio_seconds=sum(r['primary']['offered_audio_seconds'] for r in rr),
                original_dual_credit_audio_seconds=sum(r['primary']['dual_deadline_audio_credit_seconds'] for r in rr),
                original_request_gate_passes=sum(r['primary']['complete_coverage_and_original_quantile_pass'] for r in rr),
                content={},posterior_whole_text_support={},continuity={})
            for mode in ('raw','whitespace_stripped'):
                keys=('introduced_code_point_occurrences','retracted_occurrence_code_points','still_visible_occurrence_code_points','closed_occurrence_code_point_seconds','observed_text_changes')
                group['content'][mode]={k:sum(r['content'][mode][k] for r in rr) for k in keys}
                keys=('original_credit_supported_seconds','original_credit_mismatching_seconds','original_credit_unknown_seconds')
                group['posterior_whole_text_support'][mode]={k:sum(r['posterior_whole_text_support'][mode][k] for r in rr) for k in keys}
                counts=Counter()
                for r in rr:counts.update(r['posterior_whole_text_support'][mode]['all_offered_frontier_counts'])
                group['posterior_whole_text_support'][mode]['all_offered_frontier_counts']=dict(counts)
            for key in ('compatible_ahead_applications','compatible_ahead_preserved','compatible_ahead_nonempty_views','compatible_ahead_nonempty_preserved','compatible_ahead_empty_tips','necessary_incompatible_withdrawals','necessary_nonempty_view_withdrawals','wrong_compatible_withdrawals','unknown_dependency_events','retained_tip_segments_crossing_compatible_updates','observed_seconds_of_complete_tip_segments_crossing_compatible_updates','retained_nonempty_tip_segments_crossing_compatible_updates','observed_nonempty_seconds_of_tip_segments_crossing_compatible_updates'):
                group['continuity'][key]=sum(c['continuity'][key] for c in cc)
            result[cohort+'/'+arm]=group
    return result
