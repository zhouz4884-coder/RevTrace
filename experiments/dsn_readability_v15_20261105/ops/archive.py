from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261105_dsn2027_release_v15'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base=m.B+'/results/revtrace/dsn_readability_v15_20261105';fig=m.B+'/experiments/dsn_readability_v15_20261105/figure_editorial/EXPORT_v1';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();items=[]
def add(p,target):
 p=Path(p);assert p.is_file() and p.stat().st_size<20_000_000;items.append(dict(local=p,target=target,bytes=p.stat().st_size,sha256=sha(p)))
for p in (E/'figures/EXPORT_v1').iterdir():
 if p.is_file():add(p,fig+'/'+p.name)
for p in (E/'review').glob('FIGURE*'):
 if p.is_file():add(p,fig+'/identity/'+p.name)
add(E/'packages/FIGURE_SOURCE_v1.bundle',fig+'/identity/SOURCE.bundle')
for name in ['SUMMARY.json','GATE.json','NUMERIC_LEDGER.json','PDFFONTS.txt','COLD_BUILD.txt','FIGURE1_REPRODUCTION.txt']:add(E/'paper_qa/FINAL_v1'/name,base+'/editorial_qa_v1/'+name)
for name in ['CONFIG_v1.json','ENVIRONMENT_v1.json','RUN_RECORD_v1.json']:add(E/'paper_qa'/name,base+'/editorial_qa_v1/'+name)
for p in (E/'packages').glob('QA_SOURCE*'):add(p,base+'/editorial_qa_v1/'+p.name)
for name in ['main.pdf','RevTrace_DSN2027_anonymous_source_v15.zip','RevTrace_DSN2027_anonymous_evidence_v13.zip','PACKAGING_PROVENANCE.json']:add(P/name,base+'/release/'+name)
for name in ['FINAL_REPORT.zh.md','EDITORIAL_DELTA.zh.md','FINAL_RELEASE_GATE.json','MANUSCRIPT_DIFF.patch','ROOT_NOARG_QA_v1.json']:add(E/name,base+'/release/'+name)
for p in (E/'review').iterdir():
 if p.is_file() and not p.name.startswith('FIGURE'):add(p,base+'/release/review/'+p.name)
for p in (E/'paper_qa/render_b5c410b6c6fd').glob('*.png'):add(p,base+'/release/render/'+p.name)
expected={r['target']:dict(bytes=r['bytes'],sha256=r['sha256']) for r in items};assert len(expected)==len(items)
with m.Remote() as c:
 dirs=sorted({str(Path(r['target']).parent).replace('\\','/') for r in items})
 c.python('from pathlib import Path\nimport os\nb=Path('+repr(m.B)+');s=os.statvfs(b);assert s.f_blocks*s.f_frsize>6_000_000_000_000\nfor n in '+repr(dirs)+':\n p=Path(n);assert p.resolve().is_relative_to(b.resolve());p.mkdir(parents=True,exist_ok=True)\n')
 for row in items:c.put(row['local'],row['target'])
 result=c.python('from pathlib import Path\nimport hashlib,json\nx='+repr(expected)+'\nfor n,r in x.items():\n p=Path(n);assert p.stat().st_size==r["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==r["sha256"]\nprint(json.dumps(dict(status="PASS_V15_BOUNDED_8TB_ARCHIVE_AND_FIGURE_DECLARED_PATH",files=len(x),bytes=sum(r["bytes"] for r in x.values()))))\n')
record=json.loads(result);record.update(raw_qa_archive=base+'/editorial_qa_v1',declared_figure_archive=fig,new_model_calls=0,new_GPU_runs=0,rows=[{k:v for k,v in x.items() if k!='local'} for x in items]);(E/'REMOTE_ARCHIVE_RECEIPT.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(result.decode())
