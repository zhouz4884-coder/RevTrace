"""Independent stdlib-only recount of retained fixed-input GPU operator facts.

Never imports the experiment's gate, worker, actuator, or policy implementation.
No model, CUDA, tensor runtime, or SSH connection is created by this recount.
"""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE/'raw'
OUTPUT_KEYS = ('token_ids','state_tokens','text','terminated_by_eos','hit_token_limit')
NEURAL_KEYS = ('source_id','language','prompt_tokens','fault_actual_prompt_tokens','chunk_id',
              'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256')
TENSOR_KEYS = ('input_ids','attention_mask','unpadded_input_ids','batch_tensors','row_features',
               'dtype','batch_rows','prompt_width','max_new_tokens','eos_token_ids')
BIND_INPUT_KEYS = ('session_id','source_id','role','parent','prompt_tokens','chunk_id',
                  'audio_start_sample','audio_end_sample','prefix_audio_sha256',
                  'interval_audio_sha256','fault_actual_prompt_tokens')
CANCEL_KEYS = {'binding','request_id','reason','requested_perf','acknowledged_perf',
               'emitted_perf','decoded_tokens','terminal_digest'}


def read(path):return json.loads(path.read_text(encoding='utf8'))
def lines(path):return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line]
def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def file_sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def token_sha(value):return hashlib.sha256(','.join(map(str,value)).encode()).hexdigest()
def select(value,keys):return {key:value[key] for key in keys if key in value}
def check(condition,message):
    if not condition:raise AssertionError(message)


def same(a,b,message):check(a==b,message)


def validate_binding(job,binding):
    same(binding,job['_delivery']['binding'],'immutable binding disagreement')
    delivery=job['_delivery']
    same((binding['worker'],binding['worker_incarnation'],binding['batch_id']),
         (delivery['worker'],delivery['incarnation'],delivery['batch_id']),'worker incarnation/batch mismatch')
    for key in ('job_id','session_id','role','parent','contract_epoch','contract_digest',
                'runtime_digest','audio_start_sample','audio_end_sample','interval_audio_sha256'):
        same(binding[key],job[key],'binding/job mismatch: '+key)
    same(binding['input_identity'],sha({key:job.get(key) for key in BIND_INPUT_KEYS}),'input identity changed')


def joules(power,lo,hi):
    check(power[0]['observed_perf']<=lo<=hi<=power[-1]['observed_perf'],'power samples do not bracket interval')
    result={str(gpu):0.0 for gpu in (0,1)}
    covered=0.0
    for a,b in zip(power,power[1:]):
        x,y=max(lo,a['observed_perf']),min(hi,b['observed_perf'])
        if y<=x:continue
        elapsed=b['observed_perf']-a['observed_perf'];check(elapsed>0,'nonmonotonic power clock')
        for gpu in result:
            pa,pb=a['GPUs'][gpu]['watts'],b['GPUs'][gpu]['watts']
            px=pa+(pb-pa)*(x-a['observed_perf'])/elapsed
            py=pa+(pb-pa)*(y-a['observed_perf'])/elapsed
            result[gpu]+=(px+py)*.5*(y-x)
        covered+=y-x
    check(abs(covered-(hi-lo))<1e-6,'power interval has uncovered duration')
    return result


def validate_trial(directory,trial,probe,config,power,receipt_batches,submissions):
    tid=trial['trial_id'];events=lines(directory/(tid+'-events.jsonl'))
    jobs=trial['execution_jobs'];by_job={job['job_id']:job for job in jobs}
    check(len(by_job)==len(jobs),'duplicate physical job')
    same([select(job,NEURAL_KEYS) for job in jobs],[select(job,NEURAL_KEYS) for job in probe['jobs']],
         'ordered logical neural inputs differ from frozen original peer layout')
    same(trial['original_job_inputs_sha256'],sha(probe['jobs']),'frozen original job hash changed')
    bids={job['_delivery']['batch_id'] for job in jobs};check(len(bids)==1,'mixed physical batch identity')
    bid=bids.pop();submission=submissions[bid]
    same(submission['jobs'],jobs,'actual pre-submit job snapshot changed')
    physical=trial['physical_accounting'];same(physical['batch_id'],bid,'accounting batch changed')
    same(physical['job_ids'],list(by_job),'physical peer ordering changed')
    complete,cancelled=trial['complete_results'],trial['cancelled_results']
    check(not set(complete)&set(cancelled),'full/cancelled overlap')
    same(set(complete)|set(cancelled),set(by_job),'terminal partition does not cover all physical rows')
    same(physical['row_receipt_digests'],{jid:row['_row_receipt']['payload_sha256'] for jid,row in complete.items()},'complete manifest changed')
    same(physical.get('cancelled_row_receipt_digests',{}),{jid:row['terminal_digest'] for jid,row in cancelled.items()},'cancelled manifest changed')
    same({item['job_id'] for item in physical['selected_output_digests']},set(complete),'cancelled row advertised as selected output')
    phases=physical['phases'];same(len(phases),1,'not one independent generation phase')
    phase=phases[0];same(phase['executed_job_ids'],list(by_job),'masked/finished rows removed from paid model layout')
    same(phase['physical_batch_rows'],len(jobs),'physical row count changed')
    check(phase.get('fixed_layout_until_generation_return') is True,'unrecorded fixed-layout physical execution')
    pstart,pend=phase['started_perf'],phase['completed_perf'];drain=physical['batch_drained_perf']
    check(trial['submitted_perf']<=submission['observed_perf']<=physical['worker_started_perf']<=pstart<=pend<=drain<=trial['drain_observed_perf'],
          'noncausal actual dispatch/model/drain timeline')
    check(abs((pend-pstart)-trial['model_phase_seconds'])<1e-9,'model seconds not actual phase difference')
    check(abs((trial['drain_observed_perf']-trial['submitted_perf'])-trial['physical_interval_seconds'])<1e-9,'physical interval not actual span')
    starts=[event for event in events if event['kind']=='model-started']
    ends=[event for event in events if event['kind']=='model-completed']
    same(len(starts),1,'model-start record missing/repeated');same(len(ends),1,'model-end record missing/repeated')
    same(starts[0]['started_perf'],pstart,'worker model-start disagrees');same(ends[0]['completed_perf'],pend,'worker model-end disagrees')
    raw=receipt_batches[bid]
    terminal_by_job={}
    drains=[]
    for record in raw:
        if record['kind']=='batch-drained':drains.append(record);continue
        message=record['message'];jid=message['binding']['job_id']
        check(jid not in terminal_by_job,'duplicate worker terminal receipt')
        validate_binding(by_job[jid],message['binding']);terminal_by_job[jid]=record
    same(set(terminal_by_job),set(by_job),'actual worker terminal receipts do not cover batch')
    same(len(drains),1,'actual worker BatchDrained missing/repeated')
    drain_message=drains[0]['message']
    same(drain_message['completed_perf'],drain,'worker drain/controller accounting disagree')
    same(dict(drain_message['row_digests']),physical['row_receipt_digests'],'worker complete-drain manifest disagree')
    same(dict(drain_message.get('cancelled_digests',[])),physical.get('cancelled_row_receipt_digests',{}),'worker cancelled-drain manifest disagree')
    for key,value in physical.items():
        if key not in ('kind','operator_observed_perf'):
            same(drains[0]['physical_accounting'][key],value,'raw worker accounting differs: '+key)
    audits={}
    for jid,row in complete.items():
        check(terminal_by_job[jid]['kind']=='row-complete','complete result lacks worker full receipt')
        message=terminal_by_job[jid]['message'];payload=json.loads(message['payload_json'])
        same(message['payload_digest'],sha(payload),'full worker payload digest changed')
        same(select(row,[key for key in row if key!='_row_receipt']),payload,'operator complete row differs from worker payload')
        same(row['_row_receipt']['payload_sha256'],message['payload_digest'],'owner full receipt hash changed')
        same(row['_row_receipt']['binding'],message['binding'],'owner full binding changed')
        check(pstart<=message['terminal_perf']<=message['rendered_perf']<=message['emitted_perf']<=drain,'full terminal after drain or before model')
        audit=row['model_input_audit'];audits[jid]=(row['execution_context_audit'],audit)
        same(row['generated_tokens'],len(row['token_ids']),'complete generated token count changed')
        check(0<len(row['token_ids'])<=config['worker']['max_new_tokens'],'invalid complete token count')
        eos=row['token_ids'][-1] in audit['eos_token_ids']
        same(eos,row['terminated_by_eos'],'complete EOS claim false')
        check(eos or len(row['token_ids'])==config['worker']['max_new_tokens'],'partial short result presented as complete')
        selected=next(item for item in physical['selected_output_digests'] if item['job_id']==jid)
        same(selected['Z_sha256'],token_sha(row['token_ids']),'selected tokens changed')
        same(selected['P_sha256'],token_sha(row['state_tokens']),'selected feedback changed')
        same(selected['text_sha256'],hashlib.sha256(row['text'].encode()).hexdigest(),'selected text changed')
    requests={request['request_id']:request for request in trial['requests']}
    same(len(requests),len(trial['requests']),'duplicate operator request ID')
    target_schedule={item['job_id']:item for item in probe['cancel_schedule']}
    cancel_rows=[]
    for jid,cancellation in cancelled.items():
        check(terminal_by_job[jid]['kind']=='row-cancelled','cancel lacks actual worker receipt')
        message=cancellation['message'];same(set(message),CANCEL_KEYS,'cancel terminal carries unknown/output fields')
        same(message,terminal_by_job[jid]['message'],'operator cancel differs from worker receipt')
        same(message['terminal_digest'],sha(dict(kind='row-cancelled-v1',**{key:value for key,value in message.items() if key!='terminal_digest'})),
             'cancelled terminal digest changed')
        check(not {'token_ids','state_tokens','text','next_prompt_tokens'}&set(cancellation),'cancelled output advertised as usable')
        request=requests[message['request_id']]
        for key in ('binding','request_id','reason','requested_perf'):
            same(message[key],request[key],'cancelled terminal/request mismatch: '+key)
        same(request['status'],'new-request','applied cancel lacks accepted owner request')
        same(request['binding'],by_job[jid]['_delivery']['binding'],'request binding changed')
        same(request['frozen_intervention'],target_schedule[jid],'operator intervention changed')
        check(request['intervention_is_archival_not_current_owner_proof'] is True,'operator mislabeled as live coverage')
        same(request['scheduled_perf'],pstart+target_schedule[jid]['delay_from_phase_start_seconds'],'intervention clock rebased')
        check(request['scheduled_perf']<=message['requested_perf']<=message['acknowledged_perf']<=message['emitted_perf']<=pend<=drain,
              'cancel request/ack/drain clock order invalid')
        check(cancellation['physical_worker_released'] is False and request['physical_worker_released'] is False,'row/request releases worker')
        check(type(message['decoded_tokens']) is int and message['decoded_tokens']>=0,'bad canceled count')
        input_record=physical['cancelled_row_inputs'][jid]
        same(set(input_record),{'execution_context_audit','model_input_audit'},'cancelled input record contains generated output')
        audits[jid]=(input_record['execution_context_audit'],input_record['model_input_audit'])
        same(next(item for item in physical['cancelled_rows'] if item['binding']['job_id']==jid),message,'batch cancelled receipt disagreement')
        cancel_rows.append(dict(probe_id=probe['probe_id'],trial_id=tid,batch_id=bid,job_id=jid,
            decoded_tokens_before_cancel=message['decoded_tokens'],
            schedule_lateness_seconds=message['requested_perf']-request['scheduled_perf'],
            request_to_ack_seconds=message['acknowledged_perf']-message['requested_perf'],
            emitted_to_physical_model_return_seconds=pend-message['emitted_perf'],
            emitted_to_worker_batch_drain_seconds=drain-message['emitted_perf'],
            model_return_to_batch_drain_seconds=drain-pend,
            physical_charge_scope='whole unchanged fixed-layout generation; row tails overlap'))
    for jid,(context,model_audit) in audits.items():
        job=by_job[jid]
        same(model_audit['dtype'],config['worker']['dtype'],'execution dtype changed')
        same(model_audit['batch_rows'],len(jobs),'processed tensor layout changed')
        same(model_audit['source_id'],job['source_id'],'wrong consumed source')
        same(model_audit['waveform_sha256'],job['prefix_audio_sha256'],'wrong consumed audio')
        same(model_audit['declared_prompt_tokens'],job['prompt_tokens'],'declared input mismatch')
        same(context['executed_prompt_tokens'],job.get('fault_actual_prompt_tokens',job['prompt_tokens']),'actual consumed prompt changed')
        same(context['fault_override'],'fault_actual_prompt_tokens' in job,'fault context mislabeled')
    if trial['policy']=='no_cancel':
        same(len(cancelled),0,'control canceled work');same(len(requests),0,'control requested retirement')
    else:
        check(set(cancelled)<=set(target_schedule),'unscheduled row cancelled')
    # Operator logs contain repeated observations of the same request/terminal;
    # validate them, but count unique sealed worker receipts, not log entries.
    for event in events:
        if event['kind']=='cancel-request':
            request=requests[event['request_id']]
            for key in ('request_id','binding','reason','requested_perf'):
                same(event[key],request[key],'duplicate request observation changed')
        if event['kind']=='cancel-applied':
            same(event['message'],cancelled[event['job_id']]['message'],'duplicate cancel observation changed')
    same(len([event for event in events if event['kind']=='operator-row-complete']),len(complete),'operator full observation count changed')
    energy=joules(power,trial['submitted_perf'],trial['drain_observed_perf'])
    check(abs(sum(energy.values())-trial['both_board_joules'])<1e-6,'two-board energy recount differs')
    row=dict(probe_id=probe['probe_id'],trial_id=tid,repeat=trial['repeat'],policy=trial['policy'],batch_id=bid,
        physical_rows=len(jobs),full_rows=len(complete),cancelled_rows=len(cancelled),
        actual_model_phase_seconds=pend-pstart,actual_operator_interval_seconds=trial['drain_observed_perf']-trial['submitted_perf'],
        actual_worker_lease_seconds=drain-submission['observed_perf'],
        model_return_to_worker_drain_seconds=drain-pend,
        operator_receive_after_worker_drain_seconds=trial['drain_observed_perf']-drain,
        gpu0_board_joules=energy['0'],gpu1_board_joules=energy['1'],both_board_joules=sum(energy.values()),
        raw_cancel_request_observations=sum(event['kind']=='cancel-request' for event in events),
        unique_cancel_requests=len(requests),raw_cancel_observations=sum(event['kind']=='cancel-applied' for event in events))
    return row,cancel_rows,audits


def main():
    transfer=read(HERE/'RAW_INDEX.json')
    for record in transfer['files']:same(file_sha(RAW/record['path']),record['sha256'],'local raw evidence changed')
    freeze,config,environment=read(RAW/'FREEZE.json'),read(RAW/'CONFIG.json'),read(RAW/'ENVIRONMENT.json')
    same(file_sha(RAW/'CONFIG.json'),freeze['config_sha256'],'frozen config hash changed')
    same(file_sha(RAW/'ENVIRONMENT.json'),freeze['environment_sha256'],'environment hash changed')
    same(config['execution_source'],freeze['execution_source'],'source identity changed')
    manifest=config['execution_source']['manifest']
    source=HERE.parent/'source'
    same(file_sha(HERE.parent/'packages/SOURCE_v1.json'),config['execution_source']['manifest_sha256'],'execution source manifest hash differs')
    for item in manifest['files']:same(file_sha(source/item['path']),item['sha256'],'local frozen source byte differs: '+item['path'])
    power=lines(RAW/'power.jsonl');trials=[];cancellations=[];pairs=[];startup=[];equivalence=[]
    for frozen_probe in config['probe_configs']:
        probe=frozen_probe['original_inputs'];pid=probe['probe_id'];directory=RAW/pid
        same(read(directory/'EXECUTION_CONFIG.json'),frozen_probe['execution_config'],'per-probe execution config changed')
        ready=read(directory/'WORKER_READY.json');times=ready['startup_profile']
        same(ready['runtime_digest'],frozen_probe['execution_config']['runtime_digest'],'worker loaded different runtime')
        check(times['model_load_started_perf']<=times['model_load_complete_perf']<=times['warmup_started_perf']<=times['warmup_complete_perf'],
              'startup/warmup clocks not causal')
        same(ready['warmup_policy'],'synthetic-zero-audio-not-a-serving-input','warmup used a serving input')
        startup.append(dict(probe_id=pid,worker_entry_to_warmup_done_seconds=times['warmup_complete_perf']-times['worker_main_entry_perf'],
            imports_seconds=times['imports_complete_perf']-times['imports_started_perf'],
            model_load_wall_seconds=times['model_load_complete_perf']-times['model_load_started_perf'],
            warmup_wall_seconds=times['warmup_complete_perf']-times['warmup_started_perf'],
            startup_both_board_joules=sum(joules(power,times['worker_main_entry_perf'],times['warmup_complete_perf']).values()),
            model_load_both_board_joules=sum(joules(power,times['model_load_started_perf'],times['model_load_complete_perf']).values()),
            warmup_both_board_joules=sum(joules(power,times['warmup_started_perf'],times['warmup_complete_perf']).values())))
        submissions={row['batch_id']:row for row in lines(directory/'worker_receipts.jsonl.submissions')}
        receipts={}
        for row in lines(directory/'worker_receipts.jsonl'):
            bid=row['message']['batch_id'] if row['kind']=='batch-drained' else row['message']['binding']['batch_id']
            receipts.setdefault(bid,[]).append(row)
        same(set(submissions),set(receipts),'unaccounted submitted/drained physical batch')
        actuals={};audits={};observations={}
        for path in sorted(directory.glob('*-RESULT.json')):
            trial=read(path);key=(trial['repeat'],trial['policy']);check(key not in actuals,'duplicate trial')
            observation,cancel,audit=validate_trial(directory,trial,probe,frozen_probe['execution_config'],power,receipts,submissions)
            actuals[key]=trial;observations[key]=observation;audits[key]=audit
            trials.append(observation);cancellations+=cancel
        same(set(actuals),{(repeat,policy) for repeat in range(config['repeats']) for policy in config['policies']},'missing/repeated trial arm')
        same(len(submissions),len(actuals),'extra worker model trial not in result files')
        previous_drain=-math.inf
        for key,trial in sorted(actuals.items(),key=lambda pair:pair[1]['submitted_perf']):
            check(previous_drain<=trial['submitted_perf'],'worker reused before physical drain')
            previous_drain=trial['physical_accounting']['batch_drained_perf']
        reference0=actuals[(0,'no_cancel')]
        old={row['job_id']:row for row in probe['original_row_expectations']}
        for key,trial in actuals.items():
            repeat,policy=key;reference=actuals[(repeat,'no_cancel')]
            for job in trial['execution_jobs']:
                jid=job['job_id'];context,model_audit=audits[key][jid]
                reference_audit=audits[(repeat,'no_cancel')][jid][1]
                baseline_audit=audits[(0,'no_cancel')][jid][1]
                same(select(model_audit,TENSOR_KEYS),select(reference_audit,TENSOR_KEYS),'same-repeat input tensors changed')
                same(select(model_audit,TENSOR_KEYS),select(baseline_audit,TENSOR_KEYS),'repeat input tensors changed')
                same(select(model_audit,TENSOR_KEYS),select(old[jid]['model_input_audit'],TENSOR_KEYS),'archived processed input tensors changed')
                row=trial['complete_results'].get(jid)
                if row is not None:
                    same(select(row,OUTPUT_KEYS),select(reference['complete_results'][jid],OUTPUT_KEYS),'surviving full output differs from same-input control')
                    same(select(row,OUTPUT_KEYS),select(reference0['complete_results'][jid],OUTPUT_KEYS),'full output differs across repeats')
                    same(select(row,OUTPUT_KEYS),select(old[jid],OUTPUT_KEYS),'full output differs from archived expectation')
                    for raw_key in ('F2_raw_execution_state_tokens','F2_raw_execution_text'):
                        if raw_key in row:same(row[raw_key],reference['complete_results'][jid][raw_key],'raw F2 output differs across arms')
                equivalence.append(dict(probe_id=pid,trial_id=trial['trial_id'],job_id=jid,
                    processed_input_tensors_equal_reference_repeat_and_archive=True,
                    full_output_equal_reference_repeat_and_archive=True if row is not None else None,
                    terminal_kind='complete' if row is not None else 'cancelled',
                    scalar_logits_or_activation_repeat_evidence_retained=False))
            if policy!='no_cancel':
                other=observations[(repeat,'no_cancel')];this=observations[key]
                pairs.append(dict(probe_id=pid,repeat=repeat,cancelled_rows=this['cancelled_rows'],
                    model_phase_saved_seconds=other['actual_model_phase_seconds']-this['actual_model_phase_seconds'],
                    operator_interval_saved_seconds=other['actual_operator_interval_seconds']-this['actual_operator_interval_seconds'],
                    worker_lease_saved_seconds=other['actual_worker_lease_seconds']-this['actual_worker_lease_seconds'],
                    both_board_joules_saved=other['both_board_joules']-this['both_board_joules']))
    counts=Counter(row['terminal_kind'] for row in equivalence)
    summary=dict(status='PASS_INDEPENDENT_RAW_FIXED_INPUT_OPERATOR_RECOUNT',
        evidence_tier='real model-resident fixed-input operator; archival intervention; no current Owner, Consumer, service SLO, or prevalence evidence',
        execution_source_commit=config['execution_source']['source_commit'],source_manifest_files_byte_matched=len(manifest['files']),
        raw_files=transfer['file_count'],raw_bytes=transfer['total_bytes'],probes=len(config['probe_configs']),
        actual_model_trial_batch_invocations=len(trials),actual_model_trial_physical_rows=len(equivalence),
        actual_full_worker_receipts=counts['complete'],actual_cancelled_worker_receipts=counts['cancelled'],actual_worker_batch_drains=len(trials),
        observed_worker_warmup_episodes=len(startup),
        source_verified_generate_calls_per_warmup=1,
        warmup_generate_call_evidence='three warmup-start/complete worker records plus byte-matched source single execute/model.generate path; no per-forward trace',
        actual_generate_invocations_including_warmup=len(trials)+len(startup),
        cuda_kernel_invocations=None,forward_invocations=None,
        scalar_float_repeat_claim='input tensor hashes and chosen-token/state/text outputs repeated exactly; activations/logits not retained',
        trial_model_phase_seconds=sum(row['actual_model_phase_seconds'] for row in trials),
        trial_operator_interval_seconds=sum(row['actual_operator_interval_seconds'] for row in trials),
        worker_startup_wall_seconds=sum(row['worker_entry_to_warmup_done_seconds'] for row in startup),
        model_load_wall_seconds=sum(row['model_load_wall_seconds'] for row in startup),
        warmup_wall_seconds=sum(row['warmup_wall_seconds'] for row in startup),
        paired_operator_effects=pairs,
        interpretation='surviving complete rows and repeated inputs verified from raw; all row-mask tails paid to actual model return and BatchDrained; no per-row FLOPs or service benefit inferred')
    (HERE/'RECOUNT.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for name,rows in [('TRIALS',trials),('CANCELLATIONS',cancellations),('STARTUP',startup),('ROW_EQUIVALENCE',equivalence),('PAIRED_EFFECTS',pairs)]:
        (HERE/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n',encoding='utf8')
        with (HERE/(name+'.csv')).open('w',newline='',encoding='utf8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps({key:summary[key] for key in ['status','actual_model_trial_batch_invocations','actual_full_worker_receipts','actual_cancelled_worker_receipts','trial_model_phase_seconds','model_load_wall_seconds','warmup_wall_seconds','paired_operator_effects']}))


if __name__=='__main__':main()
