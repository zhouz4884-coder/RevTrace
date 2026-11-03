"""Archive only the bounded editorial outputs on the designated experiment disk."""
from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1]
spec=importlib.util.spec_from_file_location('approved_remote_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');remote=importlib.util.module_from_spec(spec);spec.loader.exec_module(remote)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
BASE=remote.B+'/results/revtrace/dsn_editorial_v13_20261103'
items=[]
def add(local,rel):
 p=Path(local);assert p.is_file() and p.stat().st_size<20_000_000
 items.append(dict(local=p,remote=BASE+'/'+rel,relative=rel,bytes=p.stat().st_size,sha256=sha(p)))
for tag in ['v1','v2']:
 prefix='figure_exports_'+tag
 for p in sorted((E/'figures'/('EXPORT_'+tag)).iterdir()):
  if p.is_file():add(p,prefix+'/'+p.name)
 for local,name in [(E/'figures'/('RUN_RECORD_'+tag+'.json'),'RUN_RECORD.json'),(E/'figures'/('ENVIRONMENT_'+tag+'.json'),'ENVIRONMENT.json'),(E/'figures'/('ROOT_DEFAULT_SOURCE_GATE_'+tag+'.json'),'DEFAULT_NN_SOURCE_GATE.json'),(E/'packages'/('FIGURE_SOURCE_'+tag+'.json'),'SOURCE_MANIFEST.json'),(E/'packages'/('FIGURE_SOURCE_'+tag+'.bundle'),'SOURCE.bundle'),(E/'figure_source/CONFIG.json','CONFIG.json')]:add(local,prefix+'/'+name)
q=E/'paper_qa';prefix='anonymous_package_qa_v1'
for name in ['SUMMARY.json','GATE.json','verify_reported_statistics.py.txt','reproduce_figures.py.txt']:add(q/'anonymous_evidence_check'/name,prefix+'/'+name)
for p in sorted((q/'anonymous_evidence_check/regenerated_figures').iterdir()):
 if p.is_file():add(p,prefix+'/regenerated_figures/'+p.name)
for local,name in [(q/'ANONYMOUS_EVIDENCE_QA_RUN_RECORD.json','RUN_RECORD.json'),(q/'ANONYMOUS_EVIDENCE_QA_CONFIG.json','CONFIG.json'),(q/'ANONYMOUS_EVIDENCE_QA_ENVIRONMENT.json','ENVIRONMENT.json'),(E/'packages/PACKAGE_QA_SOURCE_v1.json','SOURCE_MANIFEST.json'),(E/'packages/PACKAGE_QA_SOURCE_v1.bundle','SOURCE.bundle')]:add(local,prefix+'/'+name)
paper=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13'
for name in ['main.pdf','RevTrace_DSN2027_anonymous_source_v13.zip','RevTrace_DSN2027_anonymous_evidence_v13.zip','PACKAGING_PROVENANCE.json']:
 add(paper/name,'release_v13/'+name)
for name in ['FINAL_QA.json','COLD_BUILD_QA.json','ANONYMOUS_EVIDENCE_BUILD.json','PDFFONTS.txt']:
 add(q/name,'release_v13/qa/'+name)
for p in sorted((E/'review').glob('*')):
 if p.is_file():add(p,'release_v13/review/'+p.name)
for name in ['EDITORIAL_DELTA.zh.md','CLAIM_EVIDENCE.md']:
 add(E/name,'release_v13/'+name)
expected={r['remote']:dict(bytes=r['bytes'],sha256=r['sha256']) for r in items}
assert len(expected)==len(items)
with remote.Remote() as c:
 pre=c.python('from pathlib import Path\nimport json,os,subprocess\nb=Path('+repr(remote.B)+');s=os.statvfs(b);assert b.is_dir() and s.f_blocks*s.f_frsize>6_000_000_000_000\nprint(json.dumps(dict(disk_bytes=s.f_blocks*s.f_frsize,available_bytes=s.f_bavail*s.f_frsize,mount=subprocess.check_output(["findmnt","-T",str(b),"-n","-o","SOURCE,FSTYPE,TARGET"],text=True).strip())))\n')
 dirs=sorted({str(Path(r['remote']).parent).replace('\\','/') for r in items})
 c.python('from pathlib import Path\nb=Path('+repr(BASE)+')\nfor n in '+repr(dirs)+':\n p=Path(n);assert p.resolve().is_relative_to(b.resolve());p.mkdir(parents=True,exist_ok=True)\n')
 for r in items:c.put(r['local'],r['remote'])
 result=c.python('from pathlib import Path\nimport hashlib,json\nx='+repr(expected)+'\nfor n,e in x.items():\n p=Path(n);assert p.stat().st_size==e["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==e["sha256"],n\nprint(json.dumps(dict(status="PASS_DESIGNATED_8TB_BOUNDED_EDITORIAL_ARCHIVE_READBACK",files=len(x),bytes=sum(r["bytes"] for r in x.values()),all_file_hashes_verified=True,archive_root='+repr(BASE)+')))\n')
record=json.loads(result);record.update(disk=json.loads(pre),new_model_calls=0,new_GPU_runs=0,scope='Administrative bounded-output archive and readback; no original raw/model files modified',files=[dict(path=r['relative'],bytes=r['bytes'],sha256=r['sha256']) for r in items])
(E/'REMOTE_ARCHIVE_RECEIPT.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='files'}))
