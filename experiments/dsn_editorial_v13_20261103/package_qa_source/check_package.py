"""Check the deliverable ZIP after fresh extraction, never using manuscript helpers."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,zipfile
import fitz
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
m=json.loads(a.manifest.read_bytes());g=lambda *args:subprocess.check_output(['git','-C',str(HERE),*args],text=True).strip()
assert not g('status','--porcelain','--untracked-files=all') and g('rev-parse','HEAD')==m['code_commit']
assert set(g('ls-files').splitlines())=={r['path'] for r in m['files']}
for r in m['files']:assert sha(HERE/r['path'])==r['sha256']
c=json.loads(a.config.read_bytes());assert sha(c['archive'])==c['archive_sha256']
a.out.mkdir(parents=True,exist_ok=False);target=a.out/'fresh_extraction';target.mkdir()
with zipfile.ZipFile(c['archive']) as z:
 for name in z.namelist():
  path=(target/name).resolve();assert path.is_relative_to(target.resolve());path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(name))
pm=json.loads((target/'MANIFEST.json').read_bytes())
for r in pm['files']:
 path=target/r['path'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
for name in ['reproduce_figures.py','verify_reported_statistics.py']:assert sha(target/name)==sha(HERE/name)
for name,args in [('verify_reported_statistics.py',[]),('reproduce_figures.py',['--out',str((a.out/'regenerated_figures').resolve())])]:
 r=subprocess.run([sys.executable,'-B',str(target/name),*args],cwd=target,capture_output=True)
 (a.out/(name+'.txt')).write_bytes(r.stdout+r.stderr)
 assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')[-1500:]
plots=[]
for name in ['timely_full_interval_case','coordination_protocol','core_interaction','native_content','source8_paired_effects']:
 old=Path(c['frozen_figure_export'])/(name+'.pdf');new=a.out/'regenerated_figures'/(name+'.pdf')
 x=fitz.open(old)[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
 y=fitz.open(new)[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
 assert x.width==y.width and x.height==y.height and x.samples==y.samples,name
 plots.append(dict(name=name,frozen_pdf_sha256=sha(old),regenerated_pdf_sha256=sha(new),pixels_identical=True))
report=json.loads((a.out/'verify_reported_statistics.py.txt').read_bytes())
assert report['gate']=='PASS_FROZEN_SUMMARY_ARITHMETIC_AND_PAIRED_BOOTSTRAP'
assert len(pm['snapshots'])==6 and sum(r['complete_source_files'] for r in pm['snapshots'])==103
result=dict(status='PASS_FRESH_ANONYMOUS_EVIDENCE_SOURCE_STATISTICS_AND_FIGURE_REPRODUCTION',qa_code_commit=m['code_commit'],archive_sha256=c['archive_sha256'],archive_files=len(pm['files'])+1,package_manifest_sha256=sha(target/'MANIFEST.json'),frozen_runtime_source_files=59,exact_source_snapshot_files=103,source_snapshots=6,all_packaged_file_hashes_checked=True,reported_statistics=report,regenerated_figures=plots,all_five_figures_pixel_identical=True,new_model_calls=0,raw_service_readers=0,scope='Reproduces frozen summaries and plotting only; original raw journals and model inference are not rerun')
put(a.out/'SUMMARY.json',result);put(a.out/'GATE.json',dict(status=result['status'],new_model_calls=0,raw_service_readers=0))
assert sha(c['archive'])==c['archive_sha256']
for r in m['files']:assert sha(HERE/r['path'])==r['sha256']
print(json.dumps({k:v for k,v in result.items() if k not in ['regenerated_figures','reported_statistics']}))
