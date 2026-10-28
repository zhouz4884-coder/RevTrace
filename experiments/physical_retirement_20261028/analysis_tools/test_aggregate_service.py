"""Synthetic fixture tests for aggregation semantics; no research measurements."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import aggregate_service as ag


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def minimal_cell(root,arm, *, repeat=0):
    directory=root/f'{arm}-r{repeat}'
    retain='yes' if arm in ('R1_S0','R1_S1','STANDARD_FULL') else 'no'
    consumer='two_lane' if arm in ('R0_S1','R1_S1','STANDARD_FULL') else 'checked_snapshot'
    method='standard_fair' if arm=='STANDARD_FULL' else 'dgft_original'
    plan=dict(cell_id=directory.name,out='/remote/'+directory.name,arm=arm,adapter='qwen',model='Qwen',
        rho=1,arrival='sync',repeat=repeat,method=method,sessions=1,policy='row_complete',retain=retain,
        confirmation_consumer=consumer,phase='primary',cohort='A',paired_block=f'A-r{repeat}')
    cfg=dict(adapter='qwen',rho=1,arrival='sync',repeat=repeat,method=method,sessions=1,policy='row_complete',
        retain_private_prefix=retain,confirmation_consumer=consumer,display_slo_seconds=2.,commit_slo_seconds=8.,
        selected_manifest_sha256='same-inputs',fixture_sha256=None,source_manifest_sha256='same-source',microbatch=16,max_new_tokens=256)
    service=dict(unauthorized_admissions=0,stale_publications=0,root_incompatible_actual_views=0,
        certified_only_violations=0,whole_offered_frontiers=2,whole_run_dual_P99_pass=True,
        display_P99=1.,commit_view_P99=2.,original_episode_wall_seconds=5.,
        all_offered_audio_goodput_2_8=.4,final_certified_audio_coverage=1.,
        all_offered_WER_percent=0.,all_offered_character_error_percent=0.,WER_errors=0,
        GPU_joules=10.,GPU_J_per_offered_audio_second=5.)
    lifecycle=dict(complete_rows=2,cancelled_rows=0,physical_model_seconds=1.,physical_lease_seconds=2.,
        post_invalidation_model_seconds=0.,post_invalidation_lease_seconds=0.)
    independent=dict(status=ag.SAFE_AUDIT,service=service,lifecycle=lifecycle,accepted_unfulfilled_samples=0)
    summary=dict(status=ag.SAFE_STATUS,source_commit='a'*40,config=cfg,independent_summary=independent)
    put(directory/'SUMMARY.json',summary)
    put(directory/'FREEZE.json',dict(code_commit='a'*40,frozen_config=cfg))
    put(directory/'RUN_RECORD.json',dict(code_commit='a'*40,frozen_config_sha256=ag.fsha(directory/'FREEZE.json')))
    put(directory/'GATE.json',dict(gate='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT'))
    put(directory/'audit/SUMMARY.json',independent)
    put(directory/'audit/FRONTIERS.json',[dict(session_id=0,frontier=f,audio_seconds=1.,display_latency=1.,commit_view_latency=2.,dual_credit=True) for f in (16000,32000)])
    put(directory/'audit/SESSIONS.json',[dict(session_id=0,accepted_samples=32000,actual_committed_samples=32000,
        longest_actual_visible_progress_gap_seconds=1.)])
    for name in ['REQUESTS','BATCHES','OBSERVED_INVALIDATIONS','INTERFERENCE']:put(directory/f'audit/{name}.json',[])
    put(directory/'attempt0/sessions.json',[dict(session_id=0,source_id='s0',duration=2.,offset=0.)])
    put(directory/'manifest.json',dict(sessions=[dict(source_id='s0',speaker='speaker0',reference='hello')]))
    put(directory/'episode.json',dict(origin_perf=100.))
    put(directory/'POWER_MEASURED.json',dict(cold_launch_to_exit_both_GPU_joules=20.,cold_launch_perf=90.,cold_exit_perf=105.))
    put(directory/'attempt0/result.json',dict(final_states=[dict(session_id=0,text='hello')]))
    commits=[dict(kind='commit',session_id=0,job_id='a',version=1,audio_start_sample=0,audio_end_sample=32000,
        segment_tokens=[1],next_prompt_tokens=[1])]
    (directory/'attempt0/events.jsonl').write_text('\n'.join(map(json.dumps,commits))+'\n')
    (directory/'attempt0/worker_records.jsonl').write_text(json.dumps(dict(job=dict(job_id='a',role='authority'),
        result=dict(token_ids=[1],state_tokens=[1],text='hello')))+'\n')
    views=[dict(session_id=0,observed_perf=102.,valid_visible_frontier=32000,certified_frontier=32000,
        source_kind='canonical-display',visible_text='hello')]
    (directory/'attempt0/consumer.jsonl').write_text('\n'.join(map(json.dumps,views))+'\n')
    return plan


def test_raw_adjacent_rollbacks_and_nested_deficit_area_do_not_double_count():
    rows=[dict(session_id=0,observed_perf=float(i),valid_visible_frontier=f,certified_frontier=0,
        source_kind='canonical-display' if i==1 else 'display',visible_text='a'*f,
        tentative_invalidated=i==2) for i,f in enumerate([100,80,50,90,100])]
    result=ag.visible_revisions(rows,end_perf=5.,sample_rate=1)[0]
    assert result['audio_rollback_events']==2 and result['audio_rollback_seconds']==50.
    assert result['rollback_area_audio_seconds_x_wall_seconds']==80.
    assert result['canonical_triggered_rollback_events']==1
    assert result['explicit_tentative_invalidated_rollback_events']==1


def test_unrecovered_last_drop_is_charged_to_observed_service_end():
    rows=[dict(session_id=0,observed_perf=t,valid_visible_frontier=f) for t,f in [(1.,100),(2.,50)]]
    assert ag.visible_revisions(rows,end_perf=5.,sample_rate=1)[0]['rollback_area_audio_seconds_x_wall_seconds']==150.


def test_history_excludes_clocks_ids_and_global_interleaving_but_includes_text():
    event=dict(kind='commit',session_id=0,job_id='one',version=1,audio_start_sample=0,audio_end_sample=10,
        segment_tokens=[3],next_prompt_tokens=[4],time=1.)
    record=dict(job=dict(job_id='one',role='authority'),result=dict(token_ids=[3],state_tokens=[4],text='chosen'))
    first=ag.history_digests([event],[record])
    event['time']=900.;event['job_id']='two';record['job']['job_id']='two'
    assert ag.history_digests([event],[record])==first
    record['result']['text']='changed'
    assert ag.history_digests([event],[record])!=first


def test_missing_frontiers_remain_misses_and_cannot_be_removed_from_denominator():
    rows=[dict(session_id=0,frontier=1,audio_seconds=1.,display_latency=1.,commit_view_latency=2.,dual_credit=True),
          dict(session_id=0,frontier=2,audio_seconds=1.,display_latency=None,commit_view_latency=None,dual_credit=False)]
    result=ag.frontier_metrics(rows,2.)
    assert result['dual_audio_fraction']==.5 and result['offered_frontiers']==2
    with pytest.raises(AssertionError,match='denominator'):ag.frontier_metrics(rows[:1],2.)


def test_factorial_interaction_and_full_standard_same_effect_are_supported(tmp_path):
    cells=[minimal_cell(tmp_path,arm) for arm in (*ag.FACTORS,'STANDARD_FULL')]
    plan=dict(cells=cells,cohorts=[dict(cohort='A',source_ids=['s0'],speakers=['speaker0'])])
    summary,tables=ag.aggregate(plan,results_root=tmp_path)
    assert summary['accepted_cells']==5 and summary['complete_2x2_blocks']==1
    assert summary['observed_independent_speakers']==1
    assert tables['STANDARD_POSITIVE_CONTROL'][0]['canonical_histories_equal']
    assert tables['STANDARD_POSITIVE_CONTROL'][0]['delta_candidate_minus_reference']['dual_audio_fraction']==0
    values={arm:dict(audio_rollback_events=value) for arm,value in zip(ag.FACTORS,[100,40,120,0])}
    assert ag.factorial(values)['audio_rollback_events']['interaction']==-60


def test_speaker_bootstrap_does_not_count_repeat_or_deadline_windows_as_sources():
    rows=[dict(speaker='one',x=value) for value in (1.,2.,3.)]+[dict(speaker='two',x=2.)]
    result=ag.speaker_bootstrap(rows,'x',draws=100)
    assert result['independent_speakers']==2 and result['observed_rows_including_repeats']==4
    assert result['mean']==2.


def test_unbounded_speaker_endpoint_is_not_silently_filtered_from_interval():
    result=ag.speaker_bootstrap([dict(speaker='one',x=1.),dict(speaker='two',x=None)],'x',draws=100)
    assert result['independent_speakers']==2 and result['mean'] is None
    assert result['missing_or_unbounded_speakers']==['two']


def test_other_session_group_uses_frozen_targets_not_post_policy_invalidation(tmp_path):
    plan=minimal_cell(tmp_path,'R0_S0');cell=ag.planned_cells(dict(cells=[plan]))[0]
    _,data=ag.load_cell(cell,results_root=tmp_path)
    data['frozen_fault_sessions']={1};data['invalidated_sessions']={0,1}
    candidate=copy.deepcopy(data)
    rows,_=ag.granular_contrasts(data,candidate)
    assert rows[0]['session_id']==0 and rows[0]['relation']=='other-session'


def test_missing_or_failed_cell_cannot_complete_a_pair_or_plan(tmp_path):
    one=minimal_cell(tmp_path,'R0_S0');two=copy.deepcopy(one);two.update(cell_id='missing',out='/remote/missing',arm='R1_S1')
    summary,tables=ag.aggregate(dict(cells=[one,two]),results_root=tmp_path)
    assert summary['accepted_cells']==1 and summary['performance_conclusion']=='NO_COMPARATIVE_SERVICE_CONCLUSION'
    assert summary['status'].startswith('INCOMPLETE')
    assert any(row['status']=='MISSING' for row in tables['COVERAGE'])
    put(tmp_path/one['cell_id']/'STOP.json',dict(error='audit failed after rc0'))
    summary,tables=ag.aggregate(dict(cells=[one]),results_root=tmp_path)
    assert summary['accepted_cells']==0
    assert tables['COVERAGE'][0]['status']=='FAILED_DEFERRED_OR_NONFINAL'


def test_source_load_repeat_contract_must_match_before_comparison(tmp_path):
    plan=minimal_cell(tmp_path,'R0_S0');cell=ag.planned_cells(dict(cells=[plan]))[0]
    _,data=ag.load_cell(cell,results_root=tmp_path)
    other=copy.deepcopy(data);other['pair_contract']['rho']=3
    with pytest.raises(AssertionError,match='unmatched pair'):ag.contrast(data,other)


def test_h3_revision_input_missing_cannot_be_called_complete_analysis(tmp_path):
    cells=[minimal_cell(tmp_path,arm) for arm in ag.FACTORS]
    for cell in cells:(tmp_path/cell['cell_id']/'attempt0/consumer.jsonl').unlink()
    summary,_=ag.aggregate(dict(cells=cells),results_root=tmp_path)
    assert summary['accepted_cells']==4
    assert summary['status']=='CELL_COVERAGE_COMPLETE_H3_RAW_ANALYSIS_INPUTS_INCOMPLETE'


def test_plan_change_or_repaired_audit_does_not_relabel_failed_original(tmp_path):
    plan=minimal_cell(tmp_path,'R0_S0');cell=ag.planned_cells(dict(cells=[plan]))[0]
    cell['rho']=3
    with pytest.raises(AssertionError,match='differs from frozen plan'):ag.load_cell(cell,results_root=tmp_path)
    cell['rho']=1
    path=tmp_path/cell['cell_id']/'audit/SUMMARY.json';changed=ag.read(path);changed['lifecycle']['complete_rows']=999;put(path,changed)
    with pytest.raises(AssertionError,match='repaired audit'):ag.load_cell(cell,results_root=tmp_path)
