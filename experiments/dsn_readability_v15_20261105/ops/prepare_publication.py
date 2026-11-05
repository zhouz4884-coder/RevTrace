from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261105_dsn2027_release_v15';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();names=set()
def add(p):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<20_000_000;names.add(p.relative_to(R).as_posix())
for p in P.rglob('*'):
 rel=p.relative_to(P)
 if p.is_file() and (p.suffix in {'.tex','.bib','.pdf','.svg','.zip'} or 'figure1_source' in rel.parts or p.name in {'README.md','PACKAGING_PROVENANCE.json','.gitattributes'}):add(p)
for p in E.iterdir():
 if p.is_file() and p.name not in {'PUBLICATION_MANIFEST.json','PUBLICATION_PATHS.json','DELIVERY_RECEIPT.json','TASK_COMPLETION_AUDIT.json'}:add(p)
for folder in ['ops','qa_source','figure_source','packages','baseline','review']:
 for p in (E/folder).rglob('*'):
  if p.is_file() and '.git' not in p.relative_to(E/folder).parts and '__pycache__' not in p.parts:add(p)
for p in (E/'figures/EXPORT_v1').iterdir():
 if p.is_file():add(p)
for p in (E/'paper_qa').glob('*.json'):add(p)
for name in ['SUMMARY.json','GATE.json','NUMERIC_LEDGER.json','PDFFONTS.txt','COLD_BUILD.txt','FIGURE1_REPRODUCTION.txt']:add(E/'paper_qa/FINAL_v1'/name)
for p in (E/'paper_qa/render_b5c410b6c6fd').glob('*.png'):
 if not p.name.endswith('_gray.png') or p.name in ['page_02_gray.png','page_03_gray.png','page_08_gray.png','page_11_gray.png']:add(p)
for p in [R/'Paper_DSN/CURRENT.md',R/'experiments/LATEST_RESEARCH.json']:add(p)
rows=[dict(path=n,bytes=(R/n).stat().st_size,sha256=sha(R/n)) for n in sorted(names)];(E/'PUBLICATION_MANIFEST.json').write_bytes((json.dumps(dict(base_commit='3bcbb7638e6d9106965e4274a6c388a0186ab7ee',files=len(rows),bytes=sum(r['bytes'] for r in rows),rows=rows,scope='Bounded readability/figure evidence only; no raw data, models, private comments, bulky extracts or legacy dirty files'),indent=2)+'\n').encode());names.add((E/'PUBLICATION_MANIFEST.json').relative_to(R).as_posix());(E/'PUBLICATION_PATHS.json').write_bytes((json.dumps(sorted(names),indent=2)+'\n').encode());print(json.dumps(dict(files=len(names),bytes=sum(r['bytes'] for r in rows))))
