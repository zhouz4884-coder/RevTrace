"""Close only proven scopes, retaining distinct NO-GO and original failed runs."""
import datetime,hashlib,json,pathlib,subprocess
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1];T=R/'experiments/dsn_manuscript_update_20261028'
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(path,value):pathlib.Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
r1=read(E/'FINAL_R1_EXECUTION_RECORD_20261031.json');probe=read(E/'INTERFERENCE_FINAL_EXECUTION_RECORD_v1.json');paper=read(T/'FINAL_RELEASE_RECORD_20261031_v2.json')
assert r1['actual_NN_trials']['total']==40 and r1['request_instances']['total']==54 and r1['original_selected_transitions']['total']==918
assert probe['status']=='NO_GO_FIXED_TWO_CLIENT_ADMISSION_OPPORTUNITY' and probe['actual_trials']==4 and probe['unrun_frozen_trials']==0
for label,record in (('R1',r1),('probe',probe)):
    for key,item in record['gates'].items():
        path=item.get('path',item.get('local'));assert path is not None
        assert sha(path)==item['sha256'],label+':'+key
        actual=read(path);assert actual.get('status',actual.get('gate'))==item['status'],label+':'+key
post=read(E/'FINAL_CPU_AND_POSTHOC_RESULTS/posthoc_v2/GATE.json')
assert post['status']=='PASS_COMPLETE_ZERO_NN_BUFFER4_POSTHOC_REAUDIT' and post['checked_cases']==post['passed_cases']==4
assert post['all_complete_raw_and_watchdog_bytes_unchanged'] and post['original_execution_gates_unchanged'] and post['new_neural_calls']==0
old=read(E/'BUFFER4_V1_RESULTS/GATE.json');assert old['status'].startswith('NO_GO')
diag=read(E/'DIAGNOSTIC_RESULTS_v2/GATE.json');assert diag['cases']==36 and diag['long_cases']==8 and diag['CPU_controls']['tests']==67
assert diag['eventual_conditional_actual_dispatches']==dict(N=1901,CONFIRMED=360,REFUTED=1541,UNRESOLVED=0,resolved_confirmation_rate=360/1901,all_dispatch_confirmation_lower=360/1901,all_dispatch_confirmation_upper=360/1901)
assert paper['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA' and paper['technical_pagination']['technical_pages']==11 and paper['total_pages']==12
P=R/paper['release'];assert sha(P/'main.pdf')==paper['pdf_sha256'] and sha(R/paper['archive'])==paper['archive_sha256']
qa=read(P/'QA_AUTOMATED_v1/QA.json');assert len(qa['checks']['source_snapshot']['cited_keys'])==21 and qa['checks']['fonts']['font_count']==23
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
pointer=read(R/'experiments/repository_identity_20261027/CURRENT.json');assert pointer['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
final=dict(status='COMPLETE_DECLARED_RESEARCH_RESULTS_AND_PAPER_V2_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_NN_trials=44,request_instances=70,original_program_transitions=1190,selected_transition_scope='Includes declared original buffer-only steps; not a decoder/CUDA/C_U-forward count.',actual_NN_sources=r1['sources'],probe_source=probe['sources'],decisions=dict(matched_normal='FinalFull6of8VsConservative0of8WithEOSBoundary',resident_requests='Full7of8VsConservative0of8FiniteClosedLoop',controlled_full_buffer='PosthocMechanism2MatchInstalls2MismatchRejects_OriginalCompoundFailuresPreserved',admission_opportunity='NO_GO_FIXED_TWO_CLIENT_ADMISSION_OPPORTUNITY'),gate_records=dict(R1=dict(path='FINAL_R1_EXECUTION_RECORD_20261031.json',sha256=sha(E/'FINAL_R1_EXECUTION_RECORD_20261031.json')),probe=dict(path='INTERFERENCE_FINAL_EXECUTION_RECORD_v1.json',sha256=sha(E/'INTERFERENCE_FINAL_EXECUTION_RECORD_v1.json')),diagnostic=dict(path='DIAGNOSTIC_RESULTS_v2/GATE.json',sha256=sha(E/'DIAGNOSTIC_RESULTS_v2/GATE.json')),paper=dict(path='../dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v2.json',sha256=sha(T/'FINAL_RELEASE_RECORD_20261031_v2.json'))),paper_release=paper['release'],pdf_sha256=paper['pdf_sha256'],archive_sha256=paper['archive_sha256'],actual_root_visual_pages=12,all_neural_windows_closed=True,remaining_declared_work=[],raw_disk_only=True,archive_commit_is_not_execution_source=True,publication_stage='dsn2027_strengthening_20261031_release_v2',conference_submission_performed=False)
target=E/'FINAL_ROUND_AND_PAPER_GATE_v2.json';assert not target.exists();write(target,final)
backup=E/'ACTIVE_STATE_PRE_FINAL_v2.json';assert not backup.exists();backup.write_bytes((E/'ACTIVE_STATE.json').read_bytes());write(E/'ACTIVE_STATE.json',dict(status=final['status'],final_gate=target.name,final_gate_sha256=sha(target),actual_NN_trials=44,request_instances=70,original_program_transitions=1190,decisions=final['decisions'],paper=paper['release']+'/main.pdf',paper_pdf_sha256=paper['pdf_sha256'],CURRENT_default_NN=pointer['source_commit'],remaining_declared_work=[],publication_stage=final['publication_stage'],scope='Completed scope contains positive service evidence, preserved audit failures and explicit NO-GO. Not44of44PASS.',conference_submission_performed=False))
write(R/'experiments/LATEST_RESEARCH.json',dict(date='2026-10-31',status=final['status'],state='dsn_strengthening_20261031/ACTIVE_STATE.json',report='dsn_strengthening_20261031/FINAL_RESEARCH_AND_PAPER_REPORT_20261031.zh.md',final_gate='dsn_strengthening_20261031/FINAL_ROUND_AND_PAPER_GATE_v2.json',paper=paper['release']+'/main.pdf',paper_QA_record='dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v2.json',new_actual_NN_trials=44,request_instances=70,original_program_transitions=1190,all_neural_windows_closed=True,previous_complete_paper='Paper_DSN/revisions/20261030_dsn2027_release_v1/main.pdf',conference_submission_performed=False))
print(json.dumps(dict(status=final['status'],actual_NN_trials=44,request_instances=70,original_program_transitions=1190,pdf_sha256=paper['pdf_sha256'],archive_sha256=paper['archive_sha256']),indent=2))
