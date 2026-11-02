from pathlib import Path
import hashlib,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1];paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v11'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def write(p,x):
 p=Path(p);assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
required=[('sensitivity/RESULTS_v1/GATE.json','PASS_FROZEN_D2_POSITIVE_CONTROL_AND_SOURCE_PAIRED_SENSITIVITY'),('selection/ACQUISITION_RESULTS_v2/GATE.json','PASS_STRICT_METADATA_SELECTED_SPEAKER_DISJOINT_AUDIO_AVAILABLE'),('confirmation/REFERENCE_RESULTS_v1/GATE.json','PASS_CONTINUOUS_ORIGINAL_AND_RESTORED_SHORT_REFERENCES'),('confirmation/SERVICE_RESULTS_v1/GATE.json','COMPLETE_FROZEN_NEW_TEST_CONFIRMATION_TASK_AND_ENDPOINTS'),('confirmation/FINAL_C4_CLOSURE/GATE.json','PASS_COMPLETE_ORIGINAL_C4_CONFIRM32_TRACE_CLOSURE'),('confirmation/FINAL_REPORT/GATE.json','PASS_COMPLETE_NEW8_CONFIRMATION_REPORT')]
bound=[]
for n,status in required:
 p=E/n;assert read(p)['status']==status;bound.append(dict(path=n,sha256=sha(p),status=status))
data=read(E/'confirmation/FINAL_REPORT/PAPER_DATA.json');assert data['trials']==32 and data['independent_speakers']==8 and data['C4']['checked_selected_steps']==564
qa=read(E/'paper_qa/FINAL_QA.json');cold=read(E/'paper_qa/COLD_BUILD_QA.json');visual=read(E/'paper_qa/VISUAL_REVIEW_v11.json');fig=read(E/'review/FIGURE_INDEPENDENT_REVIEW.json')
assert qa['pdf_sha256']==cold['pdf_sha256']==visual['pdf_sha256']==sha(paper/'main.pdf')
assert not visual['issues_remaining'] and fig['status']=='PASS_READ_ONLY_FINAL_FIGURE_REVIEW' and fig['measured_minimum_PDF_font_pt']>=8
assert qa['pages']==12 and qa['cited_references']==31 and cold['source_zip_files']==29
assert read(E/'confirmation/SERVICE_RUN_V1_RESOURCE_CLOSURE.json')['cells']==32
assert read(E/'confirmation/REPORT_RUN_V2_RESOURCE_CLOSURE.json')['CUDA_compute_processes']==''
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
assert sha(R/'Paper_DSN/revisions/20261102_dsn2027_release_v10/main.pdf')=='a0eec6e45bab9660d6167856d40990f097874cf7159c9124d206dd5b3db86ddb'
identity=R/'experiments/repository_identity_20261027';before=E/'MACHINE_LOCAL_CURRENT_BEFORE_FINAL_RESTORE.json';before.write_bytes((identity/'CURRENT.json').read_bytes())
pointer=read(E/'CURRENT_BEFORE_SENSITIVITY_V1_CONTROLS.json');assert pointer['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
pointer.update(updated_date='2026-11-02',research_state=str(E/'FINAL_RESEARCH_REPORT.zh.md'),GPU_queue='NN32_C4_32_REPORT_COMPLETE_CUDA_EMPTY',scope='Default next-run source is original clean NN4f; all selection/reference/service-controller/checker/analysis/plot commits retain their actual distinct run identities.',previous_pointer=str(before))
(identity/'CURRENT.json').write_text(json.dumps(pointer,indent=2)+'\n',encoding='utf-8')
gate=E/'FINAL_CURRENT_SOURCE_GATE.json';subprocess.run([sys.executable,'-B',str(identity/'preflight.py'),'--output',str(gate)],cwd=R,check=True,capture_output=True);write(E/'MACHINE_LOCAL_CURRENT_FINAL.json',pointer)
release=dict(gate='PASS_COMPLETE_NEW8_RESEARCH_AND_SELECTED_DSN_V11_RELEASE',required_receipts=bound,new_independent_speakers=8,new_service_trials=32,selected_transitions=564,actual_trace_pending=False,source_paired_bootstrap_draws=20000,primary_paired_gain=data['bootstrap']['intervals']['duration_weighted_ratio_gain_pp'],quality_unchanged=True,original_D2_C8_and_all_EOS_preserved=True,actual_NN_source=pointer['source_commit'],analysis_source=data['analysis_identity']['source_commit'],final_pdf_sha256=qa['pdf_sha256'],source_zip_sha256=cold['source_zip_sha256'],technical_pages=11,reference_pages=1,cited_references=31,abstract_words=cold['abstract_words'],native_figure_source=fig['source_commit'],paper_QA_sha256=sha(E/'paper_qa/FINAL_QA.json'),cold_build_QA_sha256=sha(E/'paper_qa/COLD_BUILD_QA.json'),visual_QA_sha256=sha(E/'paper_qa/VISUAL_REVIEW_v11.json'),figure_independent_review_sha256=sha(E/'review/FIGURE_INDEPENDENT_REVIEW.json'),resource_closure_sha256=sha(E/'confirmation/REPORT_RUN_V2_RESOURCE_CLOSURE.json'),default_source_gate_sha256=sha(gate),baseline_v10_preserved=True,legacy_dirty_HEAD_preserved=True,raw_models_datasets_environments_large_results_on8TB=True,conference_submission_performed=False,publication_receipt='DELIVERY_RECEIPT.json written after actual remote verification')
write(E/'FINAL_RELEASE_GATE.json',release)
current='''# Current RevTrace manuscript — 2026-11-02, v11

- [Manuscript PDF](revisions/20261102_dsn2027_release_v11/main.pdf)
- [Main LaTeX](revisions/20261102_dsn2027_release_v11/main.tex)
- [Anonymous source ZIP](revisions/20261102_dsn2027_release_v11/RevTrace_DSN2027_anonymous_source_v11.zip)
- [Research results and decisions](../experiments/dsn_native_confirmation_20261102/FINAL_RESEARCH_REPORT.zh.md)
- [Editorial selection](../experiments/dsn_native_confirmation_20261102/EDITORIAL_DELTA_v11.zh.md)
- [Complete independent native data](../experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json)
- [Research/package/resource gate](../experiments/dsn_native_confirmation_20261102/FINAL_RELEASE_GATE.json)
- [Preserved v10 PDF](revisions/20261102_dsn2027_release_v10/main.pdf)

The independent confirmation completes32 real service trials on8 previously unused speakers with the final original4f implementation. Timely D2/C8 audio coverage rises40.6%→93.9%; whole-run passes0/16→10/16. The speaker-paired gain is53.3pp with95% interval[44.8,59.6]. Matching whole-view timely coverage rises47.000→107.162s; original task and final quality remain unchanged.

The paper has11 technical pages plus one references-only page with31 works, four vector figures and six tables. All12 pages, grayscale main figures, numeric bindings and embedded fonts passed review. The29-file anonymous source package compiles from a fresh directory to12 pixel-identical pages.

All original models/data/raw logs remain on the designated8TB disk. Source identities and generation-bound resource release are recorded separately. The v10 release and legacy manuscripts remain preserved. No conference submission has been performed.
'''
(R/'Paper_DSN/CURRENT.md').write_text(current,encoding='utf-8')
latest=dict(date='2026-11-02',status='COMPLETE_NEW8_INDEPENDENT_CONFIRMATION_AND_SELECTIVE_DSN_V11',report='dsn_native_confirmation_20261102/FINAL_RESEARCH_REPORT.zh.md',final_gate='dsn_native_confirmation_20261102/FINAL_RELEASE_GATE.json',paper='Paper_DSN/revisions/20261102_dsn2027_release_v11/main.pdf',paper_QA_record='dsn_native_confirmation_20261102/paper_qa/FINAL_QA.json',new_actual_NN_trials=32,new_independent_speakers=8,new_selected_transitions=564,whole_run_passes=dict(conservative='0/16',RevTrace='10/16'),primary_coverage_gain=data['bootstrap']['intervals']['duration_weighted_ratio_gain_pp'],actual_trace_pending=False,cited_references=31,technical_pages=11,references_pages=1,previous_complete_paper='Paper_DSN/revisions/20261102_dsn2027_release_v10/main.pdf',conference_submission_performed=False)
(R/'experiments/LATEST_RESEARCH.json').write_text(json.dumps(latest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in release.items() if k!='required_receipts'}))
