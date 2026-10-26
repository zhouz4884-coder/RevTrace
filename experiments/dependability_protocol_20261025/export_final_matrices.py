from pathlib import Path
import csv,hashlib,json
W=Path(__file__).resolve().parent;O=W/'final_matrices_v3';O.mkdir(exist_ok=False)
for src,prefix in [('UNIFIED_FAULT_MATRIX_v3.md','FAULT'),('CONTRIBUTION_EVIDENCE_MATRIX_v3.md','CONTRIBUTION')]:
 tables=[];current=[]
 for line in (W/src).read_text(encoding='utf8').splitlines()+['']:
  if line.startswith('|'):current.append([x.strip() for x in line.strip('|').split('|')])
  elif current:
   headers=current[0];rows=current[2:];assert all(len(r)==len(headers) for r in rows)
   tables.append([dict(zip(headers,r)) for r in rows]);current=[]
 for n,rows in enumerate(tables,1):
  with (O/f'{prefix}_{n}.csv').open('w',newline='',encoding='utf8') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (O/f'{prefix}.json').write_text(json.dumps(dict(source=src,source_sha256=hashlib.sha256((W/src).read_bytes()).hexdigest(),tables=tables),indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print('Final fault/contribution/reviewer-objection matrices exported without changing claims')
