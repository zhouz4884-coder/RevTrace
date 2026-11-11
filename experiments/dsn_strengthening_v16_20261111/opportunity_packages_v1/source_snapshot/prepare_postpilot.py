"""POSTPILOT IDLE ONLY: freeze fixed24 input hashes; no outcome-based selection."""
from pathlib import Path
import argparse,datetime,importlib.metadata,json,platform,sys
from contracts import B,NN,DRIVER,NN_MANIFEST,DRIVER_MANIFEST,PLAN,V5,read,put,sha,disk,source,idle

def main():
    p=argparse.ArgumentParser()
    for key in ('manifest','plan','idle-receipt','out-dir','raw-out'):p.add_argument('--'+key,required=True)
    a=p.parse_args();idle(a.idle_receipt)
    own=source(Path(__file__).resolve().parent,a.manifest)
    if sha(a.plan)!=PLAN or sha(Path(__file__).parent/'V5_CONTRACT.json')!=V5:raise ValueError('declared v5/24cell plan changed')
    plan=read(a.plan)
    if plan['expected_trials']!=24 or plan['expected_source_count']!=2:raise ValueError('not fixed PILOT24 scope')
    runtime=source(plan['actual_NN']['source_root'],plan['actual_NN']['source_manifest'],NN)
    driver=source(plan['driver']['source_root'],plan['driver']['source_manifest'],DRIVER)
    if runtime['source_manifest_sha256']!=NN_MANIFEST or driver['source_manifest_sha256']!=DRIVER_MANIFEST:raise ValueError('wrong complete dependencies')
    records={};missing=[]
    def add(path,required=True):
        path=Path(path)
        if not path.exists():
            if required:missing.append(str(path))
            return
        if not path.resolve().is_relative_to(B):raise ValueError('raw dependency escaped8TB')
        records[str(path.resolve())]=dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha(path))
    for path in (a.plan,a.idle_receipt,plan['actual_NN']['source_manifest'],plan['driver']['source_manifest']):add(path)
    add(plan['selection_receipt']['path'])
    seen_refs=set()
    def add_reference(path):
        if path in seen_refs:return
        seen_refs.add(path);add(path);ref=read(path)
        for key in ('reference_details','reference_gate','genesis'):add(ref[key]['path'])
        if ref.get('selection_receipt',{}).get('path'):add(ref['selection_receipt']['path'])
        parent_selection=ref.get('measured_parent_selection')
        if parent_selection:
            add(parent_selection['path']);selection=read(parent_selection['path'])
            if selection.get('parent_bank_receipt'):add(selection['parent_bank_receipt']['path'])
        if ref.get('measured_parent_reference'):add_reference(ref['measured_parent_reference']['path'])
    add_reference(plan['reference_receipt']['path'])
    for c in plan['cells']:
        add(c['config']);config=read(c['config'])
        if sha(c['config'])!=c['config_sha256']:raise ValueError('frozen cell config changed')
        root=Path(c['out'])
        for name in ('CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','SUMMARY.json','GATE.json','GENESIS.json','ORIGIN.json','facts.wal','consumer.jsonl','publications.jsonl','supervisor.jsonl','ingress.jsonl','JOB_ACCOUNTING.json','EXTERNAL_NEW_TEST_AUDIT.json'):add(root/name)
        for folder in root.glob('owner_e*'):
            if folder.is_dir():
                for name in ('dispatch.jsonl','owner_events.jsonl','worker_results.jsonl','policy_audit.jsonl'):add(folder/name)
                add(folder/'state_sizes.jsonl',False)
        add(c['external_power'])
        for key in ('reference_details','reference_gate'):add(config[key])
    for name in ('CONFIG.json','SUMMARY.json','GATE.json'):add(Path(plan['raw_result_location'])/name)
    out=disk(a.out_dir);out.mkdir(parents=True,exist_ok=False);raw=disk(a.raw_out)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),numpy=importlib.metadata.version('numpy'),
             CUDA_VISIBLE_DEVICES='',models_loaded=False,new_model_calls=0)
    put(out/'ENVIRONMENT.json',env)
    cfg=dict(experiment_id='REVTRACE-V16-PILOT-OPPORTUNITY-AUDIT-20261111-V1',pilot_plan=str(Path(a.plan).resolve()),pilot_plan_sha256=PLAN,
        v5_contract_sha256=V5,runtime=runtime,driver=driver,actual_audit_source=own,
        idle_receipt=str(Path(a.idle_receipt).resolve()),idle_receipt_sha256=sha(a.idle_receipt),expected_controls=22,
        bound_files=list(records.values()),missing_inputs_preserved=missing,raw_result_location=str(raw),
        aggregate_summary_location=str(raw/'SUMMARY.json'),gate_decision_location=str(raw/'GATE.json'),
        rule='Whole fixed24, no point selection, no alternate schedule; presence separate from technical conformance',new_model_calls=0)
    put(out/'CONFIG.json',cfg)
    put(out/'PREPARATION_RECORD.json',dict(record_type='POSTPILOT_INPUT_FREEZE_NOT_OPPORTUNITY_RESULT',code_commit=own['code_commit'],
        config_sha256=sha(out/'CONFIG.json'),environment_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(raw),
        expected_cells=24,input_files=len(records),missing_inputs=missing,new_model_calls=0,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    idle(a.idle_receipt);print(str(out/'CONFIG.json'))
if __name__=='__main__':main()
