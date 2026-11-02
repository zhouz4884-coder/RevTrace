"""Freeze inputs after NN16 terminates; never run during a live GPU campaign."""
from __future__ import annotations
import argparse,pathlib
from analysis_common import read,put,sha,inventory,need,verify_source,OBSERVER,DRIVER,NN4F

def main():
    p=argparse.ArgumentParser()
    for n in ('cpu-campaign','nn-campaign','observer-source','observer-manifest','driver-source','driver-manifest','out','raw-root'):p.add_argument('--'+n,required=True)
    a=p.parse_args();cpu=pathlib.Path(a.cpu_campaign);nn=pathlib.Path(a.nn_campaign)
    need(read(cpu/'GATE.json')['status']=='COMPLETE_FROZEN_COST_CPU_CAMPAIGN','CPU12 incomplete')
    need(read(nn/'GATE.json')['status']=='COMPLETE_FROZEN_COST_NN_CAMPAIGN','NN16 must finish before analysis input hashing')
    observer=verify_source(a.observer_source,a.observer_manifest,OBSERVER);driver=verify_source(a.driver_source,a.driver_manifest,DRIVER)
    cs=read(cpu/'SUMMARY.json');ns=read(nn/'SUMMARY.json');need(cs['cpu_cells']==12 and ns['NN_cells']==16,'cost matrix incomplete')
    files=[]
    for root in (cpu,nn):files.extend(root/n for n in ('SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','DRIVER_CONFIG.json'))
    for cell in cs['cells']+ns['cells']:
        root=pathlib.Path(cell['raw_result_location']);files.extend(root/n for n in ('SUMMARY.json','GATE.json','DRIVER_SPAN_AUDIT.json','facts.wal'))
        if cell['phase']=='nn':
            files.extend(root/n for n in ('CONFIG.json','ORIGIN.json','SERVICE_END.json','facts.wal','consumer.jsonl','publications.jsonl','owner_e0/worker_results.jsonl'))
            files.append(nn/'external'/(cell['cell_id']+'.jsonl'))
    inputs=inventory(files);out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False);raw=pathlib.Path(a.raw_root)
    calibration=dict(experiment_id='COST_NULL_TARGET_CLOCK_FLOOR_CALIBRATION_V1',loops=4096,repeats=8,warmup=512,
        observer_source=a.observer_source,observer_manifest=a.observer_manifest,observer_identity=observer,
        NN_terminal_gate=str(nn/'GATE.json'),terminal_inputs=inventory([nn/'GATE.json',nn/'SUMMARY.json']),
        raw_result_location=str(raw/'clock_calibration_v1'),scope='lower-reference resolution diagnostic; never subtract from real footprints')
    put(out/'CALIBRATION.json',calibration)
    aggregate=dict(experiment_id='COST_CPU12_NN16_COMPLETE_AGGREGATION_V1',cpu_campaign=str(cpu),nn_campaign=str(nn),
        inputs=inputs,observer_identity=observer,driver_identity=driver,actual_NN_source=NN4F,
        calibration_summary=str(raw/'clock_calibration_v1'/'SUMMARY.json'),calibration_gate=str(raw/'clock_calibration_v1'/'GATE.json'),
        raw_result_location=str(raw/'aggregate_v1'),independent_acoustic_sources=2,
        accounts_must_remain_separate=['CPU complete-object replay','standalone input/binding probes','actual NN observed path','off/on total observation impact'],
        source_policy_timing_repeats_not_independent_speakers=True)
    put(out/'AGGREGATE.json',aggregate);print(str(out))

if __name__=='__main__':main()
