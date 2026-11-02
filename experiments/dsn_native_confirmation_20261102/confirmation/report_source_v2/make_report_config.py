"""Bind terminal complete service/a13 audits; never choose a result subset."""
from __future__ import annotations
import argparse,pathlib
from report_common import CELLS,SPEAKERS,SEED,DRAWS,need,read,put,sha,inventory
def main():
    p=argparse.ArgumentParser()
    for n in ('service-plan','campaign','out','raw-out'):p.add_argument('--'+n,required=True)
    p.add_argument('--c4-summary');p.add_argument('--c4-gate');a=p.parse_args();root=pathlib.Path(a.campaign)
    plan=read(a.service_plan);summary=read(root/'SUMMARY.json');gate=read(root/'GATE.json')
    need(plan['expected_trials']==CELLS and plan['expected_source_count']==SPEAKERS,'report fixed32/8 scope differs')
    need(summary['status']==gate['status']=='COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS' and summary['completed_trials']==CELLS,'service queue not complete')
    need({c['cell_id'] for c in plan['cells']}=={c['cell_id'] for c in summary['cells']} and len(summary['cells'])==CELLS,'missing/duplicated service cells')
    paths=[a.service_plan,*[root/x for x in ('SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json')]]
    for cell in plan['cells']:
        raw=pathlib.Path(cell['out']);paths.extend(raw/x for x in ('CONFIG.json','SUMMARY.json','GATE.json','EXTERNAL_NEW_TEST_AUDIT.json'));paths.append(cell['config'])
    need(bool(a.c4_summary)==bool(a.c4_gate),'provide both C4 terminal files or neither')
    if a.c4_summary:paths.extend((a.c4_summary,a.c4_gate))
    cfg=dict(experiment_id='REVTRACE_NEW8SPEAKER_COMPLETE32_PAIRED_REPORT_20261102_V1',service_plan=a.service_plan,campaign=str(root),
        c4_summary=a.c4_summary,c4_gate=a.c4_gate,inputs=inventory(paths),expected_trials=CELLS,expected_speakers=SPEAKERS,
        bootstrap=dict(draws=DRAWS,seed=SEED,sampling='eight speakers with replacement; two repeats paired within source',CI='95 percent percentile, linear (n-1)*p'),
        source_rows_in_bootstrap_order='sorted speaker_id then source_id',raw_result_location=a.raw_out,old_four_speaker_bank_included=False)
    put(a.out,cfg)
if __name__=='__main__':main()

