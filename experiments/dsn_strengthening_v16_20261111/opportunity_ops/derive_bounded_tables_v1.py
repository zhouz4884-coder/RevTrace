"""Document arithmetic over closed OPV1 outputs only; not a new experiment.

No original NN raw, active RESOURCE8 data, model, parser or test is read/run.
"""
from pathlib import Path
from collections import defaultdict
import hashlib,json
H=Path(__file__).resolve().parent;D=H/'RESULTS_V1'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=json.loads((D/'ALL24_CELL_TABLE.json').read_bytes());assert len(data)==24
inputs={str(D/'ALL24_CELL_TABLE.json'):sha(D/'ALL24_CELL_TABLE.json')}
work=[]
for p in sorted((D/'cells').glob('*/ACTUAL_PAID_WORK.json')):
 inputs[str(p)]=sha(p)
 for row in json.loads(p.read_bytes()):work.append(dict(cell_id=p.parent.name,**row))
groups=defaultdict(list)
for row in data:groups[row['strategy']].append(row)
rows=[]
for arm,cells in sorted(groups.items()):
 own=[j for j in work if j['cell_id'] in {c['cell_id'] for c in cells}]
 completed=[j for j in own if j['worker_wall_seconds'] is not None and j['observed_infer_wall_seconds'] is not None]
 outside=sum(j['worker_wall_seconds']-j['observed_infer_wall_seconds'] for j in completed)
 def count(name):return sum(c['opportunities'].get(name,0) for c in cells)
 def sup(name):return sum(c['consumer_support'].get(name,0) for c in cells)
 row=dict(strategy=arm,cells=len(cells),configured_offered_audio_s=sum(c['configured_offered_audio_seconds'] for c in cells),
  deadline_credit_audio_s=sum(c['primary']['dual_deadline_audio_credit_seconds'] for c in cells),
  raw_supported_credit_audio_s=sum(c['posterior_whole_text_support']['raw']['original_credit_supported_seconds'] for c in cells),
  whole_trial_D2_C8_passes=sum(c['primary']['complete_coverage_and_original_quantile_pass'] for c in cells),
  worker_wall_s_observed=count('observed_worker_wall_seconds'),infer_wall_s_observed=count('observed_infer_wall_seconds'),
  worker_timer_missing_jobs=count('worker_interval_missing_jobs'),infer_timer_missing_jobs=count('infer_interval_missing_jobs'),
  native_active_confirmed_jobs=count('unique_model_active_compatible_confirmation_jobs'),active_through_parent_interval_jobs=count('unique_model_active_guaranteed_interval_jobs'),
  ancestor_only_treatment_disagreement_jobs=count('unique_ancestor_disagreement_jobs'),ordinary_direct_both_predicates_retain_jobs=count('unique_ordinary_direct_both_retain_jobs'),
  actual_recorded_promotions=count('recorded_promotion_events'),actual_selected_promoted_jobs=sum(c['job_accounting']['selected_promoted_jobs'] for c in cells),
  Owner_admitted_ready_hits=count('actual_owner_ready_reuse'),before_C_exits=count('actual_before_C_exits'),
  semantic_known_invalid_or_covered_exits=count('known_invalid_or_covered_before_C_exits'),UIR_suppressed_hint_observations=count('UIR_suppressed_hint_observations'),
  late_full_refusals=count('late_full_result_refusals'),actual_same_input_target_reissues=count('same_complete_input_target_redispatches_all_owner_epochs'),
  compatible_ahead_Consumer_applications=sup('compatible_ahead_applications'),compatible_ahead_preserved=sup('compatible_ahead_preserved'),
  avoidable_supported_view_losses=sup('avoidable_supported_view_losses'),necessary_incompatible_withdrawals=sup('necessary_incompatible_withdrawals'),
  verified_energy_cells=sum(c['energy_ownership']['verifiable'] for c in cells),
  both_board_service_to_drain_J=sum(c['verified_both_board_energy_J'] for c in cells),
  completed_jobs_with_both_nested_timers=len(completed),completed_worker_s=sum(j['worker_wall_seconds'] for j in completed),
  charged_worker_time_outside_original_infer_s=outside,
  outside_infer_fraction_of_completed_worker=outside/sum(j['worker_wall_seconds'] for j in completed) if completed else None,
  outside_infer_scope='Difference of paired nested durations; upper bound only on serialization component INSIDE charged worker interval. Includes required restore/insert/export; excludes transport,Owner/WAL/Consumer and callback costs inside infer. Not measured avoidable tax or whole continuous-baseline speed bound.')
 rows.append(row)
source_UIR=[]
for sid in sorted({c['source_id'] for c in data}):
 by={arm:[c for c in data if c['source_id']==sid and c['strategy']==arm] for arm in ('fullcall','uir')}
 source_UIR.append(dict(source_id=sid,
  fullcall_before_C_exits=sum(c['opportunities'].get('actual_before_C_exits',0) for c in by['fullcall']),
  UIR_suppressed=sum(c['opportunities'].get('UIR_suppressed_hint_observations',0) for c in by['uir']),
  fullcall_credit_minus_UIR_s=sum(c['primary']['dual_deadline_audio_credit_seconds'] for c in by['fullcall'])-sum(c['primary']['dual_deadline_audio_credit_seconds'] for c in by['uir']),
  fullcall_worker_minus_UIR_s=sum(c['opportunities']['observed_worker_wall_seconds'] for c in by['fullcall'])-sum(c['opportunities']['observed_worker_wall_seconds'] for c in by['uir']),
  fullcall_J_minus_UIR_J=sum(c['verified_both_board_energy_J'] for c in by['fullcall'])-sum(c['verified_both_board_energy_J'] for c in by['uir'])))
out=H/'BOUNDED_INTERPRETATION_TABLES_DERIVED_V1.json'
result=dict(record_type='DERIVED_FROM_FROZEN_OPPORTUNITY_OUTPUT_NOT_NEW_RUN',source_script_sha256=sha(__file__),inputs=inputs,
 parent_experiment='REVTRACE-V16-PILOT-OPPORTUNITY-AUDIT-20261111-V1',parent_source='0d54630951dff6e1a423a1652704ee39eea0b8ce',
 per_arm=rows,per_source_UIR_actual_comparison=source_UIR,
 current_NN_ctor_nofault_pre_post_subphase_data='not available in OPV1; separate completed new-NN profiler result not supplied. Do not reuse historical4f figures.',
 new_raw_scans=0,new_tests=0,new_model_runs=0)
with out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
print(json.dumps(dict(output=str(out),per_arm=rows,per_source_UIR=source_UIR),ensure_ascii=False))
