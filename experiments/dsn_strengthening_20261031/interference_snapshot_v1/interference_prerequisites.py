"""No automatic launch before the root's existing scopes actually completed."""
from common import need,read,sha,disk_path,FINAL
from buffer_reaudit_prerequisite import validate_buffer_reaudit
from interference_contract import ORDER

def receipt(item):
    path=disk_path(item['path']);need(sha(path)==item['sha256'],'prerequisite receipt bytes changed');return read(path)

def useful_resident_scope(resident):
    """Root's pre-probe acceptance: preserve actual 7/8, require useful real work.

    Scope completion and exact task/clock/PID success are separate from every
    request passing D2/C8. Never relabel the measured request misses as 8/8.
    """
    need(resident['status']=='PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE' and resident['completed_cells']==resident['planned_cells']==4 and len(resident['cells'])==4,'resident4 not actually complete')
    by={(r['arm'],r['repeat']):r for r in resident['cells']};need(set(by)=={(arm,rep) for arm in ('conservative','fullcall') for rep in (0,1)},'resident4 strategy/repeat partition differs')
    for result in by.values():
        summary=result['summary'];integrity=summary['integrity'];requests=summary['per_request'];pids=result['worker_PIDs_continuous']
        need(summary['gate']=='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE' and summary['actual_NN_source_commit']==FINAL and integrity['original_reference']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE' and integrity['all_original_obligations_eventually_processed'] is True,'resident actual task/reference failed')
        need(integrity['request_clock']['status']=='PASS_CLOSED_LOOP_ACTUAL_EOS_AND_ALL_ORIGINAL_REQUEST_OFFERS' and integrity['request_clock']['requests']==4 and integrity['request_clock']['EOS_included'] is True,'resident actual request clock failed')
        need(len(requests)==4 and {r['source_id'] for r in requests}==set(ORDER) and all(q['primary']['missing_D_frontiers']==q['primary']['missing_C_frontiers']==0 for q in requests),'resident source partition or original obligations incomplete')
        need(len(set(pids))==len(pids)==2 and set(result['per_request_executing_PIDs'])==set(ORDER) and all(v and set(v)<=set(pids) for v in result['per_request_executing_PIDs'].values()),'resident actual continuous model PID proof missing')
    decisions=[]
    for rep in (0,1):
        full=by[('fullcall',rep)]['summary'];control=by[('conservative',rep)]['summary'];f=full['primary'];c=control['primary'];gain=f['dual_deadline_audio_credit_seconds']-c['dual_deadline_audio_credit_seconds'];df=f['primary_linear_all_offered_D99'];dc=c['primary_linear_all_offered_D99']
        need(gain>=1. or (df is not None and dc is not None and dc>0 and df<=.75*dc),'resident measured strong E2E opportunity absent')
        decisions.append(dict(repeat=rep,Fullcall_original_request_gate_passes=sum(q['primary']['complete_coverage_and_original_quantile_pass'] for q in full['per_request']),Conservative_original_request_gate_passes=sum(q['primary']['complete_coverage_and_original_quantile_pass'] for q in control['per_request']),requests_per_arm=4,actual_credit_gain_audio_seconds=gain))
    return dict(status='PASS_COMPLETE_EXACT_RESIDENT_SCOPE_WITH_MEASURED_E2E_OPPORTUNITY',per_repeat=decisions,all_request_D2C8_success_required=False,actual_misses_retained=True,rule_change_before_any_double_client_probe=True)

def validate_prior_scopes(prior):
    paired=receipt(prior['paired32_summary']);need(paired['status']=='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT' and paired['completed_cells']==paired['planned_cells']==32,'paired32 not actually complete')
    resident=useful_resident_scope(receipt(prior['resident4_summary']))
    need('buffer4_reaudit' in prior and 'buffer4_gates' not in prior,'requires b867 zero-NN wrapper receipts; original4eb FAIL gates must never be relabelled PASS')
    buffer=validate_buffer_reaudit(prior['buffer4_reaudit'])
    return dict(status='PASS_EXISTING_PAIRED32_USEFUL_RESIDENT4_AND_BUFFER4_POSTHOC_MECHANISMS',resident_scope_prerequisite=resident,buffer_mechanism_prerequisite=buffer,receipts=prior)
