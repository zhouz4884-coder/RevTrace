"""Bind final editorial evidence without executing any serving experiment."""
from pathlib import Path
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rel=R/'Paper_DSN/revisions/20261101_dsn2027_release_v9'
p=read(R/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261101_v9.json')
q=read(rel/'QA_AUTOMATED/QA.json');c=read(E/'COLD_BUILD_QA.json');f=read(E/'FIGURE_QA_FINAL.json')
assert p['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
assert c['gate']=='PASS_ZIP_ONLY_COLD_SKILL_BUILD_LAYOUT_AND_SOURCE_PARITY'
assert f['gate']=='PASS_APPROVED_FOUR_FIGURE_SOURCE_NUMERIC_VECTOR_AND_ACTUAL_VISUAL_QA'
assert c['new_model_calls']==f['new_model_calls']==f['actual_reader_calls']==0
assert sha(rel/'main.pdf')==p['pdf_sha256'] and sha(R/p['archive'])==p['archive_sha256']
assert p['technical_pagination']['technical_pages']==11 and p['total_pages']==12
assert p['technical_pagination']['reference_numbers_seen']==list(range(1,32))
assert q['checks']['fonts']['font_count']==30
base=R/'Paper_DSN/revisions/20261031_dsn2027_release_v7'
assert sha(base/'main.pdf')=='c75378b1452304b401625a3fb097c4993370ffe5ca6c769141e2f191b9911c71'
assert sha(base/'RevTrace_DSN2027_anonymous_source_v7.zip')=='4aca80514b19d7aae0a1e74e1e033d83377c2ba169666fb24e29b7cf8305cc59'
for row in read(base/'PACKAGING_PROVENANCE.json')['files']:assert sha(base/row['target'])==row['target_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
assert read(E/'ROOT_NOARG_RESTORED_FINAL.json')['files_verified']==59
abstract=(rel/'main.tex').read_text(encoding='utf8').split('begin{abstract}')[1].split('end{abstract}')[0]
words=len(re.findall(r'\b[\w.-]+\b',abstract));assert words<=150
evidence=['EDITORIAL_DIFF.md','CLAIM_REVIEW.md','READER_CHECK.md','LITERATURE_DELTA.md',
 'ADDITIONAL_REFS.bib','CANDIDATE_COORDINATION_REFS.bib','FIGURE_QA_FINAL.json','COLD_BUILD_QA.json']
assert all((E/n).is_file() for n in evidence)
pattern=re.compile(rb'(?:hf_[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,})')
sizes=[]
for x in E.rglob('*'):
 if not x.is_file() or any(t in x.parts for t in ['.git','__pycache__','.pytest_cache']):continue
 if any(t.endswith('_source_dev') or re.search(r'_source_v\d+$',t) for t in x.relative_to(E).parts):continue
 assert x.stat().st_size<20_000_000
 if x.suffix in ['.py','.md','.json','.tex','.bib','.txt','.log']:assert not pattern.search(x.read_bytes())
 sizes.append(x.stat().st_size)
d=dict(gate='PASS_COMPLETE_EDITORIAL_GRAPHICS_31_REFERENCES_AND_PACKAGE_QA',date='2026-11-01',
 base_archive_commit='6240efceb007b9423b90871128f0cef1af79b3c2',base_v7_unchanged=True,
 paper=p['release']+'/main.pdf',pdf_sha256=p['pdf_sha256'],archive=p['archive'],archive_sha256=p['archive_sha256'],
 technical_pages=11,references_only_pages=1,cited_references=31,main_figures=4,tables=5,
 abstract_words=words,font_entries_embedded=30,source_package_files=len(p['source_package_files']),
 plot_source_commit=f['source_commit'],new_neural_calls=0,new_actual_interval_reader_calls=0,
 all_original_numeric_objects_unchanged=True,actual_color_pages_reviewed=12,gray_pages_reviewed=[2,3,8],
 scope_fixed_interval_vs_run=True,posthoc_text_agreement_not_SUP=True,
 no_causal_27ms_tradeoff_claim=True,distinct_parent_and_child_SUP_events=True,
 source_archive_cold_build=True,CURRENT_restored_NN4f=True,legacy_dirty_head_preserved=True,
 evidence=[dict(path=n,sha256=sha(E/n)) for n in evidence],
 bounded_audited_files=len(sizes),bounded_audited_bytes=sum(sizes),
 delivery_state='READY_FOR_AUTHORIZED_GITHUB_SYNC',venue_submission_performed=False)
with (E/'FINAL_QA.json').open('x',encoding='utf8',newline='\n') as out:json.dump(d,out,indent=2);out.write('\n')
print(json.dumps({k:v for k,v in d.items() if k!='evidence'}))
