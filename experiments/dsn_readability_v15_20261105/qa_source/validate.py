"""Frozen-evidence readability QA, portable source build, and Fig. 1 reproduction."""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json,re,shutil,subprocess,sys,zipfile
import fitz
HERE=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def put(p,x):Path(p).write_bytes((json.dumps(x,indent=2)+'\n').encode())
a=argparse.ArgumentParser();a.add_argument('--config',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a=a.parse_args()
m=read(a.manifest);g=lambda *x:subprocess.check_output(['git','-C',str(HERE),*x],text=True).strip()
assert g('rev-parse','HEAD')==m['code_commit'] and not g('status','--porcelain','--untracked-files=all')
assert set(g('ls-files').splitlines())=={r['path'] for r in m['files']}
for row in m['files']:assert sha(HERE/row['path'])==row['sha256']
c=read(a.config);R=Path(c['root']);E=Path(c['study']);P=Path(c['paper']);O=Path(c['old_paper']);out=E/'paper_qa'/('FINAL_'+c['version']);out.mkdir(exist_ok=False)
assert sha(P/'main.pdf')==c['pdf_sha256'];base=read(E/'baseline/FROZEN.json')
for row in base['protected_v14']:assert sha(R/row['path'])==row['sha256'] and (R/row['path']).stat().st_size==row['bytes']
f=R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json';assert sha(f)==base['frozen_v11_manifest_sha256']
for row in read(f)['rows']:assert sha(R/row['path'])==row['sha256']
assert sha(R/'experiments/repository_identity_20261027/CURRENT.json')==base['CURRENT_sha256']
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==base['legacy_HEAD']
blocks=lambda root,k:[x for p in sorted(root.rglob('*.tex')) for x in re.findall(r'\\begin\{'+k+r'\}.*?\\end\{'+k+r'\}',p.read_text(encoding='utf-8'),re.S)]
for kind,n in [('proposition',3),('proof',3),('equation',5)]:assert blocks(P,kind)==blocks(O,kind) and len(blocks(P,kind))==n
for p in O.glob('*.bib'):assert sha(p)==sha(P/p.name)
for name in ['coordination_protocol','core_interaction','native_content']:
 for ext in ['pdf','svg']:assert sha(O/'figures'/(name+'.'+ext))==sha(P/'figures'/(name+'.'+ext))
assert sha(P/'figures/timely_full_interval_case.pdf')=='df335455f5b2ab93532354ae7400b60fae5dbfc06809666dbee8f4144b39cffb'
source=E/'figure_source';tracked=subprocess.check_output(['git','-C',str(source),'ls-files'],text=True).splitlines()
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='fd8fe368e7327d36221fd1860767ec60cfd0ceeb'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
for n in tracked:assert sha(source/n)==sha(P/'figures/figure1_source'/n)
companion=P/'RevTrace_DSN2027_anonymous_evidence_v13.zip';assert sha(companion)=='09e3ae7be37b56fdc8ce4993f0a13fd767a7d62ec3f8d4adbb66afad610f7d5f'
rounds=[('05_native_retention.tex','31.0','31.000'),('05_native_retention.tex','64.118875','64.119'),('05_native_retention.tex','66.33975','66.340'),('05_same_source_validation.tex','228.51025','228.510'),('05_same_source_validation.tex','208.1003125','208.100')]
for _,old,new in rounds:assert Decimal(old).quantize(Decimal('.001'))==Decimal(new)
numeric=[];tokens=lambda s:re.findall(r'(?<![\w.])\d+(?:\.\d+)?(?![\w.])',s)
for name in ['05_evaluation_core.tex','05_native_retention.tex','05_protocol_cost.tex','05_operating_boundaries.tex','05_same_source_validation.tex','05_execution_only.tex']:
 old=(O/'sections'/name).read_text(encoding='utf-8');new=(P/'sections'/name).read_text(encoding='utf-8')
 for fn,src,dst in rounds:
  if fn==name:old=re.sub(r'(?<![\d.])'+re.escape(src)+r'(?![\d.])',dst,old)
 assert tokens(old)==tokens(new.replace(' (2-s feedback)','')),name
 numeric.append(dict(section=name,numeric_tokens_preserved=True))
put(out/'NUMERIC_LEDGER.json',dict(experimental_numeric_tokens=numeric,roundings=[dict(section=f,original=o,display=n,precision_only=True) for f,o,n in rounds],original_frozen_precision_preserved=True))
main=(P/'main.tex').read_text(encoding='utf-8');oldmain=(O/'main.tex').read_text(encoding='utf-8');abs=lambda s:s.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0]
assert abs(main).replace('preselected setting','predeclared stratum')==abs(oldmain)
wc=len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",abs(main)));assert wc<=150
doc=fitz.open(P/'main.pdf');assert len(doc)==12 and doc[-1].get_text().lstrip().startswith('REFERENCES') and 'AI TOOL USAGE' in doc[-2].get_text()
log=(P/'main.log').read_text(errors='replace');assert not any(s in log for s in ['Overfull','undefined references','multiply defined','LaTeX Error'])
bib=(P/'main.bbl').read_text(encoding='utf-8');keys=re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',bib);assert len(keys)==len(set(keys))==31 and sha(P/'main.bbl')==sha(O/'main.bbl')
text='\n'.join(p.get_text() for p in doc)
for token in ['LENOVO','VLA_QWEN','zhouz4884','if and only if','No Withdrawal Without Refutation']:assert token.lower() not in text.lower()
assert '27.4' in text and '53.3' in text and '10/16' in text
fonts=subprocess.check_output([shutil.which('pdffonts'),str(P/'main.pdf')],text=True);assert all(l.split()[-5]=='yes' for l in fonts.splitlines()[2:] if l.strip());(out/'PDFFONTS.txt').write_bytes(fonts.encode())
(P/'README.md').write_bytes(b'# Anonymous DSN 2027 manuscript source, v15\n\nCompile main.tex with PDFLaTeX, BibTeX, then PDFLaTeX twice. All manuscript\nand vector inputs are included. The original v13 scientific evidence\ncompanion remains frozen and is supplied separately under its original name.\nThe v15 source archive additionally includes the standalone updated Fig. 1\nrenderer, configuration and exact original numeric input in\nfigures/figure1_source/. With Python, matplotlib and PyMuPDF installed:\n\n    python figures/figure1_source/render.py --out new_figure1_export\n\nThis reproduces the v15 action annotations without private Git metadata.\nIt does not rerun models, change events or align the two executions.\nThe frozen companion contains original source/configuration snapshots,\nsummaries and raw-log indices; full journals, recordings and weights are\nexternal resources. Other three main figure inputs remain unchanged.\n')
inputs=[]
for p in sorted(P.rglob('*')):
 rel=p.relative_to(P)
 if p.is_file() and (p.suffix in {'.tex','.bib','.sty','.cls'} or (rel.parts[0]=='figures' and (p.suffix in {'.pdf','.svg'} or 'figure1_source' in rel.parts)) or p.name=='README.md'):
  assert '.git' not in rel.parts and '__pycache__' not in rel.parts
  if p.suffix in {'.py','.json','.md'}:
   for t in ['LENOVO','VLA_QWEN','zhouz4884']:assert t not in p.read_text(encoding='utf-8'),str(rel)
  inputs.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
assert len(inputs)==37
put(P/'PACKAGING_PROVENANCE.json',dict(release='v15',technical_pages=11,reference_pages=1,cited_works=31,abstract_words=wc,pdf_sha256=sha(P/'main.pdf'),inputs=inputs,method_and_experiments_changed=False,only_main_figure_changed='Fig1 event-action annotations; actual data/axes preserved',frozen_companion_identity='v13',frozen_companion_sha256=sha(companion)))
archive=P/'RevTrace_DSN2027_anonymous_source_v15.zip';assert not archive.exists();names=[r['path'] for r in inputs]+['PACKAGING_PROVENANCE.json']
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n in sorted(names):z.write(P/n,n)
cold=out/'cold_source';cold.mkdir()
with zipfile.ZipFile(archive) as z:
 for n in z.namelist():
  p=(cold/n).resolve();assert p.is_relative_to(cold.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
for row in inputs:assert sha(cold/row['path'])==row['sha256']
r=subprocess.run([sys.executable,'-B',c['compile_helper'],str((cold/'main.tex').resolve()),'--recipe','pdflatex-bibtex'],capture_output=True);(out/'COLD_BUILD.txt').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-1500:]
d=fitz.open(cold/'main.pdf');assert len(d)==12;pixels=[]
for i,(x,y) in enumerate(zip(doc,d)):
 assert x.get_text()==y.get_text();xx=x.get_pixmap(alpha=False);yy=y.get_pixmap(alpha=False);assert xx.samples==yy.samples,i+1;pixels.append(hashlib.sha256(xx.samples).hexdigest())
r=subprocess.run([sys.executable,'-B',str(cold/'figures/figure1_source/render.py'),'--out',str((out/'figure1_reproduction').resolve())],cwd=cold,capture_output=True);(out/'FIGURE1_REPRODUCTION.txt').write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-1500:]
oldpix=fitz.open(P/'figures/timely_full_interval_case.pdf')[0].get_pixmap(alpha=False);newpix=fitz.open(out/'figure1_reproduction/timely_full_interval_case.pdf')[0].get_pixmap(alpha=False);assert oldpix.samples==newpix.samples
result=dict(status='PASS_V15_LANGUAGE_NUMERIC_BINDINGS_SOURCE_COLD_BUILD_AND_FIG1_REPRODUCTION',qa_code_commit=m['code_commit'],pdf_sha256=sha(P/'main.pdf'),cold_pdf_sha256=sha(cold/'main.pdf'),source_zip_sha256=sha(archive),source_zip_files=len(names),frozen_companion_sha256=sha(companion),v14_files_preserved=len(base['protected_v14']),v11_files_preserved=len(read(f)['rows']),all_three_propositions_proofs_and_five_equations_unchanged=True,experimental_numbers_preserved_except_declared_display_rounding=True,bibliography_bytes_unchanged=True,cited_works=31,abstract_words=wc,technical_pages=11,reference_pages=1,full_12_page_cold_build_pixel_identical=True,updated_fig1_reproduced_from_packaged_source_pixel_identical=True,other_three_figure_PDF_SVG_bytes_unchanged=True,new_model_calls=0,new_GPU_runs=0,original_source_pointer_unchanged=True,page_pixel_sha256=pixels,visual_review='PENDING_FINAL_INDEPENDENT_REVIEW')
put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=result['status'],new_model_calls=0,new_GPU_runs=0))
for row in m['files']:assert sha(HERE/row['path'])==row['sha256']
print(json.dumps({k:v for k,v in result.items() if k!='page_pixel_sha256'}))
