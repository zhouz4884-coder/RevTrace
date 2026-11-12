"""Bound v18 source/PDF bytes, verify v17 preservation, copy local delivery."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,zipfile
import fitz
E=Path(__file__).resolve().parents[1];ROOT=E.parents[1]
V=Path(json.loads((E/'WORKING_STATE.json').read_bytes())['writing_root'])
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=ROOT
base=json.loads((E/'PROTECTED_V15_V17.json').read_bytes())
for row in base['files']:
 p=old/row['path'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],row['path']
source=json.loads((V/'qa/source_check.json').read_bytes());text=(V/'qa/flattened_source.tex').read_text(encoding='utf8')
doc=fitz.open(V/'main.pdf');refpages=[i for i,p in enumerate(doc)if p.get_text().startswith('REFERENCES')]
assert len(doc)==12 and refpages==[11]
assert not doc.metadata.get('author')
assert all(abs(p.rect.width-612)<.01 and abs(p.rect.height-792)<.01 for p in doc)
log=(V/'main.log').read_text(errors='replace');assert not re.search(r'Overfull|undefined references|undefined citations',log,re.I)
fonts=subprocess.check_output(['pdffonts',str(V/'main.pdf')],text=True);assert 'Type 3'not in fonts
for line in fonts.splitlines()[2:]:
 if line.strip():
  m=re.search(r'\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$',line);assert m and m.group(1)=='yes',line
figs=source['figures'];assert len(figs)==4
baseline={row['path']:row['sha256']for row in json.loads((E/'BASE_V18_MANIFEST.json').read_bytes())['files']}
for row in figs:assert row['sha256']==baseline[row['path']],'figure data changed'
members=set(source['reachable_sources'])|set(source['bibliographies'])|{'README.md','CHANGES.md','figures/render_v16.py','figures/figure_data_v16.json','qa/check_source.py','qa/verify_source.py','qa/source_check.json','qa/bibliography_check.json'}
members.update(row['path']for row in figs)
for p in (V/'figures/figure1_source').rglob('*'):
 if p.is_file()and'__pycache__'not in p.parts and p.suffix in {'.py','.json','.csv','.md'}:members.add(p.relative_to(V).as_posix())
for n in members:
 p=V/n
 if p.suffix in {'.tex','.bib','.py','.json','.md','.csv'}:
  t=p.read_text(encoding='utf8').lower()
  assert not any(w in t for w in ['zhouz4884','lenovo','vla_qwen','github.com/zhou','d:/','c:/users']),n
rows=[dict(path=n,bytes=(V/n).stat().st_size,sha256=sha(V/n))for n in sorted(members)]
(V/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(version='v18',files=rows),indent=2)+'\n',encoding='utf8')
zpath=V/'RevTrace_DSN2027_source_v18.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED)as z:
 for n in sorted(members|{'SOURCE_MANIFEST.json'}):z.write(V/n,n)
with zipfile.ZipFile(zpath)as z:
 assert z.testzip()is None
 for row in rows:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
check=dict(status='PASS_AMENDED_V18_AND_PRESERVED_V15_V17',version='v18',pdf_sha256=sha(V/'main.pdf'),pdf_bytes=(V/'main.pdf').stat().st_size,pages=len(doc),technical_pages=11,references_pages=1,abstract_whitespace_words=source['abstract_whitespace_words'],abstract_token_words=source['abstract_token_words'],cited_references=source['cited_keys'],all_fonts_embedded=True,type3_fonts=False,overfull_boxes=0,missing_cites=source['missing_cites'],missing_refs=source['missing_refs'],source_zip_members=len(members)+1,source_zip_sha256=sha(zpath),all_four_figures_byte_unchanged=True,figure2_page=next(i+1 for i,p in enumerate(doc)if'Fig. 2.'in p.get_text()),protected_v15_v17_all_recorded_files_unchanged=True,v17_pdf_sha256=next(row['sha256']for row in base['files']if row['path']=='Paper_DSN/revisions/20261111_dsn2027_release_v17/main.pdf'),AI_tool_usage_disclosed=bool(re.search(r'AI\s+TOOL\s+USAGE',doc[-2].get_text(),re.I)),new_GPU_experiments=0,new_scientific_experiments=0,visual_QA='Twelve-page amended layout inspected; factorial table, one-time credit account, replication and operating scope legible.')
assert check['AI_tool_usage_disclosed']
(V/'qa/final_release_check.json').write_text(json.dumps(check,indent=2)+'\n',encoding='utf8')
deliver=members|{'main.pdf',zpath.name,'SOURCE_MANIFEST.json','qa/final_release_check.json'}
manifest=dict(version='v18',record_type='MANUSCRIPT_RELEASE_NOT_EXECUTION_SOURCE',files=[dict(path=n,bytes=(V/n).stat().st_size,sha256=sha(V/n))for n in sorted(deliver)])
(V/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
target=ROOT/'Paper_DSN/revisions/20261112_dsn2027_release_v18';assert target.resolve().is_relative_to((ROOT/'Paper_DSN/revisions').resolve())
for n in deliver|{'RELEASE_MANIFEST.json'}:
 p=target/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(V/n,p)
(E/'FINAL_RELEASE_CHECK.json').write_text(json.dumps(check,indent=2)+'\n',encoding='utf8')
print(json.dumps(check))
