from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v12'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def put(p,x):
 p=Path(p);assert not p.exists();p.write_bytes((json.dumps(x,indent=2)+'\n').encode())
baseline=read(E/'baseline/FROZEN_V11_INPUTS.json')
for row in baseline['rows']:
 p=R/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
trace=read(E/'analysis/FINAL/SUMMARY.json');assert trace['status']=='PASS_COMPLETE32_RECORDED_TRACE_ACCOUNTING'
assert trace['raw_inputs_before_after_unchanged'] and trace['all32_original_endpoint_fields_conserved'] and trace['controls']['tests']==9
resource=read(E/'FINAL_RESOURCE_AND_RAW_CLOSURE.json');assert resource['status'].startswith('PASS') and resource['original_recorded_inputs_verified']==420 and resource['CUDA_compute_owners']==''
qa=read(E/'paper_qa/FINAL_QA.json');cold=read(E/'paper_qa/COLD_BUILD_QA.json');visual=read(E/'paper_qa/VISUAL_REVIEW_v12.json');pre=read(E/'SUBMISSION_PREFLIGHT.json')
assert qa['pdf_sha256']==cold['pdf_sha256']==visual['pdf_sha256']==pre['pdf_sha256']==sha(paper/'main.pdf')
assert qa['method_propositions_proofs_equations_unchanged'] and qa['all_four_figures_unchanged'] and not visual['issues_remaining']
assert qa['pages']==12 and qa['cited_references']==31 and cold['abstract_words']==130
assert (E/'review/COLD_READ.zh.md').exists() and (E/'review/FINAL_EVENT_INTERPRETATION_REVIEW.zh.md').exists()
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
identity=R/'experiments/repository_identity_20261027';before=E/'MACHINE_LOCAL_CURRENT_BEFORE_FINAL_RESTORE.json';before.write_bytes((identity/'CURRENT.json').read_bytes());pointer=read(E/'baseline/MACHINE_CURRENT.json')
assert pointer['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
pointer.update(research_state=str(E/'FINAL_REPORT.zh.md'),GPU_queue='CLOSURE_CPU_ONLY_COMPLETE_NO_GPU_MATRIX_CUDA_EMPTY',previous_pointer=str(before),scope='Default next-run source remains original clean NN4f. Original v11 and independent confirmation frozen; recorded-event CPU analysis and editorial v12 have separate identities.')
(identity/'CURRENT.json').write_bytes((json.dumps(pointer,indent=2)+'\n').encode());gate=E/'FINAL_DEFAULT_SOURCE_GATE.json'
subprocess.run([sys.executable,'-B',str(identity/'preflight.py'),'--output',str(gate)],cwd=R,check=True,capture_output=True);put(E/'MACHINE_LOCAL_CURRENT_FINAL.json',pointer)
evidence=[]
for name in ['baseline/FROZEN_V11_INPUTS.json','analysis/FINAL/GATE.json','analysis/FINAL/SUMMARY.json','review/EVENT_CLAIMS.json','review/COLD_READ.zh.md','COLD_READ_DISPOSITION.zh.md','review/FINAL_EVENT_INTERPRETATION_REVIEW.zh.md','paper_qa/FINAL_QA.json','paper_qa/COLD_BUILD_QA.json','paper_qa/VISUAL_REVIEW_v12.json','SUBMISSION_PREFLIGHT.json','FINAL_RESOURCE_AND_RAW_CLOSURE.json','FINAL_DEFAULT_SOURCE_GATE.json']:
 p=E/name;evidence.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
release=dict(status='PASS_LOCAL_GOAL_SCOPE_RECORDED_EVENT_AND_EDITORIAL_CLOSURE',v11_baseline_files_preserved=baseline['files'],original_NN_source=pointer['source_commit'],original_NN_source_clean=True,original_independent_bank_trials=32,original_independent_speakers=8,method_changed=False,new_NN_trials=0,new_GPU_matrix=False,runtime_patch_created=False,runtime_repair_decision='NO_GO_NO_ESTABLISHED_CORRECTNESS_DEFECT_OR_STRONG_END_TO_END_REPAIR_OPPORTUNITY',diagnostic_parser_repair_separately_frozen=True,diagnostic_analysis_source=read(E/'analysis/FINAL/RUN_RECORD_FINAL.json')['code_commit'],recorded_input_files=420,recorded_input_bytes=trace['raw_input_bytes'],recorded_endpoint_rows=564,recorded_job_rows=610,recorded_endpoints_original_values_preserved=True,independent_cold_read_done=True,pre_submission_artifact_checks_passed=True,technical_pages=11,reference_pages=1,cited_references=31,pdf_sha256=qa['pdf_sha256'],source_zip_sha256=cold['source_zip_sha256'],evidence=evidence,no_further_method_branch=True,legacy_dirty_HEAD_preserved=True,conference_submission_performed=False,remote_delivery='verified separately after publication')
put(E/'FINAL_RELEASE_GATE.json',release)
current='''# Current RevTrace manuscript — v12 editorial closure, 2026-11-02

- [Manuscript PDF](revisions/20261102_dsn2027_release_v12/main.pdf)
- [Main LaTeX](revisions/20261102_dsn2027_release_v12/main.tex)
- [Anonymous source ZIP](revisions/20261102_dsn2027_release_v12/RevTrace_DSN2027_anonymous_source_v12.zip)
- [Recorded-event explanation and decisions](../experiments/dsn_v11_closure_20261102/FINAL_REPORT.zh.md)
- [Cold-read disposition](../experiments/dsn_v11_closure_20261102/COLD_READ_DISPOSITION.zh.md)
- [Closure gate](../experiments/dsn_v11_closure_20261102/FINAL_RELEASE_GATE.json)
- [Frozen v11 PDF](revisions/20261102_dsn2027_release_v11/main.pdf)
- [Frozen independent native results](../experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json)

v12 changes writing only. The original4f method, v11 and its32-trial/eight-speaker independent confirmation remain frozen. The primary paired coverage gain remains53.3pp (95% interval[44.8,59.6]); all eight source pairs are positive. Original coverage40.6%→93.9% and original whole-run passes0/16→10/16 are unchanged.

Existing events explain the six remaining deadline failures. S0915 contributes6.996125 of8.404125 uncredited audio-s; repeated full-input refutations and original inference intervals accumulate on the delivery path. S0901 and S0902 have distinct late-input/recognition and refutation paths. The closure uses CPU-only accounting; it creates no runtime patch or new GPU matrix.

The paper retains11 technical pages plus one references-only page,31 cited works, four unchanged vector figures, and unchanged propositions/proofs/equations. The29-file anonymous source package cold-compiles to12 pixel-identical pages. Independent cold reading, numeric bindings, full-page color/grayscale review and pre-submission artifact checks are complete. No conference submission has been performed.
'''
(R/'Paper_DSN/CURRENT.md').write_bytes(current.encode())
latest=dict(date='2026-11-02',status='COMPLETE_FROZEN_V11_EVENT_EXPLANATION_AND_EDITORIAL_V12_CLOSURE',report='dsn_v11_closure_20261102/FINAL_REPORT.zh.md',final_gate='dsn_v11_closure_20261102/FINAL_RELEASE_GATE.json',paper='Paper_DSN/revisions/20261102_dsn2027_release_v12/main.pdf',new_actual_NN_trials=0,reused_frozen_independent_trials=32,reused_frozen_independent_speakers=8,method_changed=False,v11_confirmation_relabelled=False,CPU_recorded_endpoint_rows=564,CPU_recorded_job_rows=610,diagnostic_analysis_source=release['diagnostic_analysis_source'],runtime_patch_created=False,new_GPU_matrix=False,independent_cold_read_complete=True,submission_preflight_complete=True,no_further_method_branch=True,cited_references=31,technical_pages=11,references_pages=1,previous_frozen_paper='Paper_DSN/revisions/20261102_dsn2027_release_v11/main.pdf',conference_submission_performed=False)
(R/'experiments/LATEST_RESEARCH.json').write_bytes((json.dumps(latest,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in release.items() if k!='evidence'}))
