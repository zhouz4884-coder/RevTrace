"""Frozen-input real-Qwen retirement operator. Not a serving experiment.

Historical coverage times become explicit operator interventions. There is no
claim that a current Owner established coverage, an SLO improved, or a consumer
made progress. Fixed-layout phases charge every row until real generation end.
"""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'

from pathlib import Path
import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import platform
import re
import statistics
import subprocess
import sys
import time
import traceback

W=Path(__file__).resolve().parent
for directory in [W/'runtime/src',W/'runtime/scripts']:
    sys.path.insert(0,str(directory))

SCOPE='actual one-worker model-resident fixed-input operator; archival interventions, no online serving or natural-prevalence claim'
DISK=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
OUTPUT_KEYS=('token_ids','state_tokens','text','terminated_by_eos','hit_token_limit')
INPUT_KEYS=('source_id','language','prompt_tokens','fault_actual_prompt_tokens','chunk_id',
  'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256')
TENSOR_KEYS=('input_ids','attention_mask','unpadded_input_ids','batch_tensors','row_features',
  'dtype','batch_rows','prompt_width','max_new_tokens','eos_token_ids')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))
def put(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')


def verify_source(manifest_path,source_commit,root=W):
    """Byte-check execution sources; the launcher's local Git gate remains required."""
    if not re.fullmatch('[0-9a-f]{40}',source_commit):raise ValueError('full execution source commit required')
    source=read(manifest_path);files=source.get('files')
    if not isinstance(files,list) or not files:raise ValueError('complete source manifest required')
    declared=source.get('source_commit',source.get('code_commit'))
    if declared is not None and declared!=source_commit:raise ValueError('source commit/manifest mismatch')
    seen=set();base=Path(root).resolve()
    for item in files:
        name=item['path'];target=(base/name).resolve()
        if target==base or not target.is_relative_to(base) or name in seen:raise ValueError('invalid source manifest path')
        seen.add(name)
        if file_sha(target)!=item['sha256']:raise ValueError('source byte mismatch: '+name)
    for required in ['retirement_operator.py','runtime/scripts/row_delivery_worker.py',
      'runtime/scripts/row_delivery_executor.py','runtime/scripts/tc_live_worker.py',
      'runtime/src/revtrace/row_lifecycle.py','runtime/src/revtrace/row_stream.py']:
        if required not in seen:raise ValueError('execution manifest omits '+required)
    git_checked=False
    if (base/'.git').exists():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip()
        if head!=source_commit:raise ValueError('checkout HEAD differs from execution source')
        dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=base,text=True)
        if dirty.strip():raise ValueError('execution source checkout is dirty')
        git_checked=True
    return {'source_commit':source_commit,'manifest_sha256':file_sha(manifest_path),
      'manifest':source,'git_checked_here':git_checked,
      'local_resolvable_commit_launch_gate_required':True}


def neural_inputs(jobs):
    return [{k:copy.deepcopy(j[k]) for k in INPUT_KEYS if k in j} for j in jobs]


def validate_probe(probe):
    jobs=probe['jobs'];ids=[j['job_id'] for j in jobs]
    if not jobs or len(set(ids))!=len(ids):raise ValueError('unique full original peer jobs required')
    if any(j['role']!='proposal' for j in jobs):raise ValueError('operator accepts proposer batches only')
    schedules=probe.get('cancel_schedule',[]);targets=set()
    for item in schedules:
        delay=item['delay_from_phase_start_seconds'];jid=item['job_id']
        if jid not in ids or jid in targets:raise ValueError('cancellation schedule has unknown/repeated target')
        if not isinstance(delay,(int,float)) or not math.isfinite(delay) or delay<0:
            raise ValueError('nonnegative finite frozen intervention delay required')
        targets.add(jid)
    if len(jobs)>int(probe['original_proposal_runtime']['microbatch']):
        raise ValueError('original full physical layout exceeds declared microbatch')


def build_execution_config(probe,source_identity,software,*,gpu=0):
    """Original numerical/input contract plus newly identified shared actuator."""
    validate_probe(probe)
    original=copy.deepcopy(probe['original_proposal_runtime'])
    for name,wanted in original.get('software',{}).items():
        if software.get(name)!=wanted:raise ValueError('numerical environment drift: '+name)
    runtime={'schema':'retirement-shared-operator-runtime-v1',
      'original_numerical_contract':{k:v for k,v in original.items() if k not in
        ['code_commit','hardware_fingerprint','software','row_delivery','ces_evidence_choice']},
      'software':copy.deepcopy(software),'code_commit':source_identity['source_commit'],
      'source_manifest_sha256':source_identity['manifest_sha256'],
      'physical_exit':{'safe_point':'after-decode-token-event','layout':'unchanged-full-peer-order',
        'release':'generation-return-CUDA-synchronize-then-BatchDrained',
        'masked_compute':'charged-until-full-physical-return'},
      'row_delivery':'complete-or-cancelled-v1'}
    runtime_digest=digest(runtime)
    contract={'schema':'retirement-operator-contract-v1','runtime_digest':runtime_digest,
      'original_ordered_job_inputs_sha256':digest(probe['jobs']),
      'original_contract_digests':sorted({j['contract_digest'] for j in probe['jobs']}),
      'no_owner_install_or_consumer':True,'shared_actuator_in_both_arms':True}
    contract_digest=digest(contract)
    config={'model':probe['model_path'],'manifest':probe['manifest_path'],'gpu':gpu,
      'dtype':original['dtype'],'microbatch':int(original['microbatch']),
      'max_new_tokens':int(original['max_new_tokens']),'runtime_digest':runtime_digest,
      'render_contract':copy.deepcopy(original['render_contract']),
      'allow_execution_context_override':bool(original.get('allow_execution_context_override',False)),
      'row_delivery':'row','capture_model_inputs':True,'lifecycle_instrumentation':True,
      'physical_retirement':True}
    return {'worker':config,'runtime':runtime,'runtime_digest':runtime_digest,
      'contract':contract,'contract_digest':contract_digest}


def execution_jobs(probe,config,ready_perf):
    jobs=copy.deepcopy(probe['jobs'])
    for job in jobs:
        job.pop('_delivery',None)
        job.update(runtime_digest=config['runtime_digest'],contract_digest=config['contract_digest'],
          audio_ready_perf=ready_perf,enqueue_perf=ready_perf)
    if neural_inputs(jobs)!=neural_inputs(probe['jobs']):raise ValueError('neural input/order changed')
    return jobs


def output_identity(row):return {key:row[key] for key in OUTPUT_KEYS}


def terminal_gate(probe,policy,completed,cancelled):
    expected={j['job_id'] for j in probe['jobs']};complete=set(completed);cancel=set(cancelled)
    targets={item['job_id'] for item in probe.get('cancel_schedule',[])}
    if complete&cancel or complete|cancel!=expected:raise ValueError('terminal partition is not complete and disjoint')
    if policy=='no_cancel' and cancel:raise ValueError('no-cancel control cancelled a row')
    if not cancel<=targets:raise ValueError('operator cancelled an unscheduled row')
    if not expected-targets<=complete:raise ValueError('legitimate unscheduled rows not fully completed')
    return {'full_terminal_partition':True,'all_unscheduled_rows_complete':True,
      'complete_rows':len(complete),'cancelled_rows':len(cancel)}


def compare_trials(probe,trials):
    """All correctness comparisons happen after each timed physical interval."""
    refs={x['repeat']:x for x in trials if x['policy']=='no_cancel'}
    if not refs:raise ValueError('a repeated no_cancel reference arm is mandatory')
    first=next(iter(refs.values()))['complete_results'];checks=[]
    archived={r['job_id']:r for r in probe.get('original_row_expectations',[])}
    for trial in trials:
        ref=refs[trial['repeat']]['complete_results'];rows=[]
        for jid,row in trial['complete_results'].items():
            same=output_identity(row)==output_identity(ref[jid])
            repeated=output_identity(ref[jid])==output_identity(first[jid])
            old=archived.get(jid);tensor_equal=None;archived_equal=None
            if old:
                archived_equal=output_identity(row)==output_identity(old)
                original_audit=old.get('model_input_audit',{})
                if original_audit:
                    tensor_equal=all(row['model_input_audit'].get(k)==original_audit.get(k) for k in TENSOR_KEYS)
            rows.append({'job_id':jid,'same_repeat_no_cancel_output_equal':same,
              'no_cancel_repeat_output_equal':repeated,'archived_output_equal':archived_equal,
              'archived_neural_tensor_identity_equal':tensor_equal})
        checks.append({'trial_id':trial['trial_id'],'rows':rows,
          'all_complete_outputs_equal_no_cancel':all(r['same_repeat_no_cancel_output_equal'] for r in rows),
          'no_cancel_repeats_equal':all(r['no_cancel_repeat_output_equal'] for r in rows),
          'all_available_archived_tensors_equal':all(r['archived_neural_tensor_identity_equal'] is not False for r in rows)})
    safe=all(c['all_complete_outputs_equal_no_cancel'] and c['no_cancel_repeats_equal'] and
      c['all_available_archived_tensors_equal'] for c in checks)
    pairs=[]
    for trial in trials:
        if trial['policy']=='no_cancel':continue
        ref=refs[trial['repeat']]
        pairs.append({'repeat':trial['repeat'],'policy':trial['policy'],
          'batch_wall_saved_seconds':ref['physical_interval_seconds']-trial['physical_interval_seconds'],
          'model_phase_saved_seconds':ref['model_phase_seconds']-trial['model_phase_seconds'],
          'both_board_joules_saved':ref['both_board_joules']-trial['both_board_joules'],
          'actual_cancelled_rows':len(trial['cancelled_results'])})
    positive=bool(pairs) and statistics.median(p['model_phase_saved_seconds'] for p in pairs)>0
    return {'scope':SCOPE,'safe_equivalence_gate':safe,'comparisons':checks,'paired_operator_effects':pairs,
      'gate':('GO_TO_SERVICE_OPPORTUNITY_CHECK' if safe and positive and any(p['actual_cancelled_rows'] for p in pairs)
        else 'NO_GO_OPERATOR_OR_NO_PHYSICAL_OPPORTUNITY'),
      'service_value_proven':False,'no_expansion_without_actual_service_gate':True}


def run_trial(worker,probe,config,policy,repeat,power,out,timeout_seconds):
    trial_id=f'r{repeat}-{policy}';events=[];completed={};cancelled={};requests=[];phase_start=None
    original_job_hash=digest(probe['jobs']);jobs=execution_jobs(probe,config,time.perf_counter())
    schedules=copy.deepcopy(probe.get('cancel_schedule',[])) if policy=='covered' else []
    fired=set();began=time.perf_counter();worker.submit(jobs)
    with (out/(trial_id+'-events.jsonl')).open('x',encoding='utf8') as stream:
        def log(event):
            event=copy.deepcopy(event);event.setdefault('operator_observed_perf',time.perf_counter())
            events.append(event);stream.write(json.dumps(event,allow_nan=False)+'\n');stream.flush()
        log({'kind':'operator-submit','trial_id':trial_id,'jobs':jobs,
          'original_job_inputs_sha256':original_job_hash,'scope':SCOPE})
        while True:
            if time.perf_counter()-began>timeout_seconds:raise TimeoutError('operator physical batch did not drain')
            rows=worker.poll()
            for item in worker.drain_telemetry():
                log(item)
                if item['kind']=='model-started' and phase_start is None:phase_start=item['started_perf']
            for result in rows or []:
                jid=result['job_id']
                if jid in completed or jid in cancelled:raise ValueError('duplicate/exclusive terminal violated')
                completed[jid]=result;log({'kind':'operator-row-complete','result':result})
            for audit in worker.drain_cancellations():
                jid=audit['job_id']
                if jid in completed or jid in cancelled:raise ValueError('duplicate/exclusive cancellation violated')
                cancelled[jid]=audit;log(audit)
            now=time.perf_counter()
            if phase_start is not None and not worker.batch_drained:
                for intervention in schedules:
                    jid=intervention['job_id'];due=phase_start+intervention['delay_from_phase_start_seconds']
                    if jid not in fired and now>=due:
                        request=worker.cancel_job(jid,'frozen-operator-trusted-coverage',requested_perf=time.perf_counter())
                        request.update(frozen_intervention=intervention,scheduled_perf=due,
                          schedule_lateness_seconds=request['requested_perf']-due,
                          intervention_is_archival_not_current_owner_proof=True)
                        requests.append(request);fired.add(jid);log(request)
            if worker.batch_drained:
                drained=time.perf_counter();break
            time.sleep(.001)
        for intervention in schedules:
            if intervention['job_id'] not in fired:
                log({'kind':'operator-schedule-not-fired','job_id':intervention['job_id'],
                  'status':'physical-batch-drained-before-intervention','frozen_intervention':intervention})
    accounting=[e for e in events if e['kind']=='batch-accounting']
    if len(accounting)!=1:raise ValueError('one actual BatchDrained accounting required')
    phase=accounting[0]['phases']
    if len(phase)!=1 or phase[0]['completed_perf'] is None:raise ValueError('one synchronized independent-generation phase required')
    gate=terminal_gate(probe,policy,completed,cancelled)
    result={'trial_id':trial_id,'repeat':repeat,'policy':policy,'scope':SCOPE,
      'submitted_perf':began,'drain_observed_perf':drained,'physical_interval_seconds':drained-began,
      'model_phase_seconds':phase[0]['completed_perf']-phase[0]['started_perf'],
      'both_board_joules':power.joules(began,drained),'complete_results':completed,
      'cancelled_results':cancelled,'requests':requests,'physical_accounting':accounting[0],
      'execution_jobs':jobs,'original_job_inputs_sha256':original_job_hash,'terminal_gate':gate}
    put(out/(trial_id+'-RESULT.json'),result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe',type=Path,required=True)
    p.add_argument('--probe-id',action='append',help='select named probes; defaults to all')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--source-commit',required=True)
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--policies',nargs='+',choices=['no_cancel','covered'],default=['no_cancel','covered'])
    p.add_argument('--gpu',type=int,default=0)
    p.add_argument('--timeout-seconds',type=float,default=120.)
    a=p.parse_args()
    if a.repeats<2 or 'no_cancel' not in a.policies or len(set(a.policies))!=len(a.policies):
        raise ValueError('at least two repeats, a no_cancel control, and distinct arms required')
    if not a.out.resolve().is_relative_to(DISK.resolve()):raise ValueError('raw operator results require designated experiment disk')
    source=verify_source(a.source_manifest,a.source_commit)
    spec=read(a.probe);probes=[q for q in spec['probes'] if not a.probe_id or q['probe_id'] in a.probe_id]
    if not probes or a.probe_id and set(a.probe_id)!={q['probe_id'] for q in probes}:raise ValueError('unknown/empty probe selection')
    software={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers','numpy','soundfile']}
    environment={'python':sys.version,'platform':platform.platform(),'software':software,
      'nvidia_smi':subprocess.check_output(['nvidia-smi'],text=True),
      'evidence_tier':SCOPE}
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True)
    if apps.strip():raise RuntimeError('GPU busy before operator; no competing work launched')
    prepared=[]
    for probe in probes:
        for path in [probe['manifest_path'],probe['model_path']]:
            if not Path(path).resolve().is_relative_to(DISK.resolve()):raise ValueError('model/data outside experiment disk')
        if file_sha(probe['manifest_path'])!=probe['manifest_sha256']:raise ValueError('original audio manifest changed')
        prepared.append((probe,build_execution_config(probe,source,software,gpu=a.gpu)))
    a.out.mkdir(parents=True,exist_ok=False)
    put(a.out/'ENVIRONMENT.json',environment)
    freeze={'experiment_id':a.out.name,'status':'FROZEN_BEFORE_GPU_WORKER_START',
      'scope':SCOPE,'execution_source':source,'probe_file_sha256':file_sha(a.probe),
      'environment_sha256':file_sha(a.out/'ENVIRONMENT.json'),
      'repeats':a.repeats,'policies':a.policies,'actual_gpu':a.gpu,
      'raw_result_path':str(a.out),'summary_path':str(a.out/'SUMMARY.json'),
      'decision_path':str(a.out/'GATE.json'),'probe_configs':[
        {'probe_id':q['probe_id'],'original_inputs':q,'execution_config':c,
         'original_job_inputs_sha256':digest(q['jobs'])} for q,c in prepared]}
    put(a.out/'CONFIG.json',freeze)
    put(a.out/'FREEZE.json',{'config_sha256':file_sha(a.out/'CONFIG.json'),
      'environment_sha256':file_sha(a.out/'ENVIRONMENT.json'),'execution_source':source})
    from memory_gpu_pilot import Power
    from row_delivery_executor import RowGPUExecutor
    power=None;worker=None;all_results=[]
    try:
        power=Power(a.out/'power.jsonl')
        if len(power.rows[-1]['GPUs'])<2:raise RuntimeError('both-board energy samples required')
        for probe,config in prepared:
            directory=a.out/probe['probe_id'];directory.mkdir()
            worker_config=dict(config['worker'],receipt_trace_path=str(directory/'worker_receipts.jsonl'))
            put(directory/'EXECUTION_CONFIG.json',config)
            worker=RowGPUExecutor('operator-proposal',worker_config);worker.wait_ready()
            put(directory/'WORKER_READY.json',worker.ready);trials=[]
            for repeat in range(a.repeats):
                arms=a.policies[repeat%len(a.policies):]+a.policies[:repeat%len(a.policies)]
                for policy in arms:
                    trials.append(run_trial(worker,probe,config,policy,repeat,power,directory,a.timeout_seconds))
                    put(a.out/'PROGRESS.json',{'status':'RUNNING','probe_id':probe['probe_id'],
                      'completed_trials':len(trials),'last_trial':trials[-1]['trial_id']})
            worker.close();worker=None
            verdict=compare_trials(probe,trials);put(directory/'GATE.json',verdict)
            all_results.append({'probe_id':probe['probe_id'],'verdict':verdict,
              'trials':[{k:v for k,v in t.items() if k not in ['complete_results','execution_jobs']} for t in trials]})
            if not verdict['safe_equivalence_gate']:
                put(a.out/'GATE.json',{'status':'NO_GO_EQUIVALENCE_RETAINED','results':all_results,'scope':SCOPE})
                put(a.out/'SUMMARY.json',{'status':'STOPPED_ON_FAILED_GATE','results':all_results,'scope':SCOPE})
                return
        put(a.out/'SUMMARY.json',{'status':'COMPLETE','scope':SCOPE,'results':all_results})
        put(a.out/'GATE.json',{'status':'COMPLETE_OPERATOR_ONLY_SERVICE_GATE_REQUIRED',
          'scope':SCOPE,'service_value_proven':False,'results':all_results})
    except BaseException:
        put(a.out/'STOP.json',{'status':'FAILED_RETAINED','traceback':traceback.format_exc(),'results':all_results})
        put(a.out/'GATE.json',{'status':'FAILED_RETAINED_NO_POSITIVE_CLAIM','scope':SCOPE})
        raise
    finally:
        if worker is not None:worker.close()
        if power is not None:power.close()


if __name__=='__main__':main()
