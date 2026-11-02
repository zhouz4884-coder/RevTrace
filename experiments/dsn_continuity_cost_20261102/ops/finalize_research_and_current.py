"""Close research decisions and restore the verified uninstrumented NN source pointer."""
from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def dump(p,x):
    p=Path(p);assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
required=[
 ('history/RESULTS_H_ALL_V3/GATE.json','PASS_COMPLETENESS_AND_RECORDED_INPUT_GATES'),
 ('history/RESULTS_H_CURRENT_S_ON_V3/GATE.json','PASS_COMPLETENESS_AND_RECORDED_INPUT_GATES'),
 ('history/RESULTS_H_AUDIT_REPORTED_V2/GATE.json','PASS_INDEPENDENT_H_GAP_RECOUNT'),
 ('cost/RESULTS_COST_CPU_V1/GATE.json','COMPLETE_FROZEN_COST_CPU_CAMPAIGN'),
 ('cost/RESULTS_COST_NN_V1/GATE.json','COMPLETE_FROZEN_COST_NN_CAMPAIGN'),
 ('cost/FINAL_CALIBRATION/GATE.json','PASS_FIXED_NULL_TARGET_CLOCK_CALIBRATION'),
 ('cost/FINAL_AGGREGATE/GATE.json','PASS_COMPLETE_CPU12_NN16_UNSUBTRACTED_COST_ACCOUNTING'),
 ('review/FINAL_COST_INDEPENDENT/GATE.json','PASS_INDEPENDENT_COST_RECOUNT'),
 ('cost/FINAL_C4_CLOSURE/ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json','PASS_COMPLETE_ORIGINAL_C4_NN16_TRACE_CLOSURE'),
]
bound=[]
for name,status in required:
    p=E/name;j=read(p);assert j['status']==status,(name,j)
    bound.append(dict(path=name,sha256=sha(p),status=status))
assert read(E/'cost/FINAL_C4_CLOSURE/ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json')['root_actual_trace_recheck_pending'] is False
assert read(E/'FINAL_RESOURCE_CLOSURE.json')['CUDA_compute_processes']==''
qa=read(E/'paper_qa/FINAL_QA.json');cold=read(E/'paper_qa/COLD_BUILD_QA.json');visual=read(E/'paper_qa/VISUAL_REVIEW_v10.json')
assert qa['pdf_sha256']==cold['pdf_sha256']==visual['pdf_sha256']
assert qa['pages']==12 and qa['technical_pages']==11 and qa['cited_references']==31
identity=R/'experiments/repository_identity_20261027';before=E/'MACHINE_LOCAL_CURRENT_BEFORE_FINAL_RESTORE.json'
assert not before.exists();before.write_bytes((identity/'CURRENT.json').read_bytes())
pointer=read(E/'CURRENT_BEFORE_COST_V1_CONTROLS.json')
assert pointer['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
pointer.update(updated_date='2026-11-02',research_state=str(E/'FINAL_RESEARCH_REPORT.zh.md'),
    GPU_queue='COST_CPU12_NN16_ALL_CHECKS_COMPLETE_CUDA_EMPTY',
    scope='Default next-run source is the original clean NN4f. Observer/driver/analysis/checker commits retain separate completed run identities; no historical run relabelled.',previous_pointer=str(before))
(identity/'CURRENT.json').write_bytes((json.dumps(pointer,indent=2)+'\n').encode())
gate=E/'FINAL_CURRENT_SOURCE_GATE.json'
subprocess.run([sys.executable,'-B',str(identity/'preflight.py'),'--output',str(gate)],cwd=R,check=True,capture_output=True)
dump(E/'MACHINE_LOCAL_CURRENT_FINAL.json',pointer)
history=read(E/'history/RESULTS_H_ALL_V3/SUMMARY.json');current=read(E/'history/RESULTS_H_CURRENT_S_ON_V3/SUMMARY.json')
record=dict(gate='PASS_RESEARCH_AND_SELECTED_MANUSCRIPT_RESOURCE_CLOSURE',client_date='2026-11-02',
    required_receipts=bound,historical_attempts=287,historical_fully_bound=218,historical_unknown=69,current_S_on_cases=90,
    historical_selector_decision='ARTIFACT_ONLY_NO_CURRENT_JOINT_INCREMENTAL_OPPORTUNITY_NO_ONLINE_EXTENSION',
    actual_current_CPU_replays=12,actual_current_NN_trials=16,independent_cost_recount_cases=28,
    original_C4_actual_NN_rechecks=16,actual_trace_pending=False,coarse_cost_evidence_adopted_in_main=True,
    policy_within_pair_counterbalance_achieved=False,causal_observation_tax_or_speed_claimed=False,
    new_neural_scheduler_opportunity_established=False,additional_NN_not_justified_for_adopted_footprint_claim=True,
    cost_source='3cf7cd10a3ba76958b4173aa20eb6116ac779a39',actual_NN_source=pointer['source_commit'],
    final_default_source_gate_sha256=sha(gate),resource_closure_sha256=sha(E/'FINAL_RESOURCE_CLOSURE.json'),
    final_pdf_sha256=qa['pdf_sha256'],source_zip_sha256=cold['source_zip_sha256'],paper_QA_sha256=sha(E/'paper_qa/FINAL_QA.json'),
    cold_build_QA_sha256=sha(E/'paper_qa/COLD_BUILD_QA.json'),visual_QA_sha256=sha(E/'paper_qa/VISUAL_REVIEW_v10.json'),
    technical_pages=11,reference_pages=1,cited_references=31,original_v9_preserved=True,
    legacy_dirty_HEAD_preserved=True,raw_models_environments_large_results_on8TB=True,
    publication_receipt='DELIVERY_RECEIPT.json (written only after actual remote publication)',conference_submission_performed=False)
dump(E/'FINAL_RELEASE_GATE.json',record)
print(json.dumps({k:v for k,v in record.items() if k not in {'required_receipts'}}))
