"""Metadata-only frozen input index. No raw reader or model invocation."""
from __future__ import annotations
import argparse,pathlib
from sensitivity_common import SOURCE_RECEIPT_SHA,read,sha,put,need
def main():
    p=argparse.ArgumentParser()
    for n in ('matched-dir','resident-dir','source-receipt','out','raw-out'):p.add_argument('--'+n,required=True)
    p.add_argument('--render',action='store_true');a=p.parse_args()
    matched,resident=pathlib.Path(a.matched_dir),pathlib.Path(a.resident_dir)
    need(read(matched/'GATE.json')['status']=='COMPLETE_PAIRED32_ACTUAL_SERVICE_AND_REFERENCE_AUDIT','matched gate changed')
    need(read(resident/'GATE.json')['status']=='PASS_RESIDENT4_COMPLETE_FROZEN_SCOPE','resident gate changed')
    need(sha(a.source_receipt)==SOURCE_RECEIPT_SHA,'original source receipt frozen hash differs')
    paths=[root/name for root in (matched,resident) for name in ('SUMMARY.json','GATE.json','CONFIG.json')]+[pathlib.Path(a.source_receipt)]
    cfg=dict(experiment_id='REVTRACE_FINAL4F_ARCHIVED_D2_SENSITIVITY_20261102_V1',
        matched_summary=str(matched/'SUMMARY.json'),resident_summary=str(resident/'SUMMARY.json'),source_receipt=a.source_receipt,
        inputs={str(x):dict(bytes=x.stat().st_size,sha256=sha(x)) for x in paths},
        tau_d_grid=[.5+i*.25 for i in range(23)],tau_c=8.,
        scope='posthoc fixed-grid display-budget sensitivity on existing final4f matched/resident actual endpoints',
        original_D2_C8_pass_and_P99_must_be_preserved=True,source_unit='speaker; combine two timing repeats inside source; banks reuse same four speakers',
        render_figures=a.render,raw_result_location=a.raw_out)
    put(a.out,cfg)
if __name__=='__main__':main()

