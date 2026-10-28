"""Aggregate frozen RevTrace service cells without importing runtime policies.

Read existing audited results only. Missing, failed, deferred and repaired old
cells remain visible; none become completed experimental arms by aggregation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import re
import statistics
import sys
import unicodedata


SAFE_STATUS = 'COMPLETE_SINGLE_CELL_AND_INDEPENDENT_AUDIT'
SAFE_AUDIT = 'PASS_INDEPENDENT_RETIREMENT_AND_INPUT_CONSUMER_AUDIT'
FACTORS = ('R0_S0','R0_S1','R1_S0','R1_S1')
MEASURES = {
    'dual_audio_fraction':1, 'all_offered_audio_goodput_2_8':1,
    'display_P99':-1, 'commit_view_P99':-1, 'GPU_J_per_offered_audio_second':-1,
    'all_offered_WER_percent':-1, 'all_offered_character_error_percent':-1,
    'audio_rollback_events':-1, 'audio_rollback_seconds':-1,
    'rollback_area_audio_seconds_x_wall_seconds':-1,
    'erased_visible_characters':-1, 'longest_actual_visible_progress_gap_seconds':-1,
}
INPUT_FILES = {}


def input_bytes(path):
    path=Path(path);payload=path.read_bytes()
    INPUT_FILES[str(path.resolve())]=dict(bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    return payload
def read(path):return json.loads(input_bytes(path).decode('utf8'))
def lines(path):return [json.loads(row) for row in input_bytes(path).decode('utf8').splitlines() if row]
def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def fsha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(condition,message):
    if not condition:raise AssertionError(message)
def finite(value):return type(value) in (int,float) and math.isfinite(value)
def minus(a,b):return a-b if finite(a) and finite(b) else None
def average(values):
    values=list(values)
    return statistics.mean(values) if values and all(finite(value) for value in values) else None
def percentile(values,q):
    values=sorted(float(value) if finite(value) else math.inf for value in values)
    if not values:return None
    position=(len(values)-1)*q;i=int(position);j=min(i+1,len(values)-1)
    return values[i]+(values[j]-values[i])*(position-i) if math.isfinite(values[j]) else None
def edit_distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        next_row=[i]
        for j,y in enumerate(b,1):next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=next_row
    return row[-1]
def flag(argv,key,default=None):
    return argv[argv.index(key)+1] if key in argv else default
def basename(path):return str(path).replace('\\','/').rstrip('/').rsplit('/',1)[-1]


def planned_cells(plan):
    output=[];seen=set()
    cohorts={row['cohort']:row for row in plan.get('cohorts',[])}
    for raw in plan['cells']:
        argv=raw.get('argv',[]);target=raw.get('out',raw.get('output',flag(argv,'--out')))
        need(bool(target),'planned cell has no output path')
        cid=raw.get('cell_id',basename(target));need(cid not in seen,'duplicate frozen cell ID');seen.add(cid)
        cell=dict(raw,cell_id=cid,out=target)
        for key,option,default in [('adapter','--adapter','qwen'),('arrival','--arrival','sync'),
            ('policy','--policy','row_complete'),('method','--method','standard_fair'),
            ('retain','--retain','yes'),('confirmation_consumer','--confirmation-consumer','two_lane')]:
            cell[key]=cell.get(key,flag(argv,option,default))
        for key,option,default in [('rho','--rho',1),('sessions','--sessions',16),('repeat','--repeat',0)]:
            cell[key]=int(cell.get(key,flag(argv,option,default)))
        cell.setdefault('model',flag(argv,'--model'));cell.setdefault('manifest',flag(argv,'--manifest'))
        cell.setdefault('expected_source_commit',plan.get('code_commit'))
        cell.setdefault('fixture',flag(argv,'--fixture'));cell.setdefault('arm',cell['policy'])
        cell.setdefault('phase','retirement');cell.setdefault('cohort','development')
        if cell['cohort'] in cohorts:
            cohort=cohorts[cell['cohort']]
            cell['expected_source_ids']=cohort['source_ids']
            cell['expected_speakers']=dict(zip(cohort['source_ids'],cohort['speakers']))
        cell.setdefault('paired_block','|'.join(map(str,[cell['phase'],cell['adapter'],cell['rho'],
            cell['arrival'],cell['cohort'],cell['repeat'],cell['sessions']])))
        output.append(cell)
    return output


def visible_revisions(records, *, end_perf, sample_rate=16000):
    """Adjacent actual-view drops and high-watermark deficit area, no double count.

    Area integrates max(previous observed high-watermark - current view, 0)
    until recovery/end. Nested drops share one deficit process. This describes
    visible withdrawal, including necessary legal withdrawal; it is not a safety
    failure count. Trigger labels never infer semantics absent from metadata.
    """
    by_session=defaultdict(list)
    for row in records:by_session[row['session_id']].append(row)
    output={}
    for sid,rows in by_session.items():
        rows=sorted(rows,key=lambda row:row['observed_perf'])
        previous=None;high=0;area=0.;counts=Counter();audio_drop=0;erased=0;inserted=0
        for row in rows:
            now=row['observed_perf'];need(finite(now) and now<=end_perf+1e-6,'invalid actual Consumer clock')
            current=row['valid_visible_frontier'];need(type(current) is int and current>=0,'invalid visible frontier')
            if previous is not None:
                elapsed=now-previous['observed_perf'];need(elapsed>=0,'Consumer time regressed')
                area+=max(0,high-previous['valid_visible_frontier'])/sample_rate*elapsed
                decrease=previous['valid_visible_frontier']-current
                if decrease>0:
                    counts['audio_rollback_events']+=1;audio_drop+=decrease/sample_rate
                    if row.get('source_kind')=='canonical-display':counts['canonical_triggered_rollback_events']+=1
                    if row.get('certified_frontier',0)>previous.get('certified_frontier',0):counts['trusted_frontier_advance_rollback_events']+=1
                    if row.get('tentative_invalidated') is True:counts['explicit_tentative_invalidated_rollback_events']+=1
                    if row.get('source_kind')!='canonical-display':counts['other_triggered_rollback_events']+=1
                before,after=previous.get('visible_text',''),row.get('visible_text','')
                common=0
                for a,b in zip(before,after):
                    if a!=b:break
                    common+=1
                erased+=len(before)-common;inserted+=len(after)-common
            high=max(high,current);previous=row
        if previous is not None:area+=max(0,high-previous['valid_visible_frontier'])/sample_rate*(end_perf-previous['observed_perf'])
        output[sid]=dict(audio_rollback_events=counts['audio_rollback_events'],audio_rollback_seconds=audio_drop,
            rollback_area_audio_seconds_x_wall_seconds=area,erased_visible_characters=erased,
            inserted_visible_characters=inserted,canonical_triggered_rollback_events=counts['canonical_triggered_rollback_events'],
            trusted_frontier_advance_rollback_events=counts['trusted_frontier_advance_rollback_events'],
            explicit_tentative_invalidated_rollback_events=counts['explicit_tentative_invalidated_rollback_events'],
            other_triggered_rollback_events=counts['other_triggered_rollback_events'])
    return output


def history_digests(events,worker_records):
    """Full authoritative F/Z/P/text sequence per session, no clocks/job IDs."""
    results={row['job']['job_id']:row for row in worker_records};histories=defaultdict(list)
    for event in events:
        if event['kind']!='commit':continue
        selected=results[event['job_id']];need(selected['job']['role']=='authority','history uses non-Authority result')
        result=selected['result'];need(result['token_ids']==event['segment_tokens'] and result['state_tokens']==event['next_prompt_tokens'],'history selection mismatch')
        histories[event['session_id']].append(dict(version=event['version'],start=event['audio_start_sample'],
            F=event['audio_end_sample'],Z=event['segment_tokens'],P=event['next_prompt_tokens'],text=result['text']))
    for rows in histories.values():rows.sort(key=lambda row:row['version'])
    return {sid:sha(rows) for sid,rows in histories.items()}


def frontier_metrics(rows, expected_audio):
    keys={(row['session_id'],row['frontier']) for row in rows};need(len(keys)==len(rows),'duplicate offered frontier')
    audio=sum(row['audio_seconds'] for row in rows);need(abs(audio-expected_audio)<1e-6,'offered audio denominator changed')
    credited=0.;miss_display=miss_commit=0
    for row in rows:
        display=row['display_latency'];commit=row['commit_view_latency']
        dpass=finite(display) and display<=2.;cpass=finite(commit) and commit<=8.
        need(row['dual_credit']==(dpass and cpass),'frontier deadline classification mismatch')
        if dpass and cpass:credited+=row['audio_seconds']
        miss_display+=not dpass;miss_commit+=not cpass
    return dict(offered_audio_seconds=audio,dual_credited_audio_seconds=credited,dual_audio_fraction=credited/audio,
                offered_frontiers=len(rows),display_deadline_missed_frontiers=miss_display,
                commit_deadline_missed_frontiers=miss_commit)


def cell_path(cell,results_root):return Path(results_root)/basename(cell['out']) if results_root else Path(cell['out'])


def load_cell(cell, *, results_root=None, audit_overrides=None):
    directory=cell_path(cell,results_root);state=dict(cell_id=cell['cell_id'],arm=cell['arm'],path=str(directory),
        phase=cell['phase'],adapter=cell['adapter'],rho=cell['rho'],arrival=cell['arrival'],cohort=cell['cohort'],
        repeat=cell['repeat'],paired_block=cell['paired_block'],status='MISSING',formal_accepted=False)
    if not directory.exists():return state,None
    for name in ['STOP.json','RUNNER_EXIT.json','GATE.json']:
        if (directory/name).exists():state[name.removesuffix('.json').lower()]=read(directory/name)
    summary_path=directory/'SUMMARY.json'
    if not summary_path.exists():
        state['status']='FAILED_OR_UNFINISHED_WITHOUT_SUMMARY';return state,None
    summary=read(summary_path);state['recorded_summary_status']=summary.get('status')
    if summary.get('status')!=SAFE_STATUS or 'stop' in state:
        state['status']='FAILED_DEFERRED_OR_NONFINAL';return state,None
    need(state.get('gate',{}).get('gate')=='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT','cell lacks completed independent gate')
    frozen=read(directory/'FREEZE.json');cfg=frozen['frozen_config'];run=read(directory/'RUN_RECORD.json')
    need(summary['config']==cfg,'summary config differs from frozen config')
    same_source=summary['source_commit']==frozen['code_commit']==run['code_commit'];need(same_source,'cell source identity relabelled')
    if cell.get('expected_source_commit'):need(summary['source_commit']==cell['expected_source_commit'],'execution source differs from frozen plan')
    need(fsha(directory/'FREEZE.json')==run['frozen_config_sha256'],'cell freeze hash changed')
    if (directory/'ENVIRONMENT.json').exists():need(fsha(directory/'ENVIRONMENT.json')==cfg['environment_sha256'],'environment record changed')
    if (directory/'COMMAND.json').exists():
        command=read(directory/'COMMAND.json');need(fsha(directory/'COMMAND.json')==cfg['command_sha256'],'frozen command record changed')
        if cell.get('model'):need(flag(command['argv'],'--model')==cell['model'],'executed model differs from plan')
    for key in ['adapter','rho','arrival','repeat','method','sessions','policy']:
        need(cfg[key]==cell[key],'cell differs from frozen plan: '+key)
    need(cfg['retain_private_prefix']==cell['retain'] and cfg['confirmation_consumer']==cell['confirmation_consumer'],'composition arm differs from frozen plan')
    if cell.get('manifest_sha256'):need(cfg['original_manifest_sha256']==cell['manifest_sha256'],'source cohort manifest changed')
    need(cfg['display_slo_seconds']==2. and cfg['commit_slo_seconds']==8.,'original deadlines changed')
    audit_dir=Path((audit_overrides or {}).get(cell['cell_id'],directory/'audit'))
    independent=read(audit_dir/'SUMMARY.json');need(independent['status']==SAFE_AUDIT,'audit summary not accepted')
    need(independent==summary['independent_summary'],'separate/repaired audit cannot relabel original formal cell')
    service=independent['service'];lifecycle=independent['lifecycle']
    for key in ['unauthorized_admissions','stale_publications','root_incompatible_actual_views','certified_only_violations']:
        need(service[key]==0,'protected service invariant failed: '+key)
    need(independent['accepted_unfulfilled_samples']==0,'accepted input left unfinished')
    tables={name:read(audit_dir/(name+'.json')) for name in
        ['FRONTIERS','SESSIONS','REQUESTS','BATCHES','OBSERVED_INVALIDATIONS','INTERFERENCE']}
    sessions={row['session_id']:row for row in read(directory/'attempt0/sessions.json')}
    metadata=read(directory/'manifest.json')['sessions'];by_source={row['source_id']:row for row in metadata}
    if cell.get('expected_source_ids'):
        need([sessions[sid]['source_id'] for sid in sorted(sessions)]==cell['expected_source_ids'][:cell['sessions']],
             'actual source cohort/order differs from frozen plan')
        for source_id,speaker in cell['expected_speakers'].items():
            if source_id in by_source:need(str(by_source[source_id].get('speaker'))==str(speaker),'speaker identity differs from frozen cohort')
    per_session={row['session_id']:dict(row) for row in tables['SESSIONS']}
    need(set(per_session)==set(sessions),'session audit coverage incomplete')
    metric=dict(service);metric.update(frontier_metrics(tables['FRONTIERS'],sum(row['duration'] for row in sessions.values())))
    need(metric['offered_frontiers']==service['whole_offered_frontiers'],'offered frontier count changed')
    need(service['whole_run_dual_P99_pass']==(finite(service['display_P99']) and service['display_P99']<=2 and
        finite(service['commit_view_P99']) and service['commit_view_P99']<=8),'whole run 2s/8s classification mismatch')
    metric.update(complete_rows=lifecycle['complete_rows'],cancelled_rows=lifecycle['cancelled_rows'],
        physical_model_seconds=lifecycle['physical_model_seconds'],physical_lease_seconds=lifecycle['physical_lease_seconds'],
        post_invalidation_model_seconds=lifecycle['post_invalidation_model_seconds'],
        post_invalidation_lease_seconds=lifecycle['post_invalidation_lease_seconds'])
    requests=[row for row in tables['REQUESTS'] if row.get('outcome')=='row-cancelled']
    metric['cancel_request_to_ack_max_seconds']=max((row['request_to_ack_seconds'] for row in requests),default=None)
    metric['cancel_request_to_drain_max_seconds']=max((row['request_to_drain_seconds'] for row in requests),default=None)
    metric['cancel_post_ack_model_seconds_row_max']=max((row['post_ack_model_seconds'] for row in requests),default=None)
    metric['cancel_latency_count']=len(requests)
    fixture=read(directory/'fixture.json') if (directory/'fixture.json').exists() else None
    fault_sessions={int(key.split(':')[0]) for key in fixture['fault_plan']} if fixture else set()
    other=[row for row in per_session.values() if row['session_id'] not in fault_sessions]
    metric['other_session_max_gap_seconds']=max((row['longest_actual_visible_progress_gap_seconds'] for row in other),default=None) if fault_sessions else None
    interference=[row for row in tables['INTERFERENCE'] if row['relation']=='unrelated-session']
    metric['unrelated_stall_overlap_max_seconds']=max((row['longest_visible_stall_overlap_seconds'] for row in interference),default=None)
    context=read(directory/'episode.json');end=context['origin_perf']+service['original_episode_wall_seconds']
    consumer_path=directory/'attempt0/consumer.jsonl'
    revisions=visible_revisions(lines(consumer_path),end_perf=end) if consumer_path.exists() else {}
    state['actual_consumer_revision_data_available']=bool(revisions)
    for sid,row in per_session.items():
        spec=sessions[sid];source=by_source[spec['source_id']]
        known_speaker=source.get('speaker',source.get('speaker_id'))
        row.update(source_id=spec['source_id'],speaker=str(known_speaker) if known_speaker is not None else None,
            cohort=cell['cohort'],cell_id=cell['cell_id'],arm=cell['arm'])
        source_frontiers=[item for item in tables['FRONTIERS'] if item['session_id']==sid]
        row.update(frontier_metrics(source_frontiers,spec['duration']))
        row.update(display_P99=percentile([item['display_latency'] for item in source_frontiers],.99),
            commit_view_P99=percentile([item['commit_view_latency'] for item in source_frontiers],.99),
            all_offered_audio_goodput_2_8=row['dual_credited_audio_seconds']/service['original_episode_wall_seconds'])
        if sid in revisions:row.update(revisions[sid])
    if (directory/'attempt0/result.json').exists():
        final=read(directory/'attempt0/result.json')['final_states']
        for selected in final:
            sid=selected['session_id'];source=by_source[sessions[sid]['source_id']]
            ref=unicodedata.normalize('NFKC',source['reference']).lower()
            hyp=unicodedata.normalize('NFKC',selected['text']).lower()
            a=re.findall(r"[a-z0-9']+",ref);b=re.findall(r"[a-z0-9']+",hyp)
            errors=edit_distance(a,b);chars=[x for x in ref if x.isalnum()];out=[x for x in hyp if x.isalnum()]
            per_session[sid].update(WER_errors=errors,WER_reference_words=len(a),
                all_offered_WER_percent=100*errors/len(a) if a else None,
                all_offered_character_error_percent=100*edit_distance(chars,out)/len(chars) if chars else None)
        need(sum(row.get('WER_errors',0) for row in per_session.values())==service['WER_errors'],'per-source quality differs from audited total')
    if revisions:
        for key in next(iter(revisions.values())):metric[key]=sum(row[key] for row in revisions.values())
    metric['longest_actual_visible_progress_gap_seconds']=max(row['longest_actual_visible_progress_gap_seconds'] for row in per_session.values())
    history={}
    if (directory/'attempt0/events.jsonl').exists() and (directory/'attempt0/worker_records.jsonl').exists():
        history=history_digests(lines(directory/'attempt0/events.jsonl'),lines(directory/'attempt0/worker_records.jsonl'))
    state['canonical_history_data_available']=bool(history)
    power=read(directory/'POWER_MEASURED.json');metric.update(cold_launch_to_exit_both_GPU_joules=power['cold_launch_to_exit_both_GPU_joules'],
        cold_launch_to_exit_seconds=power['cold_exit_perf']-power['cold_launch_perf'])
    state.update(status='ACCEPTED_AUDITED_SINGLE_CELL',formal_accepted=True,source_commit=summary['source_commit'])
    pair_contract=select_contract(cfg,cell,sessions)
    if (directory/'attempt0/config.json').exists():
        runtime=read(directory/'attempt0/config.json')
        pair_contract['actual_authority_runtime_sha256']=sha(runtime['authority_runtime'])
    for sid,row in per_session.items():row['canonical_history_sha256']=history.get(sid)
    return state,dict(plan=cell,config=cfg,metric=metric,sessions=per_session,histories=history,pair_contract=pair_contract,
        frontiers={(row['session_id'],row['frontier']):row for row in tables['FRONTIERS']},
        invalidated_sessions={row['session_id'] for row in tables['OBSERVED_INVALIDATIONS']},
        frozen_fault_sessions=fault_sessions,
        cancelled_sessions={row['session_id'] for row in requests})


def select_contract(cfg,cell,sessions):
    return dict(adapter=cfg['adapter'],model=cell.get('model'),rho=cfg['rho'],arrival=cfg['arrival'],repeat=cfg['repeat'],
        selected_manifest_sha256=cfg['selected_manifest_sha256'],fixture_sha256=cfg['fixture_sha256'],
        sessions=[{key:row[key] for key in ['session_id','source_id','duration','offset']} for row in sessions.values()],
        source_manifest_sha256=cfg['source_manifest_sha256'],microbatch=cfg['microbatch'],max_new_tokens=cfg['max_new_tokens'])


def contrast(reference,candidate):
    need(reference['pair_contract']==candidate['pair_contract'],'unmatched pair input/source/model/arrival/load/repeat contract')
    common=set(reference['metric'])&set(candidate['metric']);delta={key:minus(candidate['metric'][key],reference['metric'][key]) for key in common}
    history=set(reference['histories'])|set(candidate['histories'])
    exact=sum(reference['histories'].get(sid)==candidate['histories'].get(sid) for sid in history)
    changed_quality=(delta.get('all_offered_WER_percent') or 0)>0 or (delta.get('all_offered_character_error_percent') or 0)>0
    improvement=(delta.get('all_offered_audio_goodput_2_8') or 0)>0 or (delta.get('dual_audio_fraction') or 0)>0 or (delta.get('other_session_max_gap_seconds') or 0)<0
    point_tradeoff=any((delta.get(key) or 0)>0 for key in ['display_P99','commit_view_P99','other_session_max_gap_seconds']) or (delta.get('dual_audio_fraction') or 0)<0
    coverage_ok=candidate['metric']['final_certified_audio_coverage']>=reference['metric']['final_certified_audio_coverage']
    gate=('OBSERVED_SERVICE_TRADEOFF' if improvement and (changed_quality or point_tradeoff or not coverage_ok) else
          'OBSERVED_PAIRED_SERVICE_BENEFIT_REPLICATION_REQUIRED' if improvement and coverage_ok else
          'NO_POSITIVE_PAIRED_SERVICE_EFFECT')
    return dict(reference_cell=reference['plan']['cell_id'],candidate_cell=candidate['plan']['cell_id'],
        reference_arm=reference['plan']['arm'],candidate_arm=candidate['plan']['arm'],
        paired_block=reference['plan']['paired_block'],delta_candidate_minus_reference=delta,
        matched_canonical_history_sessions=exact,compared_canonical_history_sessions=len(history),
        canonical_histories_equal=(exact==len(history)) if history else None,
        quality_regression_observed=changed_quality,other_endpoint_point_tradeoff=point_tradeoff,service_effect_gate=gate,
        inference_scope='paired measured point; no population superiority inferred from one pair')


def granular_contrasts(reference,candidate):
    """Actual matched sessions/frontiers, not lost-work or policy-error oracles."""
    need(reference['pair_contract']==candidate['pair_contract'],'granular pair contract mismatch')
    source_rows=[];frontier_rows=[]
    frozen_targets=reference['frozen_fault_sessions']|candidate['frozen_fault_sessions']
    # For controlled faults, the group is fixed BEFORE execution by the input
    # fixture. Do not condition an "unaffected" group on post-policy outcomes.
    intervened=frozen_targets or (reference['cancelled_sessions']|candidate['cancelled_sessions'])
    label=dict(reference_cell=reference['plan']['cell_id'],candidate_cell=candidate['plan']['cell_id'],
        paired_block=reference['plan']['paired_block'])
    for sid,left in reference['sessions'].items():
        right=candidate['sessions'][sid];need(left['source_id']==right['source_id'],'session source changed')
        metrics=set(MEASURES)|{'display_deadline_missed_frontiers','commit_deadline_missed_frontiers'}
        delta={key:minus(right.get(key),left.get(key)) for key in metrics}
        source_rows.append(dict(**label,session_id=sid,source_id=left['source_id'],speaker=left['speaker'],
            relation=('frozen-fault-target-session' if frozen_targets else 'cancelled-target-session') if sid in intervened else 'other-session' if intervened else 'no-identified-target',
            reference_visible_gap_seconds=left['longest_actual_visible_progress_gap_seconds'],
            candidate_visible_gap_seconds=right['longest_actual_visible_progress_gap_seconds'],
            delta_candidate_minus_reference=delta,
            canonical_history_equal=reference['histories'].get(sid)==candidate['histories'].get(sid) if sid in reference['histories'] and sid in candidate['histories'] else None))
    need(set(reference['frontiers'])==set(candidate['frontiers']),'paired offered frontier denominator changed')
    for key,left in reference['frontiers'].items():
        right=candidate['frontiers'][key];need(left['audio_seconds']==right['audio_seconds'],'frontier audio weight changed')
        sid,frontier=key
        frontier_rows.append(dict(**label,session_id=sid,source_id=reference['sessions'][sid]['source_id'],frontier=frontier,
            audio_seconds=left['audio_seconds'],reference_dual_credit=left['dual_credit'],candidate_dual_credit=right['dual_credit'],
            outcome='gained' if right['dual_credit'] and not left['dual_credit'] else 'lost' if left['dual_credit'] and not right['dual_credit'] else 'same',
            reference_display_latency=left['display_latency'],candidate_display_latency=right['display_latency'],
            reference_commit_latency=left['commit_view_latency'],candidate_commit_latency=right['commit_view_latency']))
    return source_rows,frontier_rows


def factorial(values):
    need(set(FACTORS)<=set(values),'incomplete 2x2 block')
    output={}
    for metric in MEASURES:
        y=[values[arm].get(metric) for arm in FACTORS]
        if not all(finite(value) for value in y):output[metric]=None;continue
        y00,y01,y10,y11=y
        output[metric]=dict(interaction=y11-y10-y01+y00,retention_when_snapshot=y10-y00,
            retention_when_two_lane=y11-y01,two_lane_without_retention=y01-y00,two_lane_with_retention=y11-y10,
            full_minus_neither=y11-y00,beneficial_interaction_sign=MEASURES[metric])
    return output


def speaker_bootstrap(rows,metric, *, draws=2000,seed=20261028):
    """All repeated deadline windows/runs are inside one speaker cluster."""
    groups=defaultdict(list)
    for row in rows:
        value=row.get(metric)
        if metric in row and row.get('speaker') is not None:groups[row['speaker']].append(value)
    unbounded=[speaker for speaker,values in groups.items() if not all(finite(value) for value in values)]
    if unbounded:
        return dict(independent_speakers=len(groups),observed_rows_including_repeats=sum(map(len,groups.values())),
            missing_or_unbounded_speakers=unbounded,mean=None,lower95=None,upper95=None,
            scope='endpoint unavailable/unbounded in these speakers; no missing-source filtering or finite-only CI')
    means={speaker:statistics.mean(values) for speaker,values in groups.items()}
    if not means:return dict(independent_speakers=0,mean=None,lower95=None,upper95=None)
    values=list(means.values());rng=random.Random(seed)
    samples=sorted(statistics.mean(rng.choices(values,k=len(values))) for _ in range(draws))
    return dict(independent_speakers=len(means),observed_rows_including_repeats=sum(map(len,groups.values())),
        mean=statistics.mean(values),lower95=samples[int(.025*(draws-1))],upper95=samples[int(.975*(draws-1))],
        repeat_counts_by_speaker={speaker:len(values) for speaker,values in groups.items()},
        scope='speaker-cluster descriptive bootstrap; sessions share cohort/run service, not independent GPU deployments')


def aggregate(plan, *, results_root=None):
    cells=planned_cells(plan);coverage=[];accepted={};errors=[]
    for cell in cells:
        try:state,data=load_cell(cell,results_root=results_root)
        except (AssertionError,KeyError,ValueError,OSError) as error:
            state=dict(cell_id=cell['cell_id'],arm=cell['arm'],status='INVALID_OR_INCOMPLETE_ARTIFACTS',formal_accepted=False,error=str(error));data=None
            errors.append(state)
        coverage.append(state)
        if data is not None:accepted[cell['cell_id']]=data
    blocks=defaultdict(dict)
    for cell in cells:
        need(cell['arm'] not in blocks[cell['paired_block']],'duplicate arm inside frozen paired block')
        blocks[cell['paired_block']][cell['arm']]=cell
    pairs=[];effects=[];source_effects=[];standard=[];block_coverage=[]
    for block,arms in blocks.items():
        complete={arm:accepted[cell['cell_id']] for arm,cell in arms.items() if cell['cell_id'] in accepted}
        block_coverage.append(dict(paired_block=block,planned_arms=list(arms),accepted_arms=list(complete),complete=len(complete)==len(arms)))
        if set(FACTORS)<=set(arms):
            if not set(FACTORS)<=set(complete):continue
            ref=complete['R0_S0']
            for arm in FACTORS[1:]:pairs.append(contrast(ref,complete[arm]))
            factors=factorial({arm:complete[arm]['metric'] for arm in FACTORS})
            info={key:ref['plan'][key] for key in ['phase','adapter','rho','arrival','cohort','repeat']}
            effects.append(dict(paired_block=block,**info,effects=factors))
            for sid,row in ref['sessions'].items():
                values={arm:complete[arm]['sessions'][sid] for arm in FACTORS}
                need(len({value['source_id'] for value in values.values()})==1,'2x2 source pairing changed')
                per_source=factorial(values)
                source_effects.append(dict(paired_block=block,**info,speaker=row['speaker'],source_id=row['source_id'],
                    **{metric:value['interaction'] if value else None for metric,value in per_source.items()}))
            if 'STANDARD_FULL' in complete:
                comparison=contrast(complete['R1_S1'],complete['STANDARD_FULL'])
                comparison['role']='author-built complete-composition positive control; same effect is acceptable'
                standard.append(comparison)
        else:
            reference=complete.get('row_complete',complete.get('no_cancel'))
            if reference:
                for arm,value in complete.items():
                    if value is not reference:pairs.append(contrast(reference,value))
    # Additional frozen plans may contain the original pair and strong controls
    # separately. Cross-plan comparisons are permitted only by the full actual
    # input/source/model/arrival/load/repeat contract, never a method name alone.
    controls=defaultdict(list)
    for value in accepted.values():
        if value['plan']['arm'] not in (*FACTORS,'STANDARD_FULL'):controls[sha(value['pair_contract'])].append(value)
    known={(row['reference_cell'],row['candidate_cell']) for row in pairs}
    policy_order={name:index for index,name in enumerate(['row_complete','no_cancel','watchdog','parent','covered','causal'])}
    for group in controls.values():
        group.sort(key=lambda value:(policy_order.get(value['plan']['arm'],99),value['plan']['cell_id']))
        for i,reference in enumerate(group):
            for candidate in group[i+1:]:
                key=(reference['plan']['cell_id'],candidate['plan']['cell_id'])
                if reference['plan']['arm']!=candidate['plan']['arm'] and key not in known:
                    pairs.append(contrast(reference,candidate));known.add(key)
    source_pairs=[];frontier_pairs=[]
    for pair in pairs+standard:
        source_rows,frontier_rows=granular_contrasts(accepted[pair['reference_cell']],accepted[pair['candidate_cell']])
        source_pairs+=source_rows;frontier_pairs+=frontier_rows
        pair['gained_joint_deadline_audio_seconds']=sum(row['audio_seconds'] for row in frontier_rows if row['outcome']=='gained')
        pair['lost_joint_deadline_audio_seconds']=sum(row['audio_seconds'] for row in frontier_rows if row['outcome']=='lost')
        others=[row for row in source_rows if row['relation']=='other-session']
        pair['other_source_visible_gap_improved']=sum(row['candidate_visible_gap_seconds']<row['reference_visible_gap_seconds'] for row in others)
        pair['other_source_visible_gap_worsened']=sum(row['candidate_visible_gap_seconds']>row['reference_visible_gap_seconds'] for row in others)
        pair['other_source_gap_delta_median']=statistics.median(row['candidate_visible_gap_seconds']-row['reference_visible_gap_seconds'] for row in others) if others else None
        other_ids={row['session_id'] for row in others}
        pair['other_source_net_joint_deadline_audio_seconds']=sum((1 if row['outcome']=='gained' else -1 if row['outcome']=='lost' else 0)*row['audio_seconds'] for row in frontier_rows if row['session_id'] in other_ids)
    strata=defaultdict(list)
    for row in source_effects:strata[(row['phase'],row['adapter'],row['rho'],row['arrival'])].append(row)
    bootstrap=[]
    for key,rows in strata.items():
        for metric in MEASURES:
            bootstrap.append(dict(phase=key[0],adapter=key[1],rho=key[2],arrival=key[3],metric=metric,
                **speaker_bootstrap(rows,metric),cohorts=sorted({row['cohort'] for row in rows})))
    independent_sources={row['source_id'] for value in accepted.values() for row in value['sessions'].values()}
    independent_speakers={row['speaker'] for value in accepted.values() for row in value['sessions'].values() if row['speaker'] is not None}
    h3=any(cell['arm'] in FACTORS for cell in cells)
    h3_raw_complete=all(row.get('actual_consumer_revision_data_available') and row.get('canonical_history_data_available') for row in coverage if row['formal_accepted'])
    status='COMPLETE_FROZEN_PLAN_AGGREGATION' if len(accepted)==len(cells) else 'INCOMPLETE_FROZEN_PLAN_NO_COMPLETE_STUDY_CONCLUSION'
    if h3 and len(accepted)==len(cells) and not h3_raw_complete:status='CELL_COVERAGE_COMPLETE_H3_RAW_ANALYSIS_INPUTS_INCOMPLETE'
    summary=dict(status=status,
        planned_cells=len(cells),accepted_cells=len(accepted),coverage_statuses=dict(Counter(row['status'] for row in coverage)),
        observed_independent_source_audio=len(independent_sources),observed_independent_speakers=len(independent_speakers),
        planned_independent_speakers=len({speaker for cohort in plan.get('cohorts',[]) for speaker in cohort.get('speakers',[])}),
        paired_comparisons=len(pairs),complete_2x2_blocks=len(effects),positive_control_comparisons=len(standard),
        performance_conclusion='READ_PAIRED_EFFECTS_AND_UNCERTAINTY' if pairs else 'NO_COMPARATIVE_SERVICE_CONCLUSION',
        performance_effect_criterion='same frozen input/source/model/load/repeat; unchanged protected invariants and accepted obligations; actual all-offered joint-deadline goodput/coverage or other-session stall improves; report quality/energy and any tradeoff; single pair only mechanism/value evidence, no population claim',
        source_independence='repeats, deadline windows, models and arms reuse source clusters; do not count them as new speakers',
        h3_actual_consumer_and_history_inputs_complete=h3_raw_complete if h3 else None,
        canonical_history_rule='report full F/Z/P/text history equality by matched session; do not require equality or hide differences',
        no_arbitrary_effect_threshold=True)
    runs=[dict(cell_id=value['plan']['cell_id'],arm=value['plan']['arm'],**{key:value['plan'][key] for key in
        ['phase','adapter','rho','arrival','cohort','repeat','paired_block']},**value['metric']) for value in accepted.values()]
    registry=defaultdict(list)
    for value in accepted.values():
        for row in value['sessions'].values():registry[row['source_id']].append((value['plan'],row))
    sources=[dict(source_id=source,speaker=entries[0][1]['speaker'],
        cohorts=sorted({entry[0]['cohort'] for entry in entries}),
        models=sorted({entry[0]['adapter'] for entry in entries}),
        repeats=sorted({entry[0]['repeat'] for entry in entries}),
        accepted_cell_reuses=len(entries)) for source,entries in registry.items()]
    history_groups=defaultdict(list)
    for value in accepted.values():
        for row in value['sessions'].values():
            key=(row['source_id'],value['plan']['adapter'],value['plan']['rho'],value['plan']['arrival'],
                 value['pair_contract'].get('actual_authority_runtime_sha256'))
            history_groups[key].append((value['plan']['cell_id'],row.get('canonical_history_sha256')))
    history_rows=[]
    for key,values in history_groups.items():
        members=defaultdict(list)
        for cid,digest in values:members[str(digest)].append(cid)
        history_rows.append(dict(source_id=key[0],adapter=key[1],rho=key[2],arrival=key[3],
            actual_authority_runtime_sha256=key[4],canonical_history_groups=dict(members),
            missing_history_cells=[cid for cid,digest in values if digest is None],
            all_recorded_histories_equal=len(members)==1 and 'None' not in members))
    return summary,dict(COVERAGE=coverage,BLOCK_COVERAGE=block_coverage,SOURCE_REGISTRY=sources,RUNS=runs,
        SOURCE_METRICS=[dict(row,cell_id=value['plan']['cell_id']) for value in accepted.values() for row in value['sessions'].values()],
        PAIRED_EFFECTS=pairs,SOURCE_PAIRED_EFFECTS=source_pairs,FRONTIER_PAIRED_EFFECTS=frontier_pairs,
        FACTORIAL_EFFECTS=effects,SOURCE_FACTORIAL_EFFECTS=source_effects,SPEAKER_BOOTSTRAP=bootstrap,
        CANONICAL_HISTORY_GROUPS=history_rows,STANDARD_POSITIVE_CONTROL=standard)


def write_outputs(directory,summary,tables,plan_path):
    directory.mkdir(parents=True,exist_ok=False)
    (directory/'SUMMARY.json').write_text(json.dumps(dict(summary,plan_path=str(plan_path),plan_sha256=fsha(plan_path)),indent=2,allow_nan=False)+'\n',encoding='utf8')
    record=dict(experiment_id='REVTRACE-SERVICE-AGGREGATION-'+directory.name,
        evidence_type='read-only aggregation of recorded service artifacts; no inference',
        analysis_script=str(Path(__file__).resolve()),analysis_script_sha256=fsha(Path(__file__)),
        execution_source_commits=sorted({row['source_commit'] for row in tables['COVERAGE'] if row.get('source_commit')}),
        environment=dict(python=sys.version,platform=platform.platform()),
        frozen_plan_sha256=fsha(plan_path),inputs=INPUT_FILES,
        raw_result_paths=[row.get('path') for row in tables['COVERAGE'] if row.get('path')],
        aggregate_summary_path=str((directory/'SUMMARY.json').resolve()),
        gate_decision=summary['status'],new_GPU_calls=0)
    (directory/'ANALYSIS_RECORD.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for name,rows in tables.items():
        (directory/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n',encoding='utf8')
        if rows:
            flat=[{key:json.dumps(value,sort_keys=True) if isinstance(value,(dict,list)) else value for key,value in row.items()} for row in rows]
            with (directory/(name+'.csv')).open('w',newline='',encoding='utf8') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(key for row in flat for key in row)))
                writer.writeheader();writer.writerows(flat)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--additional-plan',type=Path,action='append',default=[])
    parser.add_argument('--results-root',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    plan=read(args.plan)
    if args.additional_plan:
        plan=dict(plan,cells=planned_cells(plan))
        for path in args.additional_plan:plan['cells']+=planned_cells(read(path))
    summary,tables=aggregate(plan,results_root=args.results_root)
    write_outputs(args.output,summary,tables,args.plan)
    print(json.dumps(summary,allow_nan=False))


if __name__=='__main__':main()
