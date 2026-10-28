"""Freeze six old-source development cells; no GPU or ASR execution."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028'
O=B+'/results/revtrace/physical_retirement_20261028'
COMMIT='1d8c30804a945570429d85d934b3bfcba6171a43'
SOURCE_SHA='5b1527bdcb20e165bc69f5002e3092a38b8ec773606828936c211ed595781f63'
MANIFEST=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
LOCAL=ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    old=json.loads(LOCAL.read_text());selected=old['sessions'][:8]
    if len(selected)!=8 or len({s['source_id'] for s in selected})!=8 or len({s['audio_sha256'] for s in selected})!=8:raise ValueError('eight original metadata-first independent audio rows required')
    if sha(LOCAL)!='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc':raise ValueError('old source manifest identity')
    local_source=ROOT/'experiments/physical_retirement_20261028/packages/SOURCE_v2.json'
    if sha(local_source)!=SOURCE_SHA or json.loads(local_source.read_text())['code_commit']!=COMMIT:raise ValueError('final source v2 identity')
    order=[('qwen','sync','two_lane'),('whisper','sync','checked_snapshot'),
      ('qwen','staggered','two_lane'),('whisper','sync','two_lane'),
      ('qwen','sync','checked_snapshot'),('whisper','staggered','two_lane')]
    cells=[]
    for index,(adapter,arrival,consumer) in enumerate(order):
        cell_id=f'dev-{adapter}-rho1-{arrival}-{consumer}-r0'
        output=O+'/confirmation_dev_v2/'+cell_id
        model=B+'/models/'+('Qwen3-ASR-1.7B' if adapter=='qwen' else 'whisper-base.en')
        argv=[B+'/envs/revbatch-cu128/bin/python','-B',P+'/source_v2/retirement_service.py',
          '--out',output,'--source-manifest',P+'/SOURCE_v2.json','--manifest',MANIFEST,
          '--model',model,'--adapter',adapter,'--policy','row_complete','--method','dgft_original',
          '--rho','1','--sessions','8','--arrival',arrival,'--repeat','0','--retain','yes',
          '--confirmation-consumer',consumer,'--watchdog-seconds','2.0','--service-timeout','240.0','--wall-timeout','420.0']
        cells.append(dict(cell_id=cell_id,cohort='OLD_DEVELOPMENT_FIRST8',adapter=adapter,rho=1,
          arrival=arrival,repeat=0,retain='yes',confirmation_consumer=consumer,method='dgft_original',
          manifest=MANIFEST,manifest_sha256=sha(LOCAL),sessions=8,policy='row_complete',fixture=None,
          output=output,argv=argv,run_order_index=index,model=model,
          paired_block=f'old-dev-{adapter}-rho1-sync' if arrival=='sync' else f'old-dev-{adapter}-rho1-staggered',
          scope='already used development sources; final runtime/actual Consumer prequalification, not independent confirmation'))
    plan=dict(experiment_id='REVTRACE-COMPOSITION-OLD-DEVELOPMENT-PREQUALIFICATION-V2-20261028',
      status='FROZEN_SIX_DEVELOPMENT_CELLS_NOT_STARTED_BY_PREPARATION',code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,
      execution_source=P+'/source_v2',source_manifest=P+'/SOURCE_v2.json',original_manifest=MANIFEST,
      original_manifest_sha256=sha(LOCAL),source_selection='first8 metadata rows in frozen original16 manifest; no reordering, duplication or outcome selection',
      selected_sources=[{k:s[k] for k in ['source_id','path','audio_sha256','duration']} for s in selected],
      selected_audio_seconds=sum(s['duration'] for s in selected),cells=cells,
      run_order='fixed before outcomes; alternate model blocks and interleave checked_snapshot validation with two_lane cells',
      shared_contract=dict(authority_rho=1,fine_seconds=2.,display_slo_seconds=2.,commit_slo_seconds=8.,microbatch=16,
        max_new_tokens=256,proposal_dtype='float16',authority_dtype='float32',proposal_GPU=0,authority_GPU=1,
        physical_retirement='row_complete',protocol_kernel=True,kernel_copy_mode='event-cow',D1=True,
        input_WAL=True,canonical_WAL=True,actual_Consumer=True,retain_private_prefix=True,fixture=None),
      required_prelaunch='retirement_campaign and every retirement_service cell freeze source/environment/config/command/input hashes and experiment paths before launching; clean complete source v2 required; no existing GPU processes',
      interpretation=dict(execution_and_safety='All6 must complete independent full-input/kernel/Consumer audit. A code or safety failure requires preserved raw, repair and a newly committed source, never relabel this plan.',
        deadlines='D2/C8 failures are reported but do not select or alter heldout c8/arrival/110-cell matrix; no SLO promise is inferred from a development pass.',
        effect='one development process per cell is a carrier qualification, not a composition effect estimate or source-generalization result'),
      heldout_consumption=0,new_ASR_calls_by_plan_preparation=0,
      workload=dict(cells=6,offered_audio_seconds=sum(s['duration'] for s in selected)*6,
        outer_timeout_seconds_per_cell=420.,serial_timeout_budget_seconds=2520.,GPU_boards_per_cell=2,
        scope='descriptive workload/timeout bounds, not predicted or measured performance'))
    path=HERE/'DEV_PREFLIGHT_PLAN_v2.json';path.write_text(json.dumps(plan,indent=2,allow_nan=False)+'\n')
    receipt=dict(plan_file=path.name,plan_sha256=sha(path),plan_bytes=path.stat().st_size,
      remote_plan=P+'/CONFIRMATION_DEV_PLAN_v2_FROZEN.json',code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,
      builder_sha256=sha(Path(__file__)),ASR_calls_by_preparation=0)
    (HERE/'DEV_PREFLIGHT_PLAN_v2_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
