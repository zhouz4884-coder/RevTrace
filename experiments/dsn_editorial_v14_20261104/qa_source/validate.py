"""Frozen-editorial verification and portable-source cold build; no model imports."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
import fitz
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def put(p,x):Path(p).write_bytes((json.dumps(x,indent=2)+'\n').encode())
a=argparse.ArgumentParser();a.add_argument('--config',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a=a.parse_args()
g=lambda *x:subprocess.check_output(['git','-C',str(HERE),*x],text=True).strip()
m=read(a.manifest);assert g('rev-parse','HEAD')==m['code_commit'] and not g('status','--porcelain','--untracked-files=all')
assert set(g('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert sha(HERE/r['path'])==r['sha256']
c=read(a.config);R=Path(c['root']);E=Path(c['study']);P=Path(c['paper']);O=Path(c['old_paper']);Q=E/'paper_qa';out=Q/('FINAL_'+c['version']);out.mkdir(exist_ok=False)
assert sha(P/'main.pdf')==c['pdf_sha256'];baseline=read(E/'baseline/FROZEN.json')
for row in baseline['protected_v13']:assert sha(R/row['path'])==row['sha256'] and (R/row['path']).stat().st_size==row['bytes']
oldfreeze=R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json';assert sha(oldfreeze)==baseline['frozen_v11_manifest_sha256']
for row in read(oldfreeze)['rows']:assert sha(R/row['path'])==row['sha256']
assert sha(R/'experiments/repository_identity_20261027/CURRENT.json')==baseline['CURRENT_sha256']
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==baseline['legacy_HEAD']
blocks=lambda root,kind:[re.sub(r'\s+',' ',x) for p in sorted(root.rglob('*.tex')) for x in re.findall(r'\\begin\{'+kind+r'\}.*?\\end\{'+kind+r'\}',p.read_text(encoding='utf-8'),re.S)]
for kind,n in [('proposition',3),('equation',5)]:assert blocks(P,kind)==blocks(O,kind) and len(blocks(P,kind))==n
oldp,newp=blocks(O,'proof'),blocks(P,'proof');assert oldp[:2]==newp[:2] and len(oldp)==len(newp)==3
added='An early completion remains buffered while its parent input is unknown. Exclusive serial selection revalidates its actual parent and complete frozen input before append, so completion order adds no parentless edge. '
assert newp[2].replace(added,'')==oldp[2]
for p in (O/'figures').iterdir():assert sha(p)==sha(P/'figures'/p.name)
for p in O.glob('*.bib'):assert sha(p)==sha(P/p.name)
assert (P/'tables/native_reliability.tex').read_text().replace('Fault-to-new-fact (s)','New result (s)')==(O/'tables/native_reliability.tex').read_text()
assert sha(P/'sections/05_native_retention.tex')==sha(O/'sections/05_native_retention.tex')
companion=P/'RevTrace_DSN2027_anonymous_evidence_v13.zip';assert sha(companion)=='09e3ae7be37b56fdc8ce4993f0a13fd767a7d62ec3f8d4adbb66afad610f7d5f'
main=(P/'main.tex').read_text(encoding='utf-8');oldmain=(O/'main.tex').read_text(encoding='utf-8');getabs=lambda t:t.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0]
assert getabs(main)==getabs(oldmain);wc=len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",getabs(main)));assert wc<=150
doc=fitz.open(P/'main.pdf');assert len(doc)==12 and doc[-1].get_text().lstrip().startswith('REFERENCES') and 'AI TOOL USAGE' in doc[-2].get_text()
alltext='\n'.join(p.get_text() for p in doc);alltex='\n'.join(p.read_text(encoding='utf-8') for p in P.rglob('*.tex'))
for token in ['zhouz4884','LENOVO','VLA_QWEN','if and only if','No Withdrawal Without Refutation']:assert token.lower() not in (alltext+alltex).lower()
for token in ['Overfull','undefined references','multiply defined','LaTeX Error']:assert token not in (P/'main.log').read_text(errors='replace')
keys=re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',(P/'main.bbl').read_text(encoding='utf-8'));assert len(keys)==len(set(keys))==31
fonts=subprocess.check_output([shutil.which('pdffonts'),str(P/'main.pdf')],text=True);assert all(l.split()[-5]=='yes' for l in fonts.splitlines()[2:] if l.strip());(out/'PDFFONTS.txt').write_bytes(fonts.encode())
(P/'README.md').write_bytes(b'# Anonymous DSN 2027 manuscript source, v14\n\nCompile main.tex with PDFLaTeX, BibTeX, then PDFLaTeX twice.\nAll LaTeX/BibTeX and vector figure inputs are included.\nThe unchanged RevTrace_DSN2027_anonymous_evidence_v13.zip is the frozen\ncompanion for source snapshots, configurations, summaries and figure programs.\nIts v13 identity is retained; v14 adds no model or serving experiment.\nFull journals, weights and recordings are indexed, not included in the companion.\n')
inputs=[]
for p in sorted(P.rglob('*')):
 rel=p.relative_to(P)
 if p.is_file() and (p.suffix in {'.tex','.bib','.sty','.cls'} or (rel.parts[0]=='figures' and p.suffix in {'.pdf','.svg'}) or p.name=='README.md'):
  inputs.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
assert len(inputs)==32
provenance=dict(release='v14',technical_pages=11,reference_pages=1,cited_references=31,abstract_word_count=wc,manuscript_pdf_sha256=sha(P/'main.pdf'),method_changed=False,figures_changed=False,proof_change='Prop3 explanation of early unknown-parent completion only; theorem assumptions and conclusion unchanged',frozen_companion_identity='v13',frozen_companion_sha256=sha(companion),inputs=inputs)
put(P/'PACKAGING_PROVENANCE.json',provenance);names=[r['path'] for r in inputs]+['PACKAGING_PROVENANCE.json'];archive=P/'RevTrace_DSN2027_anonymous_source_v14.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n in sorted(names):z.write(P/n,n)
cold=out/'cold_source';cold.mkdir()
with zipfile.ZipFile(archive) as z:
 for n in z.namelist():
  p=(cold/n).resolve();assert p.is_relative_to(cold.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
for row in inputs:assert sha(cold/row['path'])==row['sha256']
assert sha(c['compile_helper'])==c['compile_helper_sha256']
r=subprocess.run([sys.executable,'-B',c['compile_helper'],str((cold/'main.tex').resolve()),'--recipe','pdflatex-bibtex'],capture_output=True)
(out/'COLD_BUILD.txt').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-1800:]
coldpdf=fitz.open(cold/'main.pdf');assert len(coldpdf)==12
pixels=[]
for i,(x,y) in enumerate(zip(doc,coldpdf)):
 assert x.get_text()==y.get_text()
 xx=x.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);yy=y.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);assert xx.samples==yy.samples,i+1;pixels.append(hashlib.sha256(xx.samples).hexdigest())
result=dict(status='PASS_V14_FROZEN_EVIDENCE_FORMAT_AND_FRESH_SOURCE_COLD_BUILD',qa_code_commit=m['code_commit'],pdf_sha256=sha(P/'main.pdf'),cold_pdf_sha256=sha(cold/'main.pdf'),source_zip_sha256=sha(archive),source_zip_files=33,frozen_companion_sha256=sha(companion),v13_files_unchanged=len(baseline['protected_v13']),v11_evidence_files_unchanged=len(read(oldfreeze)['rows']),original_NN_source_unchanged=True,source_pointer_unchanged=True,abstract_unchanged=True,abstract_word_count=wc,propositions_unchanged=3,equations_unchanged=5,unchanged_proofs=2,proof3_only_declared_explanation_added=True,four_figure_PDF_and_SVG_bytes_unchanged=True,bibliography_bytes_unchanged=True,cited_works=31,technical_pages=11,reference_pages=1,all_fonts_embedded=True,full_12_page_cold_build_pixel_identical=True,page_pixel_sha256=pixels,new_model_calls=0,new_GPU_runs=0,visual_review='PENDING_ACTUAL_REVIEW',scope='Editorial source packaging and checks only; not a new scientific or service experiment')
put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=result['status'],new_model_calls=0,new_GPU_runs=0))
for row in m['files']:assert sha(HERE/row['path'])==row['sha256']
print(json.dumps({k:v for k,v in result.items() if k!='page_pixel_sha256'}))
