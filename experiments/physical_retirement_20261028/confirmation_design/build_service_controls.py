"""Frozen minimum retirement controls on old development inputs; never launch."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_physical_retirement_20261028'
O=B+'/results/revtrace/physical_retirement_20261028'
COMMIT='1d8c30804a945570429d85d934b3bfcba6171a43'
SOURCE_SHA='5b1527bdcb20e165bc69f5002e3092a38b8ec773606828936c211ed595781f63'
OLD=ROOT/'experiments/ces_v6_abcd_20261025/evidence/inputs/development_manifest.json'
FIXTURE=ROOT/'experiments/physical_retirement_20261028/packages/F2_INPUT_FIXTURE_v1.json'
MANIFEST=B+'/results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source=ROOT/'experiments/physical_retirement_20261028/packages/SOURCE_v2.json'
    if sha(source)!=SOURCE_SHA or json.loads(source.read_text())['code_commit']!=COMMIT:raise ValueError('full source v2 identity differs')
    if sha(OLD)!='8904fa5b16cb5d2c1f75d101079c6b7f640c2817b873cb92e816eecb694ea1bc':raise ValueError('original16 development manifest differs')
    fixture=json.loads(FIXTURE.read_text());old=json.loads(OLD.read_text());rows=old['sessions']
    if fixture['schema']!='physical-retirement-f2-input-fixture-v1' or sha(FIXTURE)!='b86566894c0db85c85e9a4bd4ffefb33c5db14067d42aeb0e75cebd42ba12892':raise ValueError('current F2 fixture identity differs')
    if len(rows)!=16 or len({r['source_id'] for r in rows})!=16 or len({r['audio_sha256'] for r in rows})!=16:raise ValueError('complete original16 distinct sources required')
    # Clean pairs bracket the F2 controls. Each repeat uses the opposite policy
    # order, fixed before any control result is available.
    order=[('clean','row_complete',0),('clean','no_cancel',0)]
    order += [('F2',policy,0) for policy in ['no_cancel','watchdog','parent','causal']]
    order += [('F2',policy,1) for policy in ['causal','parent','watchdog','no_cancel']]
    order += [('clean','no_cancel',1),('clean','row_complete',1)]
    cells=[]
    for index,(traffic,policy,repeat) in enumerate(order):
        cell_id=f'{policy}-{traffic}-r{repeat}';output=O+'/service_controls_v2/'+cell_id
        argv=[B+'/envs/revbatch-cu128/bin/python','-B',P+'/source_v2/retirement_service.py',
          '--out',output,'--source-manifest',P+'/SOURCE_v2.json','--manifest',MANIFEST,
          '--model',B+'/models/Qwen3-ASR-1.7B','--adapter','qwen','--policy',policy,
          '--method','standard_fair','--rho','1','--sessions','16','--arrival','sync','--repeat',str(repeat),
          '--retain','yes','--confirmation-consumer','two_lane','--watchdog-seconds','2.0',
          '--service-timeout','240.0','--wall-timeout','420.0']
        if traffic=='F2':argv += ['--fixture',P+'/F2_INPUT_FIXTURE_v1.json']
        cells.append(dict(cell_id=cell_id,policy=policy,traffic=traffic,repeat=repeat,cohort='OLD_DEVELOPMENT_16',
          adapter='qwen',method='standard_fair',rho=1,sessions=16,arrival='sync',retain='yes',
          confirmation_consumer='two_lane',watchdog_seconds=2.0,
          manifest=MANIFEST,manifest_sha256=sha(OLD),fixture=P+'/F2_INPUT_FIXTURE_v1.json' if traffic=='F2' else None,
          fixture_sha256=sha(FIXTURE) if traffic=='F2' else None,output=output,argv=argv,run_order_index=index,
          paired_block=f'{traffic}-r{repeat}',status='NOT_STARTED_BY_PREPARATION'))
    plan=dict(experiment_id='REVTRACE-PHYSRET-MINIMUM-STRONG-CONTROLS-V2-20261028',
      status='FROZEN_12_CONTROL_CELLS_NOT_STARTED_BY_PREPARATION',code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,
      execution_source=P+'/source_v2',source_manifest=P+'/SOURCE_v2.json',cells=cells,
      original_audio_manifest=MANIFEST,original_audio_manifest_sha256=sha(OLD),fixture=P+'/F2_INPUT_FIXTURE_v1.json',fixture_sha256=sha(FIXTURE),
      evidence_tier='known development sources; controlled wrong-conditioning MODEL INPUT in F2; no natural incidence or new-source generalization claim',
      order='clean r0 forward; F2 r0 [no_cancel,watchdog,parent,causal]; F2 r1 opposite; clean r1 opposite. All order frozen before controls.',
      scope='required strong controls and bounded failed-opportunity diagnosis; not expansion of physical-retirement study or confirmation-data selection',
      shared_contract=dict(model=B+'/models/Qwen3-ASR-1.7B',authority_rho=1,fine_seconds=2.,display_slo_seconds=2.,commit_slo_seconds=8.,
        proposal_dtype='float16',authority_dtype='float32',proposal_GPU=0,authority_GPU=1,microbatch=16,max_new_tokens=256,
        method='standard_fair',retain='yes',confirmation_consumer='two_lane',full_kernel=True,event_cow=True,D1=True,
        input_WAL=True,canonical_WAL=True,actual_Consumer=True,watchdog_seconds=2.0),
      policy_roles=dict(no_cancel='shared actuator with no cancellation requests; F2 cost/critical-path reference',
        watchdog='ordinary frozen2s timeout; never tune using control or heldout results',
        parent='conservative parent-version cancellation; count lost useful work and original obligations',
        causal='covered target or explicitly retired branch generation; preserve otherwise compatible work',
        row_complete='original full-row execution for clean normal-overhead comparison'),
      matched_original_pair=dict(plan=P+'/SERVICE_PILOT_v2_CONFIG.json',
        policies=['row_complete','covered'],repeats=[0,1],
        source_commit=COMMIT,role='already separately frozen original/simple-covered pair; compare only source/input/fixture matched raw'),
      evaluation=dict(service='actual unrelated-session Consumer stalls, legal progress and original D2/C8 goodput, not merely token/lease reduction',
        resources='actual neural phases, cancellation terminal/drain clocks, masked residual work, both-GPU energy and complete cold/serving intervals',
        normal_cost='clean row_complete vs no_cancel matched repeat; all instrumentation/checking costs remain charged',
        safety_quality='full selected state/Consumer/input obligations and WER/CER remain mandatory; ordinary timeout may sacrifice useful work',
        inference='two fresh-process repeats share the same16 sources; report both values and do not treat rows/repeats as independent new anomalies'),
      gate='execution/safety failure preserves raw and requires a new committed source for repair. Negative/inconclusive service value closes expansion; do not alter fixedwatchdog, sources or110-cell H3 plan.',
      required_prelaunch='retirement_campaign and every service cell verify clean full source, freeze environment/config/command/input hashes and experiment/result/gate paths before launching; GPU must be idle; caller owns its child only',
      heldout_consumption=0,new_ASR_calls_by_preparation=0,
      workload=dict(cells=12,F2_cells=8,clean_cells=4,unique_audio_seconds=sum(r['duration'] for r in rows),
        offered_audio_seconds_all_cells=12*sum(r['duration'] for r in rows),outer_timeout_seconds_per_cell=420.,serial_timeout_budget_seconds=5040.,
        GPU_boards_per_cell=2,scope='descriptive frozen work and upper timeout budget; no predicted or measured speedup'))
    output=HERE/'SERVICE_CONTROLS_PLAN_v2.json';output.write_text(json.dumps(plan,indent=2,allow_nan=False)+'\n')
    receipt=dict(plan=output.name,plan_sha256=sha(output),plan_bytes=output.stat().st_size,
      remote_plan=P+'/SERVICE_CONTROLS_PLAN_v2_FROZEN.json',code_commit=COMMIT,source_manifest_sha256=SOURCE_SHA,
      fixture_sha256=sha(FIXTURE),builder_sha256=sha(Path(__file__)),cells=12,ASR_calls_by_preparation=0)
    (HERE/'SERVICE_CONTROLS_PLAN_v2_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
