from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
names=set()
def add(p):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<20_000_000;names.add(p.relative_to(R).as_posix())
for p in P.rglob('*'):
 if p.is_file() and (p.suffix in {'.tex','.bib','.pdf','.svg','.zip'} or p.name in {'README.md','PACKAGING_PROVENANCE.json','.gitattributes'}):add(p)
for p in E.iterdir():
 if p.is_file() and p.name not in {'PUBLICATION_MANIFEST.json','PUBLICATION_PATHS.json','DELIVERY_RECEIPT.json','TASK_COMPLETION_AUDIT.json'}:add(p)
for folder in ['ops','qa_source','packages','baseline','review']:
 for p in (E/folder).rglob('*'):
  if p.is_file() and '.git' not in p.relative_to(E/folder).parts and '__pycache__' not in p.parts:add(p)
for p in (E/'paper_qa').glob('*.json'):add(p)
for v in ['v1','v2']:
 for name in ['SUMMARY.json','GATE.json','PDFFONTS.txt','COLD_BUILD.txt']:add(E/'paper_qa'/('FINAL_'+v)/name)
for p in (E/'paper_qa/render_5462d73d98a7').glob('*.png'):
 if not p.name.endswith('_gray.png') or p.name in ['page_02_gray.png','page_03_gray.png','page_08_gray.png','page_11_gray.png']:add(p)
for p in [R/'Paper_DSN/CURRENT.md',R/'experiments/LATEST_RESEARCH.json']:add(p)
rows=[dict(path=n,bytes=(R/n).stat().st_size,sha256=sha(R/n)) for n in sorted(names)]
(E/'PUBLICATION_MANIFEST.json').write_bytes((json.dumps(dict(base_commit='1f841da127d7bba5cead8b129da25da56a50b0eb',files=len(rows),bytes=sum(x['bytes'] for x in rows),rows=rows,scope='Audited bounded editorial outputs only; no private feedback text, bulky extracts, raw journals, models, .git directories or legacy dirty files'),indent=2)+'\n').encode())
names.add((E/'PUBLICATION_MANIFEST.json').relative_to(R).as_posix());(E/'PUBLICATION_PATHS.json').write_bytes((json.dumps(sorted(names),indent=2)+'\n').encode());print(json.dumps(dict(files=len(names),bytes=sum(x['bytes'] for x in rows))))
