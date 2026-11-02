"""Package sanitized source inputs, then compile an isolated fresh extraction."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,zipfile
import fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1]
paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v12';qa=E/'paper_qa'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads((qa/'FINAL_QA.json').read_bytes())['pdf_sha256']==sha(paper/'main.pdf')
readme=paper/'README.md'
readme.write_bytes(b'# Anonymous DSN 2027 source\n\nCompile main.tex with pdflatex, bibtex main, then pdflatex twice.\nThe package contains the complete manuscript and vector figure inputs.\n')
inputs=[]
for p in sorted(paper.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(paper)
    if p.suffix.lower() in {'.tex','.bib','.sty','.cls'} or (rel.parts[0]=='figures' and p.suffix.lower() in {'.pdf','.png','.svg','.eps'}) or p.name=='README.md':
        inputs.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
assert len(inputs)==28
main=(paper/'main.tex').read_text(encoding='utf-8')
abstract=main.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0]
words=re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",abstract);assert len(words)<=150
provenance=dict(release='v12',venue='DSN 2027 Regular',anonymous=True,technical_pages=11,reference_pages=1,
                cited_references=31,abstract_word_count=len(words),manuscript_pdf_sha256=sha(paper/'main.pdf'),
                inputs=inputs,scope='Complete anonymous LaTeX/vector source package; research execution records are archived separately.')
pp=paper/'PACKAGING_PROVENANCE.json';assert not pp.exists();pp.write_bytes((json.dumps(provenance,indent=2)+'\n').encode())
names=[r['path'] for r in inputs]+[pp.name]
archive=paper/'RevTrace_DSN2027_anonymous_source_v12.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in sorted(names):z.write(paper/name,name)
cold=qa/'cold_build_v12';assert not cold.exists();cold.mkdir()
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist())==set(names)
    for name in z.namelist():
        target=(cold/name).resolve();assert target.is_relative_to(cold.resolve())
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
for row in inputs:assert (cold/row['path']).stat().st_size==row['bytes'] and sha(cold/row['path'])==row['sha256']
command=[__import__('sys').executable,'-B',r'C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py',str((cold/'main.tex').resolve()),'--recipe','pdflatex-bibtex']
r=subprocess.run(command,capture_output=True)
(qa/'cold_build_full.txt').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-2000:]

a,b=fitz.open(paper/'main.pdf'),fitz.open(cold/'main.pdf')
assert len(a)==len(b)==12
pixel=[]
for i,(x,y) in enumerate(zip(a,b)):
    assert x.get_text()==y.get_text(),'cold-build content/layout differs at page '+str(i+1)
    px=x.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);py=y.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
    assert px.samples==py.samples,'cold-build raster differs at page '+str(i+1)
    pixel.append(hashlib.sha256(px.samples).hexdigest())
record=dict(gate='PASS_ANONYMOUS_SOURCE_COLD_BUILD_ALL_12_PAGES_PIXEL_IDENTICAL',
    pdf_sha256=sha(paper/'main.pdf'),cold_pdf_sha256=sha(cold/'main.pdf'),source_zip_sha256=sha(archive),
    source_zip_bytes=archive.stat().st_size,source_zip_files=len(names),abstract_words=len(words),
    pages=12,technical_pages=11,reference_pages=1,citations=31,per_page_pixel_sha256=pixel,
    environment_scope='Fresh source extraction, same installed TeX toolchain; no stale auxiliary files or external source references.')
(qa/'COLD_BUILD_QA.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in record.items() if k!='per_page_pixel_sha256'}))
