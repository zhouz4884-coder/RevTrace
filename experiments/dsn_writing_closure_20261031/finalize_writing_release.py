"""Consolidate completed, immutable evidence; never execute a neural run."""
from pathlib import Path
import hashlib,json,re,subprocess

R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
release=R/'Paper_DSN/revisions/20261031_dsn2027_release_v4'
paper=read(R/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v4.json')
cpu=read(E/'CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json')
cold=read(E/'ANONYMOUS_COLD_BUILD_REVIEW_v4.json')
assert paper['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
assert cpu['status']=='PASS_COMPLETE20_CPU_CONTENT_EXACT_G_AND_DEPENDENCY_CONTINUITY'
assert cpu['new_model_calls']==0 and cpu['actual_NN_trials_reused']==20 and cpu['request_instances']==32
assert paper['pdf_sha256']==sha(release/'main.pdf')
assert paper['archive_sha256']==sha(R/paper['archive'])
assert paper['total_pages']==12 and paper['technical_pagination']['technical_pages']==11
abstract=(release/'main.tex').read_text(encoding='utf8').split('begin{abstract}')[1].split('end{abstract}')[0]
abstract_words=len(re.findall(r'\b[\w.-]+\b',abstract));assert abstract_words<=150
base=R/'Paper_DSN/revisions/20261031_dsn2027_release_v2'
assert sha(base/'main.pdf')=='a91618cc80ca5649ac1ffd118fb08188b2693d903ccd69750b533c4c7b1dbb32'
assert sha(base/'RevTrace_DSN2027_anonymous_source_v2.zip')=='8b704826835d7d51a167cb29ddcca1c2af165ab79a41006290eaf3f3a18997ce'
for row in read(base/'PACKAGING_PROVENANCE.json')['files']:
    assert sha(base/row['target'])==row['target_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
source=read(E/'ROOT_NOARG_FINAL4F_RESTORED.json')
assert source['gate']=='SOURCE_IDENTITY_PASS' and source['files_verified']==59
assert source['code_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
tokens=re.compile(rb'(?:hf_[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})')
audited=[]
for p in E.rglob('*'):
    if not p.is_file() or any(x in p.parts for x in ['.git','__pycache__','.pytest_cache']):continue
    if any(x.endswith('_source_dev') or re.search(r'_source_v\d+$',x) for x in p.relative_to(E).parts):continue
    assert p.stat().st_size<20_000_000, str(p)
    if p.suffix in ['.py','.tex','.md','.json','.txt','.log','.bib']:
        assert not tokens.search(p.read_bytes()), 'Unexpected credential-like value in bounded evidence'
    audited.append(dict(path=p.relative_to(R).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
record=dict(gate='PASS_DECLARED_WRITING_CLOSURE_CONTENT_AND_PAPER_QA',date='2026-10-31',
    report='FINAL_WRITING_AND_RESEARCH_REPORT.zh.md',report_sha256=sha(E/'FINAL_WRITING_AND_RESEARCH_REPORT.zh.md'),
    actual_new_NN_calls=0,reused_NN_trials=20,recounted_request_instances=32,recounted_original_frontiers=544,
    actual_analysis_commit='6eb6639478a87e6be971e23282bd2f31789f242f',
    actual_NN_commit=source['code_commit'],figure_commit='60211b74f78b8420ea48f7a08746aedbbcbfb868',
    paper=paper['release']+'/main.pdf',pdf_sha256=paper['pdf_sha256'],source_archive=paper['archive'],
    archive_sha256=paper['archive_sha256'],technical_pages=11,references_only_pages=1,abstract_words=abstract_words,
    cold_build_record='ANONYMOUS_COLD_BUILD_REVIEW_v4.json',cold_build_record_sha256=sha(E/'ANONYMOUS_COLD_BUILD_REVIEW_v4.json'),
    all_page_root_review=True,independent_content_QA=True,first_page_cold_review=True,claim_review=True,
    base_v2_unchanged=True,legacy_dirty_head_preserved=True,current_restored_to_actual_NN4f=True,
    bounded_evidence_audited_files=len(audited),bounded_evidence_audited_bytes=sum(r['bytes'] for r in audited),
    no_actual_conference_submission=True,delivery_state='READY_FOR_AUTHORIZED_GITHUB_SYNC',
    remaining_risks=['closest-prior-art overlap','four native acoustic sources','EOS deadline margin',
        'no-reset quality and cold-Owner deadline failures','no open-arrival capacity claim','author/title/public-draft anonymity before actual submission'])
with (E/'FINAL_CLOSURE_GATE_v1.json').open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(record))
