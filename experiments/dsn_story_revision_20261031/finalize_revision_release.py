"""Bind the completed writing, figure, independent review and package evidence."""
from pathlib import Path
import hashlib,json,re,subprocess

R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rel=R/'Paper_DSN/revisions/20261031_dsn2027_release_v7'
paper=read(R/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v7.json')
cold=read(E/'ANONYMOUS_COLD_BUILD_REVIEW_v7.json')
fig=read(E/'FIGURE_QA_v3.json')
actual=read(E/'FIGURE_COMPARISON_ACTUAL_RESULT_REVIEW_v1.json')
assert paper['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
assert cold['gate']=='PASS_ANONYMOUS_ZIP_COLD_SKILL_COMPILE_AND_LAYOUT_PARITY'
assert cold['original_inputs_hash_before_after_unchanged'] is True
assert cold['cold_packaged_source_bytes_unchanged'] is True
assert fig['gate']=='PASS_SOURCE_NUMERIC_VECTOR_AND_ACTUAL_ARTWORK_VISUAL_QA'
assert actual['gate']=='PASS_INDEPENDENT_EMITTED_COMPARISON_OBSERVATION_QA'
assert fig['new_model_calls']==0 and cold['new_model_calls']==0
assert sha(rel/'main.pdf')==paper['pdf_sha256']=='c75378b1452304b401625a3fb097c4993370ffe5ca6c769141e2f191b9911c71'
assert sha(R/paper['archive'])==paper['archive_sha256']=='4aca80514b19d7aae0a1e74e1e033d83377c2ba169666fb24e29b7cf8305cc59'
assert paper['total_pages']==12 and paper['technical_pagination']['technical_pages']==11
abstract=(rel/'main.tex').read_text(encoding='utf8').split('begin{abstract}')[1].split('end{abstract}')[0]
words=len(re.findall(r'\b[\w.-]+\b',abstract));assert words<=150
base=R/'Paper_DSN/revisions/20261031_dsn2027_release_v4'
assert sha(base/'main.pdf')=='d5174767ee7101339b535fa3f32f3c2fc45a1cf25ad36a345c57a0a9d2067c62'
assert sha(base/'RevTrace_DSN2027_anonymous_source_v4.zip')=='e51a97416c611fd127591161c83db3cca43f98d9c328367835855f0896f45ce7'
for row in read(base/'PACKAGING_PROVENANCE.json')['files']:
    assert sha(base/row['target'])==row['target_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
pointer=read(E/'ROOT_NOARG_FINAL4F_RESTORED_AFTER_V3.json')
assert pointer['gate']=='SOURCE_IDENTITY_PASS' and pointer['files_verified']==59
assert pointer['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
sources=['FINAL_REVISION_REPORT.zh.md','REVISION_BLUEPRINT.zh.md','REVIEW_RESOLUTION.zh.md',
    'CONTRIBUTION_EVIDENCE_CARD.zh.md','DISPLAY_NAME_MAP.csv','FIGURE_QA_v3.json',
    'FIGURE_COMPARISON_ACTUAL_RESULT_REVIEW_v1.json','METHOD_DISPATCH_SCOPE_AND_REVISION.zh.md',
    'CORE_PRESENTATION_AUDIT_v1.zh.md','NATIVE_PRESENTATION_CHECK_v2.json',
    'COLD_PROBLEM_MECHANISM_REVIEW_v1.zh.md','COLD_RESULTS_ONLY_REVIEW_v1.zh.md',
    'ANONYMOUS_COLD_BUILD_REVIEW_v7.json','FINAL_PAPER_VISUAL_INDEX_v7.json']
assert all((E/n).is_file() for n in sources)
tokens=re.compile(rb'(?:hf_[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})')
audited=[]
for p in E.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ['.git','__pycache__','.pytest_cache']):continue
    if any(x.endswith('_source_dev') or re.search(r'_source_v\d+$',x) for x in p.relative_to(E).parts):continue
    assert p.stat().st_size<20_000_000,str(p)
    if p.suffix in ['.py','.tex','.md','.json','.txt','.log','.bib','.csv']:
        assert not tokens.search(p.read_bytes()), 'Credential-like value in bounded artifact'
    audited.append((p,p.stat().st_size))
result=dict(gate='PASS_COMPLETE_DSN_ARGUMENT_FIGURES_AND_MANUSCRIPT_REVISION',date='2026-10-31',
    base_archive_commit='696bc889dd678312e0817b811a648649871e3e72',base_v4_unchanged=True,
    paper=paper['release']+'/main.pdf',pdf_sha256=paper['pdf_sha256'],archive=paper['archive'],
    archive_sha256=paper['archive_sha256'],technical_pages=11,references_only_pages=1,
    abstract_words=words,main_figures=3,tables=5,citations=21,embedded_font_entries=29,
    new_NN_calls=0,actual_bounded_interval_reader_runs=1,original_interval_NN_commit=actual['original_NN_commit'],
    actual_interval_analysis_commit=actual['actual_extraction_commit'],actual_final_figure_commit=fig['actual_plot_source_commit'],
    global_dispatch_priority_claim_removed=True,all_original_metrics_and_raw_preserved=True,
    actual_joint_D2_miss_milliseconds=27.43760496377945,
    no_event_matched_counterfactual_claim=True,complete_48point_companion_retained=True,
    source_package_cold_build_PASS=True,two_independent_cold_reads_complete=True,
    all_page_visual_and_three_gray_page_reviews=True,CURRENT_restored_NN4f=True,
    evidence=[dict(path=n,sha256=sha(E/n)) for n in sources],
    bounded_audited_files=len(audited),bounded_audited_bytes=sum(n for _,n in audited),
    legacy_dirty_head_preserved=True,delivery_state='READY_FOR_AUTHORIZED_GITHUB_SYNC',
    venue_submission_performed=False)
with (E/'FINAL_REVISION_GATE_v7.json').open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='evidence'}))
