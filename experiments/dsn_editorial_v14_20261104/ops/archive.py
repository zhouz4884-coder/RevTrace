"""Immutable bounded editorial archive on the designated experiment disk."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];P=R/'Paper_DSN/revisions/20261104_dsn2027_release_v14'
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base=m.B+'/results/revtrace/dsn_editorial_v14_20261104';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();items=[]
def add(p,n):
 p=Path(p);assert p.stat().st_size<20_000_000;items.append(dict(local=p,target=base+'/'+n,path=n,bytes=p.stat().st_size,sha256=sha(p)))
for version in ['v1','v2']:
 for name in ['SUMMARY.json','GATE.json','PDFFONTS.txt','COLD_BUILD.txt']:add(E/'paper_qa'/('FINAL_'+version)/name,'editorial_qa_'+version+'/'+name)
 for name in ['QA_SOURCE_'+version+'.json','QA_SOURCE_'+version+'.bundle']:add(E/'packages'/name,'editorial_qa_'+version+'/'+name)
 if version=='v1':
  for name in ['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json']:add(E/'paper_qa'/name,'editorial_qa_v1/'+name)
  add(E/'paper_qa/candidate1/RevTrace_DSN2027_anonymous_source_v14.zip','editorial_qa_v1/SOURCE_CANDIDATE.zip')
 else:
  for name in ['CONFIG_v2.json','ENVIRONMENT_v2.json','RUN_RECORD_v2.json']:add(E/'paper_qa'/name,'editorial_qa_v2/'+name)
for name in ['main.pdf','RevTrace_DSN2027_anonymous_source_v14.zip','RevTrace_DSN2027_anonymous_evidence_v13.zip','PACKAGING_PROVENANCE.json']:add(P/name,'release/'+name)
for name in ['FINAL_REPORT.zh.md','EDITORIAL_DELTA.zh.md','CLAIM_EVIDENCE_DELTA.md','FINAL_RELEASE_GATE.json','FINAL_DEFAULT_SOURCE_GATE.json','ROOT_NOARG_QA_v2.json','MANUSCRIPT_DIFF.patch']:add(E/name,'release/'+name)
for p in (E/'review').iterdir():
 if p.is_file():add(p,'release/review/'+p.name)
for p in (E/'paper_qa/render_5462d73d98a7').glob('*.png'):add(p,'release/render/'+p.name)
expected={r['target']:dict(bytes=r['bytes'],sha256=r['sha256']) for r in items}
with m.Remote() as c:
 dirs=sorted({str(Path(x['target']).parent).replace('\\','/') for x in items})
 c.python('from pathlib import Path\nimport os\nb=Path('+repr(base)+');root=Path('+repr(m.B)+');s=os.statvfs(root);assert root.is_dir() and s.f_blocks*s.f_frsize>6_000_000_000_000\nfor n in '+repr(dirs)+':\n p=Path(n);assert p.resolve().is_relative_to(b.resolve());p.mkdir(parents=True,exist_ok=True)\n')
 for row in items:c.put(row['local'],row['target'])
 result=c.python('from pathlib import Path\nimport hashlib,json\nx='+repr(expected)+'\nfor n,r in x.items():\n p=Path(n);assert p.stat().st_size==r["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==r["sha256"]\nprint(json.dumps(dict(status="PASS_8TB_V14_EDITORIAL_IMMUTABLE_ARCHIVE_READBACK",files=len(x),bytes=sum(r["bytes"] for r in x.values()))))\n')
record=json.loads(result);record.update(archive_root=base,new_model_calls=0,new_GPU_runs=0,rows=[{k:v for k,v in row.items() if k not in ['local','target']} for row in items]);(E/'REMOTE_ARCHIVE_RECEIPT.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(result.decode())
