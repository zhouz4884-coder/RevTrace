"""Comprehensive fixed24 output; opportunity absence is never a technical error."""
from collections import defaultdict
import csv,json,traceback
from pathlib import Path
from trial_audit import audit_cell,read,dump,sha

ARMS=('conservative','dependency_versioned','ready_only','fullcall','uir','safe_versioned')
PLAN_SHA='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6'

def presence(rows,sources,arms,metric):
    result=[]
    for source in sources:
        chosen=[r for r in rows if r['source_id']==source['source_id'] and r['strategy'] in arms]
        complete=all(r['status']=='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS' for r in chosen)
        count=sum(r.get('opportunities',{}).get(metric,0) for r in chosen)
        unknown=sum(r.get('opportunities',{}).get('confirmed_input_worker_active_infer_timer_missing_events',0)+r.get('opportunities',{}).get('confirmed_input_missing_execution_interval_events',0) for r in chosen) if metric=='unique_model_active_compatible_confirmation_jobs' else 0
        result.append(dict(source_id=source['source_id'],speaker_id=source['speaker_id'],
            arms=list(arms),actual_events_or_jobs=count if complete else None,
            minimum_one_present=(True if count>=1 else None if unknown else False) if complete else None,
            unresolved_execution_interval_events=unknown,
            basis='actual cells / actual-state predicates only; no schedule replay'))
    return dict(per_speaker=result,all_speakers_minimum_one=(all(r['minimum_one_present'] is True for r in result) if all(r['minimum_one_present'] is not None for r in result) else None),
                interpretation='Minimum presence only, never statistical power, success guarantee or a reason to delete a null')

def analyze(cfg,out):
    plan=read(cfg['pilot_plan']);assert sha(cfg['pilot_plan'])==PLAN_SHA
    from confirmation_common import reference_binding
    reference_binding(plan['reference_receipt']['path'],plan['selection_receipt']['path'],plan['sources'],plan['driver']['source_commit'])
    cells=plan['cells'];sources=plan['sources']
    assert len(cells)==24 and len(sources)==2 and {c['strategy'] for c in cells}==set(ARMS)
    assert len({c['cell_id'] for c in cells})==24 and [c['position'] for c in cells]==list(range(24))
    for s in sources:
        assert {(c['strategy'],c['repeat']) for c in cells if c['source_id']==s['source_id']}=={(a,r) for a in ARMS for r in (0,1)}
    rows=[]
    for cell in cells:
        if cfg.get('idle_guard_callable'):cfg['idle_guard_callable']()
        frozen=read(cell['config']);assert sha(cell['config'])==cell['config_sha256']
        offered=sum(s['frames']/16000 for s in frozen['settings']['sources'])
        gate_path=Path(cell['out'])/'GATE.json'
        basic=dict(cell_id=cell['cell_id'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],
            strategy=cell['strategy'],repeat=cell['repeat'],estimand_role=cell['estimand_role'],configured_offered_audio_seconds=offered)
        if not gate_path.exists():
            rows.append(dict(basic,status='NOT_COMPLETED_OR_NOT_EXECUTED_PRESERVED',observed_metrics=None));continue
        gate=read(gate_path)
        if gate.get('status')!='PASS_ACTUAL_RESILIENT_NATIVE_EXECUTION_AND_COMPLETE_TASK':
            rows.append(dict(basic,status='ORIGINAL_TECHNICAL_FAILURE_PRESERVED',original_gate=gate,observed_metrics=None));continue
        try:rows.append(audit_cell(cell,frozen,out))
        except Exception:rows.append(dict(basic,status='FAIL_AUDIT_BINDING_PRESERVED',failure=traceback.format_exc(),observed_metrics=None))
    pairs=[]
    for source in sources:
        for repeat in (0,1):
            by={r['strategy']:r for r in rows if r['source_id']==source['source_id'] and r['repeat']==repeat}
            for control in ARMS:
                if control=='fullcall':continue
                a,b=by['fullcall'],by[control];complete=all(r['status']=='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS' for r in (a,b))
                pair=dict(source_id=source['source_id'],speaker_id=source['speaker_id'],repeat=repeat,
                    candidate='fullcall',control=control,control_role='auxiliary' if control=='safe_versioned' else 'main',
                    configured_offered_audio_seconds=a['configured_offered_audio_seconds'],status='COMPLETE_ACTUAL_STRATEGY_CONTRAST' if complete else 'MISSING_OR_FAILED_ACTUAL_PAIR_PRESERVED',
                    additive_check_contribution_identified=False)
                if complete:
                    if a['configured_offered_audio_seconds']!=b['configured_offered_audio_seconds']:raise ValueError('paired all-offered denominator differs')
                    pair.update(actual_credit_difference_audio_seconds=a['primary']['dual_deadline_audio_credit_seconds']-b['primary']['dual_deadline_audio_credit_seconds'],
                        actual_raw_supported_credit_difference_audio_seconds=a['posterior_whole_text_support']['raw']['original_credit_supported_seconds']-b['posterior_whole_text_support']['raw']['original_credit_supported_seconds'],
                        observed_worker_wall_difference_seconds=a['opportunities'].get('observed_worker_wall_seconds',0)-b['opportunities'].get('observed_worker_wall_seconds',0),
                        verified_both_board_energy_difference_J=(a['verified_both_board_energy_J']-b['verified_both_board_energy_J']) if a['verified_both_board_energy_J'] is not None and b['verified_both_board_energy_J'] is not None else None)
                    missing=a['opportunities'].get('worker_interval_missing_jobs',0)+b['opportunities'].get('worker_interval_missing_jobs',0)
                    pair['missing_worker_interval_jobs_in_pair']=missing
                    pair['verified_total_worker_wall_difference_seconds']=pair['observed_worker_wall_difference_seconds'] if missing==0 else None
                pairs.append(pair)
    activation=dict(inflight_fullcall=presence(rows,sources,('fullcall',),'unique_model_active_compatible_confirmation_jobs'),
        dependency_disagreement_fullcall_basis=presence(rows,sources,('fullcall',),'unique_ancestor_disagreement_jobs'),
        dependency_disagreement_actual_contrast_union_basis=presence(rows,sources,('fullcall','dependency_versioned'),'unique_ancestor_disagreement_jobs'),
        early_exit_fullcall=presence(rows,sources,('fullcall',),'known_invalid_or_covered_before_C_exits'),
        ready_reuse_positive_minimum=None,SUP_independent_increment_identified=False,
        policy='Separate technical conformance from opportunity presence. Zero ready reuse, zero disagreement, ties, >2percent drift remain data.')
    dump(out/'ALL24_CELL_TABLE.json',rows);dump(out/'ACTUAL_PAIRED_STRATEGY_CONTRASTS.json',pairs);dump(out/'ACTIVATION_PRESENCE_NOT_POWER.json',activation)
    fields=('cell_id','source_id','speaker_id','strategy','repeat','estimand_role','status','configured_offered_audio_seconds',
        'credit_audio_seconds','raw_supported_credit_audio_seconds','actual_canonical_installs','unique_model_active_confirmations',
        'unique_ancestor_disagreements','later_legally_applied_disagreements','ordinary_direct_both_predicates_keep',
        'Owner_ready_reuse','actual_before_C_exits','UIR_suppressed_hints','late_full_refusals','redispatches',
        'observed_worker_wall_seconds','observed_infer_wall_seconds','missing_infer_timers','compatible_nonempty_Consumer_ahead',
        'avoidable_supported_view_losses','necessary_incompatible_withdrawals','verified_both_board_energy_J')
    with (out/'ALL24_OPPORTUNITY_TABLE.csv').open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            good=r['status']=='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS';o=r.get('opportunities',{});s=r.get('consumer_support',{})
            row={k:r[k] for k in fields[:8]}
            metrics=dict(credit_audio_seconds=r.get('primary',{}).get('dual_deadline_audio_credit_seconds'),
                raw_supported_credit_audio_seconds=r.get('posterior_whole_text_support',{}).get('raw',{}).get('original_credit_supported_seconds'),
                actual_canonical_installs=o.get('actual_canonical_install_events',0),unique_model_active_confirmations=o.get('unique_model_active_compatible_confirmation_jobs',0),
                unique_ancestor_disagreements=o.get('unique_ancestor_disagreement_jobs',0),later_legally_applied_disagreements=o.get('ancestor_disagreement_later_legally_applied_jobs',0),
                ordinary_direct_both_predicates_keep=o.get('unique_ordinary_direct_both_retain_jobs',0),Owner_ready_reuse=o.get('actual_owner_ready_reuse',0),
                actual_before_C_exits=o.get('actual_before_C_exits',0),UIR_suppressed_hints=o.get('UIR_suppressed_hint_observations',0),late_full_refusals=o.get('late_full_result_refusals',0),
                redispatches=o.get('same_complete_input_target_redispatches_all_owner_epochs',0),observed_worker_wall_seconds=o.get('observed_worker_wall_seconds',0),
                observed_infer_wall_seconds=o.get('observed_infer_wall_seconds',0),missing_infer_timers=o.get('infer_interval_missing_jobs',0),
                compatible_nonempty_Consumer_ahead=s.get('compatible_ahead_applications',0),avoidable_supported_view_losses=s.get('avoidable_supported_view_losses',0),
                necessary_incompatible_withdrawals=s.get('necessary_incompatible_withdrawals',0),verified_both_board_energy_J=r.get('verified_both_board_energy_J'))
            row.update(metrics if good else {k:None for k in metrics});writer.writerow(row)
    good=sum(r['status']=='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS' for r in rows)
    return dict(status='PASS_COMPLETE_ALL24_OPPORTUNITY_BINDINGS' if good==24 else 'PARTIAL_OR_FAILED_PILOT_OPPORTUNITY_SCOPE_PRESERVED',
        expected_cells=24,audited_complete_cells=good,all_preselected_cells_retained=len(rows)==24,speaker_clusters=2,
        configured_all_offered_audio_seconds=sum(r['configured_offered_audio_seconds'] for r in rows),
        activation=activation,independent_SUP_effect_identified=False,unique_additive_five_arm_check_decomposition_identified=False,
        shadow_alternative_schedule_runs=0,new_model_calls=0,interpretation='Actual strategy audio-second contrasts and separate non-causal predicate profiles; presence is not power. Future work only under frozen v5 rules.')
