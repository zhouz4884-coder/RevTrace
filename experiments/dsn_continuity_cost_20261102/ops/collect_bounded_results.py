"""Collect bounded terminal evidence; leave spans/models/full logs on8TB."""
from pathlib import Path
import hashlib,json
from remote import Remote,E,O
jobs=[
 (O+'/cost_analysis_v1/aggregate_v1',E/'cost/FINAL_AGGREGATE',
  ['SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','PAPER_DATA.json',
   'CPU_REAL_OBJECT_CHECKS.csv','NN_CELLS.csv','OBSERVATION_PAIRS.csv','UNSUBTRACTED_FAMILY_FOOTPRINTS.csv','PAPER_COARSE_FOOTPRINT.csv','UNSUBTRACTED_FOOTPRINT_SCOPE.md']),
 (O+'/cost_analysis_v1/clock_calibration_v1',E/'cost/FINAL_CALIBRATION',
  ['SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json']),
 (O+'/cost_independent_v1',E/'review/FINAL_COST_INDEPENDENT',
  ['SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json']),
 (O+'/cost_c4_closure_v1',E/'cost/FINAL_C4_CLOSURE',
  ['SUMMARY.json','GATE.json','CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json']),
]
receipt=[]
with Remote() as c:
 for remote,local,names in jobs:
  for name in names:
   try:raw=c.get(remote+'/'+name,local/name)
   except FileNotFoundError:
    if name in {'CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json'}:continue
    raise
   receipt.append(dict(remote=remote+'/'+name,local=(local/name).relative_to(E).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 # Four positive-history attempts only: original full input traces stay on8TB.
 for bank,tag in [('h_all_v3','n5-031'),('h_all_v3','n5-061'),('h_all_v3','n5-099'),('h_current_s_on_v3','current_stability-017')]:
  for name in ['SUMMARY.json','GAPS.json','CUTS.json','INPUTS.json']:
   local=E/'history/BOUNDED_POSITIVE_TRACES'/bank/tag/name
   raw=c.get(O+'/'+bank+'/'+tag+'/'+name,local)
   receipt.append(dict(remote=O+'/'+bank+'/'+tag+'/'+name,local=local.relative_to(E).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
record=dict(gate='PASS_BOUNDED_TERMINAL_EVIDENCE_TRANSFER',files=len(receipt),bytes=sum(r['bytes'] for r in receipt),
            raw_models_spans_full_logs_retained_on8TB=True,rows=receipt)
p=E/'BOUNDED_COLLECTION_MANIFEST_v1.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in record.items() if k!='rows'}))
