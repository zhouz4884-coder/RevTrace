"""Bind three retained anomalous inputs and exactly nine future calls."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
REVIEW=ROOT/'experiments/physical_retirement_20261028/confirmation_design/whisper_bad_data_review_v2'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_physical_retirement_20261028'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def main():
    source_path=HERE/'SOURCE_v3.json';source=read(source_path)
    raw=read(REVIEW/'RAW_EXTRACT.json');run=raw['dev-whisper-rho1-sync-checked_snapshot-r0']
    env_path=REVIEW/'ORIGINAL_ENVIRONMENT.json';env=read(env_path)
    old_path=ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json'
    old=read(old_path);audio={r['source_id']:r for r in old['sessions']};cases={}
    for name,sid,window in [('word_short',6,7),('word_full2s',7,8),('blank_short',5,8)]:
        index,rec=next((i,r) for i,r in enumerate(run['records']) if r['job']['session_id']==sid and r['job']['role']=='authority' and r['job']['end_window']==window)
        result=rec['result'];job=rec['job'];a=result['model_input_audit']
        # Serial neural rows share a batch-start clock. Peer scheduling is only
        # archival context and is intentionally not reexecuted by this plan.
        peers=sorted([r for r in run['records'] if r['job']['role']=='authority' and r['result']['started_perf']==result['started_perf']],key=lambda r:r['result']['model_started_perf'])
        cases[name]=dict(original_job=job,original_result=result,
          original_audio_row=audio[job['source_id']],reference=audio[job['source_id']]['reference'],
          original_streaming_final_text=next(s['text'] for s in run['result']['final_states'] if s['session_id']==sid),
          original_worker_record_file=run['files']['worker_records.jsonl'],original_worker_records_line_1based=index+1,
          expected_initial_decoder_ids_sha256=digest(a['actual_first_decoder_ids']),
          expected_CPU_features_sha256=a['input_features_sha256'],expected_GPU_FP32_features_sha256=a['actual_gpu_features_sha256'],
          original_peer_order=[r['job']['job_id'] for r in peers],
          peer_scope='recorded same batch-start serial peer order; peers omitted to preserve nine-call cap; not a lease replay')
    order=[('repeat','word_short',0),('repeat','word_full2s',0),('repeat','blank_short',0),
      ('repeat','blank_short',1),('repeat','word_full2s',1),('repeat','word_short',1),
      ('whole','word_short',None),('whole','word_full2s',None),('whole','blank_short',None)]
    calls=[dict(call_id=f'{i:02}-{kind}-{case}'+('' if repeat is None else '-r'+str(repeat)),kind=kind,case_id=case,repeat=repeat) for i,(kind,case,repeat) in enumerate(order)]
    plan=dict(schema='whisper-bad-data-nine-call-diagnostic-v1',experiment_id='REVTRACE-WHISPER-BAD-DATA-PAID-DIAGNOSTIC-20261028',
      status='FROZEN_PREPARATION_ONLY_NO_MODEL_CALLS_STARTED',code_commit=source['code_commit'],source_manifest_sha256=sha(source_path),
      execution_source=P+'/whisper_bad_data_diagnostic_source_v3',source_manifest=P+'/WHISPER_BAD_DATA_DIAGNOSTIC_SOURCE_v3.json',
      original_execution_source_commit='1d8c30804a945570429d85d934b3bfcba6171a43',
      original_execution_source_manifest_sha256='5b1527bdcb20e165bc69f5002e3092a38b8ec773606828936c211ed595781f63',
      original_raw_root=run['raw_root'],original_raw_inputs=run['files'],
      original_raw_extract_sha256=sha(REVIEW/'RAW_EXTRACT.json'),original_environment_sha256=sha(env_path),
      original_environment=env,original_authority_runtime=run['config']['authority_runtime'],
      audio_manifest=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json',audio_manifest_sha256=sha(old_path),
      model=B+'/models/whisper-base.en',gpu=1,dtype='float32',max_new_tokens=256,do_sample=False,
      cases=cases,calls=calls,warmup={'calls':1,'audio_samples':16000,'max_new_tokens':4,'history':[],
        'scope':'synthetic zero audio; separately counted, not a formal diagnostic call'},
      scope='six same-neural-input FP32 single-row repetitions plus three empty-history whole-source quality references; no serving claim, full original peer scheduling omitted',
      forbidden_features=['VAD','deduplication','repetition stopping','fallback','parameter sweep','holdout selection'],
      formal_model_calls=9,separate_warmup_model_calls=1,
      interpretation='Whole-source references use a different segmentation/input contract, not same-contract legal oracles or native transcribe fallback. Original streaming results remain unchanged. Differences are results, never permission for extra calls.',
      input_mask_limitation='original attention mask passed by pinned processor but not separately hashed; reconstruct and hash it now. Original decoded audio, CPU/FP32 features and actual first decoder IDs must match exactly.',
      intended_result=B+'/results/revtrace/physical_retirement_20261028/whisper_bad_data_diagnostic_v3',
      prior_scope='known failed development targets selected to explain retained bad data; not independent population/holdout evidence',
      holdout_consumption=0,model_calls_by_preparation=0)
    path=HERE/'PLAN_v3.json';path.write_text(json.dumps(plan,indent=2,allow_nan=False)+'\n')
    commands={}
    for mode,out in [('formal',plan['intended_result']),('CPU_inputs_only',plan['intended_result']+'_cpu_inputs')]:
        argv=[B+'/envs/revbatch-cu128/bin/python','-B','-u',plan['execution_source']+'/diagnostic.py',
          '--plan',P+'/WHISPER_BAD_DATA_DIAGNOSTIC_PLAN_v3.json','--plan-sha256',sha(path),
          '--source-manifest',plan['source_manifest'],'--out',out]
        if mode=='CPU_inputs_only':argv.append('--validate-inputs-only')
        commands[mode]=dict(argv=argv,scope='prepared only; parent controls serial launch',environment=dict(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',
          HF_HOME=B+'/cache/huggingface',XDG_CACHE_HOME=B+'/cache',TMPDIR=B+'/tmp/physical_retirement_20261028/whisper_diagnostic_v1'))
    (HERE/'LAUNCH_COMMANDS_v3.json').write_text(json.dumps(commands,indent=2)+'\n')
    print(json.dumps(dict(plan_sha256=sha(path),plan_bytes=path.stat().st_size,source_commit=source['code_commit'],source_manifest_sha256=sha(source_path),formal_calls=9,separate_warmup_calls=1)))

if __name__=='__main__':main()
