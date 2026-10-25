"""Bounded historical intake, manifest verification, no new GPU evidence."""
from pathlib import Path
import csv,hashlib,json,shutil
W=Path(__file__).resolve().parent
S=Path(r'D:\StreamTxn\outputs\revtrace_dsn_sixweek_20261018')
O=W/'historical_20261020';O.mkdir(exist_ok=False)
idx=json.loads((S/'EVIDENCE_INDEX.json').read_text());rows=[]
names=['SOURCE_E1_IDENTITY.json','SOURCE_E2_IDENTITY.json','E1_AUDIT_EVIDENCE_20261020.tar.gz',
       'E1_CPU_PROJECTION_AUDIT_20261020.json','E1_INDEPENDENT_AUDIT_20261020.json',
       'E2_AGGREGATE_20261020.json','E2_INDEPENDENT_AUDIT_20261020.json']
for name in names:
 expected=next(r for r in idx['files'] if r['path']==name)
 paths=[S/name,S/'review_extension'/name]
 valid=[p for p in paths if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==expected['sha256']]
 assert valid,name
 p=valid[0];shutil.copyfile(p,O/name)
 rows.append(dict(expected,original_path=str(p)))
for name in ['RESULTS_REPORT.zh.md','PROTOCOL_E1.md','EVIDENCE_INDEX.json']:
 p=S/name;shutil.copyfile(p,O/name)
 rows.append({'path':name,'original_path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
p=S/'review_extension/E1_CASES_20261020.csv';shutil.copyfile(p,O/p.name)
cases=list(csv.DictReader(p.open(newline='',encoding='utf8')))
audit=json.loads((O/'E1_INDEPENDENT_AUDIT_20261020.json').read_text())
assert len(cases)==audit['contexts']==24 and len({r['source_id'] for r in cases})==12
counts={k:sum(r[k]=='True' for r in cases) for k in ['raw_projection_diff','reconstruction_diff',
   'authority_repeat_equal','future_repeat_equal','new_future_tokens_differ','correct_rescore_pass']}
for k,v in counts.items():assert v==audit['counts'][k],k
effects={v:sum(r['quality_effect']==v for r in cases) for v in ['worse_without_protection','equal_error_count','better_without_protection']}
assert effects==audit['future_quality_effects']
(O/'INTAKE_AND_CASE_RECOUNT.json').write_text(json.dumps({'status':'PASS_IDENTITIES_AND_CASE_RECOUNT',
 'files':rows,'case_counts':counts,'effects':effects,
 'not_new_GPU_or_processor_reexecution':True,'public_intake_scope':'E1/E0 predate public experiment-prefix archiving; retain this explicit local historical source provenance.'},indent=2)+'\n')
print(json.dumps({'verified_files':len(rows),'contexts':len(cases),'effects':effects}))
