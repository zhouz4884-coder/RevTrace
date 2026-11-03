from pathlib import Path
import hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1]
s=importlib.util.spec_from_file_location('approved_transport',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
base=m.B+'/results/revtrace/dsn_editorial_v13_20261103/release_v13_final_metadata'
names=['FINAL_REPORT.zh.md','EDITORIAL_DELTA.zh.md','CLAIM_EVIDENCE.md','FINAL_RELEASE_GATE.json','FINAL_DEFAULT_SOURCE_GATE.json','SUBMISSION_PREFLIGHT.json','paper_qa/FINAL_QA.json','paper_qa/VISUAL_REVIEW.json','paper_qa/COLD_BUILD_QA.json','review/ANONYMOUS_PACKAGE_INDEPENDENT_REVIEW.zh.md','review/ANONYMOUS_PACKAGE_INDEPENDENT_REVIEW.json']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[dict(path=n,bytes=(E/n).stat().st_size,sha256=sha(E/n)) for n in names]
with m.Remote() as c:
 dirs=sorted({base+'/'+str(Path(n).parent).replace('\\','/') for n in names})
 c.python('from pathlib import Path\nb=Path('+repr(base)+')\nfor n in '+repr(dirs)+':\n p=Path(n);assert p.resolve().is_relative_to(b.resolve());p.mkdir(parents=True,exist_ok=True)\n')
 for n in names:c.put(E/n,base+'/'+n)
 result=c.python('from pathlib import Path\nimport hashlib,json\nb=Path('+repr(base)+')\nrows='+repr(rows)+'\nfor r in rows:\n p=b/r["path"];assert p.stat().st_size==r["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==r["sha256"]\nprint(json.dumps(dict(status="PASS_FINAL_EDITORIAL_METADATA_8TB_READBACK",files=len(rows),archive_root=str(b))))\n')
record=json.loads(result);record['rows']=rows;(E/'FINAL_METADATA_ARCHIVE_RECEIPT.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(result.decode())
