"""Package only portable anonymous manuscript inputs; verify a clean cold build."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,zipfile
import fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13';Q=E/'paper_qa'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
qa=json.loads((Q/'FINAL_QA.json').read_bytes());assert qa['pdf_sha256']==sha(P/'main.pdf')
for name in ['timely_full_interval_case','coordination_protocol','core_interaction','native_content']:
 shutil.copyfile(E/'figures/EXPORT_v2'/(name+'.svg'),P/'figures'/(name+'.svg'))
(P/'README.md').write_text('''# Anonymous DSN 2027 manuscript source, v13

Compile main.tex using PDFLaTeX, BibTeX, then PDFLaTeX twice. The archive
contains all LaTeX/BibTeX inputs and four portable vector PDF/SVG figures.
The separate anonymous evidence ZIP supplies editable matplotlib programs,
frozen plotting inputs, exact source snapshots and bounded result records.
No external file path or model dependency is needed to compile the paper.
''',encoding='utf-8')
inputs=[]
for p in sorted(P.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(P)
 if p.suffix in {'.tex','.bib','.sty','.cls'} or (rel.parts[0]=='figures' and p.suffix in {'.pdf','.svg'}) or p.name=='README.md':
  inputs.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
assert len(inputs)==32
record=dict(release='v13',revision_type='editorial and vector figures; original method and independent confirmation frozen',venue='DSN 2027 Regular',anonymous=True,technical_pages=11,reference_pages=1,cited_references=31,abstract_word_count_whitespace=qa['abstract_words_whitespace'],abstract_word_count_alphanumeric=qa['abstract_words_alphanumeric'],manuscript_pdf_sha256=sha(P/'main.pdf'),inputs=inputs,companion_evidence_archive_sha256=sha(P/'RevTrace_DSN2027_anonymous_evidence_v13.zip'))
pp=P/'PACKAGING_PROVENANCE.json';assert not pp.exists();put(pp,record)
names=[r['path'] for r in inputs]+[pp.name];archive=P/'RevTrace_DSN2027_anonymous_source_v13.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for name in sorted(names):z.write(P/name,name)
cold=Q/'cold_manuscript';assert not cold.exists();cold.mkdir()
with zipfile.ZipFile(archive) as z:
 assert set(z.namelist())==set(names)
 for n in z.namelist():
  t=(cold/n).resolve();assert t.is_relative_to(cold.resolve());t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(z.read(n))
for r in inputs:assert sha(cold/r['path'])==r['sha256']
command=[sys.executable,'-B','C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py',str((cold/'main.tex').resolve()),'--recipe','pdflatex-bibtex']
r=subprocess.run(command,capture_output=True,cwd=cold);(Q/'COLD_MANUSCRIPT_BUILD.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-2000:]
x,y=fitz.open(P/'main.pdf'),fitz.open(cold/'main.pdf');assert len(x)==len(y)==12
pixels=[]
for i,(a,b) in enumerate(zip(x,y)):
 assert a.get_text()==b.get_text(),'Cold text/layout mismatch page '+str(i+1)
 ax=a.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);by=b.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
 assert ax.samples==by.samples,'Cold raster mismatch page '+str(i+1)
 pixels.append(hashlib.sha256(ax.samples).hexdigest())
assert not any(k in (cold/'main.log').read_text(errors='replace') for k in ['Overfull','undefined references','multiply defined','LaTeX Error'])
out=dict(status='PASS_ANONYMOUS_SOURCE_FRESH_COLD_BUILD_ALL_12_PAGES_PIXEL_IDENTICAL',pdf_sha256=sha(P/'main.pdf'),cold_pdf_sha256=sha(cold/'main.pdf'),source_zip_sha256=sha(archive),source_zip_bytes=archive.stat().st_size,source_zip_files=len(names),pages=12,technical_pages=11,reference_pages=1,cited_references=31,abstract_whitespace_words=qa['abstract_words_whitespace'],abstract_alphanumeric_words=qa['abstract_words_alphanumeric'],per_page_pixel_sha256=pixels,scope='Fresh ZIP extraction using same installed TeX toolchain, no stale auxiliaries or files outside archive')
put(Q/'COLD_BUILD_QA.json',out);print(json.dumps({k:v for k,v in out.items() if k!='per_page_pixel_sha256'}))
