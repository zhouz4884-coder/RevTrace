"""Only in a Root-allocated idle window: freeze exact reused inputs and env."""
from pathlib import Path
import argparse,datetime,importlib.metadata,platform,sys
from provenance import *

def main():
    p=argparse.ArgumentParser()
    for k in ('manifest','op-config','op-gate','idle-receipt','out-dir','raw-out'):p.add_argument('--'+k,required=True)
    a=p.parse_args();idle(a.idle_receipt)
    own=source(Path(__file__).resolve().parent,a.manifest)
    if sha(a.op_config)!=OP_CONFIG:raise ValueError('wrong previously frozen all24 input list')
    old=read(a.op_config)
    if old['pilot_plan_sha256']!=PLAN or sha(old['pilot_plan'])!=PLAN:raise ValueError('whole24 plan changed')
    if read(a.op_gate).get('status')!='PASS_COMPLETE_ALL24_OPPORTUNITY_BINDINGS' or read(a.op_gate).get('code_commit')!=OP:raise ValueError('prior complete actual bindings absent')
    runtime=source(old['runtime']['source_root'],old['runtime']['source_manifest'],NN)
    driver=source(old['driver']['source_root'],old['driver']['source_manifest'],old['driver']['code_commit'])
    auditor=source(old['actual_audit_source']['source_root'],old['actual_audit_source']['source_manifest'],OP)
    check_files(old['bound_files'])
    out=disk(a.out_dir);out.mkdir(parents=True,exist_ok=False);raw=disk(a.raw_out)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),numpy=importlib.metadata.version('numpy'),CUDA_VISIBLE_DEVICES='',models_loaded=False,new_model_calls=0)
    put(out/'ENVIRONMENT.json',env)
    records=list(old['bound_files'])
    for pth in (a.op_config,a.op_gate,a.idle_receipt):
        pp=disk(pth);records.append(dict(path=str(pp),bytes=pp.stat().st_size,sha256=sha(pp)))
    cfg=dict(experiment_id=EXPERIMENT,actual_analysis_source=own,runtime=runtime,driver=driver,actual_binding_auditor=auditor,
        pilot_plan=old['pilot_plan'],pilot_plan_sha256=PLAN,prior_OP_config=str(disk(a.op_config)),prior_OP_config_sha256=OP_CONFIG,
        idle_receipt=str(disk(a.idle_receipt)),idle_receipt_sha256=sha(a.idle_receipt),expected_controls=24,bound_files=records,
        rules=['actual_SUP','canonical_only','fixed_lag_0p5','LA2_CP'],new_audio_unit='strictly increasing actual delivered supported nonempty visible frontier; never same-F ASR/full-C twice',
        actual_task='unchanged AlignAtt then C/U then actual Consumer',external_rule='LA2 Unicode read adapter above original task, not LA-ASR replacement',
        fixed_lag_seconds=.5,deadline_D_seconds=2.,deadline_C_seconds=8.,
        raw_result_location=str(raw),aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),
        max_bounded_output_bytes=12000000,all24_no_outcome_selection=True,new_model_calls=0,live_closed_loop_effect_identified=False)
    put(out/'CONFIG.json',cfg)
    put(out/'PREPARATION_RECORD.json',dict(record_type='IDLE_INPUT_ENV_FREEZE_NOT_RESULT',experiment_id=EXPERIMENT,
        code_commit=own['code_commit'],frozen_config_sha256=sha(out/'CONFIG.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),
        bound_files=len(records),raw_result_location=str(raw),utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    idle(a.idle_receipt);print(out/'CONFIG.json')
if __name__=='__main__':main()
