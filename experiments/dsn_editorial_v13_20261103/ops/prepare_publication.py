"""Select bounded delivery files, never the legacy dirty tree or bulky extracts."""
from pathlib import Path
import difflib,hashlib,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13';OLD=R/'Paper_DSN/revisions/20261102_dsn2027_release_v12'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
patch=[]
for p in sorted(P.rglob('*')):
 if p.is_file() and p.suffix in {'.tex','.bib'}:
  q=OLD/p.relative_to(P)
  patch.extend(difflib.unified_diff(q.read_text(encoding='utf-8').splitlines(True),p.read_text(encoding='utf-8').splitlines(True),fromfile='v12/'+p.relative_to(P).as_posix(),tofile='v13/'+p.relative_to(P).as_posix()))
(E/'MANUSCRIPT_TEXT_DIFF.patch').write_text(''.join(patch),encoding='utf-8')
names=set()
def add(p):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<20_000_000
 rel=p.relative_to(R).as_posix();assert '.git' not in p.relative_to(R).parts;names.add(rel)
for p in P.rglob('*'):
 if p.is_file() and (p.suffix in {'.tex','.bib','.pdf','.svg','.zip'} or p.name in {'.gitattributes','README.md','PACKAGING_PROVENANCE.json'}):add(p)
for p in E.iterdir():
 if p.is_file() and p.name not in {'PUBLICATION_MANIFEST.json','PUBLICATION_PATHS.json','DELIVERY_RECEIPT.json','TASK_COMPLETION_AUDIT.json'}:add(p)
for folder in ['ops','packages','baseline','figure_source','package_qa_source']:
 for p in (E/folder).rglob('*'):
  if p.is_file() and '.git' not in p.relative_to(E/folder).parts and '__pycache__' not in p.parts:add(p)
for p in (E/'review').iterdir():
 if p.is_file():add(p)
for p in (E/'figures').iterdir():
 if p.is_file():add(p)
for p in (E/'figures/EXPORT_v2').iterdir():
 if p.is_file():add(p)
for name in ['SUMMARY.json','GATE.json']:
 add(E/'figures/EXPORT_v1'/name)
for p in (E/'paper_qa').iterdir():
 if p.is_file() and (p.suffix=='.json' or p.name in {'PDFFONTS.txt','COLD_MANUSCRIPT_BUILD.txt','ANONYMOUS_EVIDENCE_QA_OUTPUT.txt'}):add(p)
qa=json.loads((E/'paper_qa/FINAL_QA.json').read_bytes());render=Path(qa['render_directory'])
for p in render.iterdir():
 if p.is_file() and (not p.name.endswith('_gray.png') or p.name in {'page_02_gray.png','page_03_gray.png','page_08_gray.png'}):add(p)
for name in ['SUMMARY.json','GATE.json','verify_reported_statistics.py.txt','reproduce_figures.py.txt']:add(E/'paper_qa/anonymous_evidence_check'/name)
for p in [R/'Paper_DSN/CURRENT.md',R/'experiments/LATEST_RESEARCH.json']:add(p)
rows=[dict(path=n,bytes=(R/n).stat().st_size,sha256=sha(R/n)) for n in sorted(names)]
record=dict(status='FROZEN_BOUNDED_PUBLICATION_INPUTS_BEFORE_GITHUB_WRITE',base_delivery_commit='1268e587b1ff71ab539fc6a353137c355885a859',files=len(rows),bytes=sum(r['bytes'] for r in rows),rows=rows,scope='No legacy dirty files, model weights, data, raw journals, .git directories, cold extracts, or private external comments included. Complete editable figure and QA source identities retained.')
(E/'PUBLICATION_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
names.add((E/'PUBLICATION_MANIFEST.json').relative_to(R).as_posix())
(E/'PUBLICATION_PATHS.json').write_text(json.dumps(sorted(names),indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='rows'}))
