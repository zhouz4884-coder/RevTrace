from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent
read=lambda f:json.loads((W/f).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[]
for folder,manifest in [('runtime','N1_SOURCE_MANIFEST.json'),('runtime_n5_v3','N5_SOURCE_MANIFEST_v3.json'),('adversarial_frozen_v2','ROLE_PROBE_SOURCE_MANIFEST_v2.json')]:
 m=read(manifest);commit=subprocess.check_output(['git','-C',str(W/folder),'rev-parse','HEAD'],text=True).strip();assert commit==m['code_commit']
 for r in m['files']:assert (W/folder/r['path']).stat().st_size==r['bytes'] and sha(W/folder/r['path'])==r['sha256']
 sources.append(dict(folder=folder,commit=commit,files=len(m['files']),manifest_sha256=sha(W/manifest)))
assert sha(Path(r'E:\Downloads\main(4).pdf'))=='ad4441834abbf31047b432ceb36c855b7efa002f4f6c33e3868a361c8125e87f'
assert read('ROLE_FORMAL_DECISION_v2.json')['status'].startswith('COMPLETE64_ALL')
assert read('N5_NORMAL_DECISION_v1.json')['CDE_extra_feedback_control_independent_performance_contribution']=='NO_GO_ON_THIS_FROZEN_NORMAL_STUDY'
assert read('n5_postfault_collected_v1/postfault_cpu_v2/SUMMARY.json')['status'].startswith('PASS21')
assert read('FINAL_RESOURCE_RELEASE_v1.json')['new_GPU_queue_closed']
assert read('REVIEW_SNAPSHOT_RECHECK_v1.json')['status'].startswith('PASS_ZIP_ALL_BYTES')
assert read('candidate_20261026/qa/FINAL_QA_v1.json')['status'].startswith('PASS_CANDIDATE')
files=['FINAL_REPORT.zh.md','UNIFIED_FAULT_MATRIX_v3.md','CONTRIBUTION_EVIDENCE_MATRIX_v3.md',
 'N1_DECISION.json','N5_NORMAL_DECISION_v1.json','N5_FORMAL_RECOVERY_REPORT.zh.md','ROLE_FORMAL_DECISION_v2.json','ROLE_FORMAL_REPORT.zh.md',
 'formal/CROSSCHECK_v2.json','formal/CDE_CROSSCHECK_v2.json','formal/INDUCTIVE_OBLIGATIONS.md','formal/ENVELOPE_OBLIGATIONS.md','formal/IMPLEMENTATION_SEMANTIC_AUDIT_v2.md',
 'candidate_20261026/main.pdf','candidate_20261026/main.tex','candidate_20261026/qa/FINAL_QA_v1.json',
 'review_snapshot_v1.zip','ANONYMOUS_SNAPSHOT_AUDIT_v1.json','REVIEW_SNAPSHOT_RECHECK_v1.json','FINAL_RESOURCE_RELEASE_v1.json',
 'role_formal_evidence_v2.tar.gz','n5_postnormal_cpu_bounded_v1.tar.gz','n5_postfault_cpu_bounded_v1.tar.gz',
 'figures/causal_protocol_v1.pdf','figures/cost_boundary_v1.pdf','figures/normal_cost_v2.pdf']
for folder in ['final_matrices_v3','synthesis_data_v2']:
 files.extend(p.relative_to(W).as_posix() for p in (W/folder).iterdir() if p.is_file())
out=dict(status='COMPLETE_BOUNDED_RESEARCH_AND_CANDIDATE_FINAL_PUBLICATION_VERIFICATION_SEPARATE',
 original_scope=['P0','P1/N1','P2','P3','P4','P5'],additional_scope=['five-modeCDE','independentnormal105','independentrecovery21','conditionalrolefeedback64','unifiedcostandcausalfigures'],
 all_research_stages_resolved=True,sources=sources,old_manuscript_unchanged=True,
 formal_serving_campaigns=dict(N1=54,normal=105,process_fault_episodes=21),prepared_operator_cases=64,pilots_not_added_to_formal_denominators=True,
 candidate=dict(technical_pages=11,reference_only_pages=1,abstract_words=137,formal_refs=18,PDF_sha256=sha(W/'candidate_20261026/main.pdf')),
 decisions=dict(C1='GO_BOUNDED_STATE_WRITE_BOUNDARY_AND_OBSERVABLE_HARM_PROTECTION',C2='GO_PROTOCOL_COORDINATION_AND_COST_BOUNDARIES',
  C3='GO_RECORDED_RECOVERABLE_HISTORY_AND_INPUT_OBLIGATIONS',new_CDE_performance='NO_GO_INDEPENDENT_ADVANTAGE',
  V2_DAG_Elastic_CES_variants='PRIOR_NO_GOS_RETAINED_NOT_RESTARTED'),
 files=[dict(path=f,bytes=(W/f).stat().st_size,sha256=sha(W/f),delivery='LOCAL_OR_VERIFIED_PRIVATE_ONLY' if f.startswith('candidate_') or f=='review_snapshot_v1.zip' else 'BOUNDED_RESEARCH_EVIDENCE') for f in files],
 large_raw_on8TB=True,anonymous_host_updated=False,automatic_submission=False,
 final_author_actions=['claims and attribution signoff','COIs/ethics as applicable','review-host publishing/snapshot check','manual submission'],
 stopping_reason='All requested scientific gates resolved; fullsafecontrols and negatives retained; independentread-only audits and candidateQA pass. No validationretuning/newalgorithmnames or topic/acceptance guarantee.')
(W/'FINAL_DELIVERY_INDEX_v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(files=len(files),sources=sources,research_complete=True)))
