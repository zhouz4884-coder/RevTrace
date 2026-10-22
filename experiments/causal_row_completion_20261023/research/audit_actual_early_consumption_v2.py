"""Actual Consumer applications, not internal commit markers or send clocks."""
from pathlib import Path
import csv,hashlib,json,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'actual_early_consumer_v2';assert not D.exists();D.mkdir()
assert json.loads((O/'FINAL_CLOSED_EVIDENCE_v1/SUMMARY.json').read_text())['status']=='PASS_FINAL_CLOSED_UNION_AND_TASK_RELEASE'
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
table=[];witnesses=[]
for stage in ['formal_row_v1','validation_row_v1']:
 for C in sorted((O/stage).iterdir()):
  if not C.is_dir() or not (C/'result.json').exists():continue
  cfg=read(C/'config.json')
  if cfg['result_delivery']!='row':continue
  es=lines(C/'events.jsonl');vs=lines(C/'consumer.jsonl');rs=lines(C/'worker_records.jsonl')
  pubs={e['job_id']:e for e in es if e['kind']=='canonical-display'}
  saved={(v['session_id'],v['source_kind'],v['server_time']):v for v in vs}
  accounts={a['batch_id']:a for a in lines(C/'worker_batch_accounting.jsonl')}
  before_drain=before_fallback=0
  for r in rs:
   j,z=r['job'],r['result']
   if j['role']!='authority':continue
   p=pubs[j['job_id']];v=saved[p['session_id'],p['kind'],p['displayed']]
   assert v['certified_frontier']>=j['audio_end_sample']
   a=accounts[z['physical_batch_id']];early=v['observed_perf']<a['batch_drained_perf'];before_drain+=early
   proof=z.get('online_verification');passed=bool(proof and not proof['fallback_used'])
   f=[q for q in a['phases'] if q['phase']=='fresh-FP32-fallback']
   fb_early=bool(passed and f and v['observed_perf']<max(x['completed_perf'] for x in f));before_fallback+=fb_early
   if early or fb_early:witnesses.append({'stage':stage,'cell':C.name,'job_id':j['job_id'],'certified_consumer_observed_perf':v['observed_perf'],
     'physical_batch_drained_perf':a['batch_drained_perf'],'peer_fallback_end_perf':max((x['completed_perf'] for x in f),default=None),
     'actual_canonical_consumer_before_drain':early,'verified_success_consumer_before_peer_fallback_end':fb_early})
  table.append({'stage':stage,'cell':C.name,'method':cfg['online_study']['method'],'actual_canonical_consumer_before_batch_drain':before_drain,
    'actual_verified_success_consumer_before_peer_fallback_end':before_fallback,'not_an_acknowledgement_or_wire_send_proxy':True})
assert len(table)==90  #60core row cells+30all-row validation cells
for name,data in [('CELL_COUNTS.csv',table),('ACTUAL_CONSUMER_WITNESSES.csv',witnesses)]:
 with (D/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
out={'status':'PASS_ACTUAL_CANONICAL_CONSUMER_EARLY_APPLICATION_CLOCKS','row_delivery_cells':90,
 'canonical_applications_before_physical_drain':sum(r['actual_canonical_consumer_before_batch_drain'] for r in table),
 'verified_success_applications_before_peer_fallback_end':sum(r['actual_verified_success_consumer_before_peer_fallback_end'] for r in table),
 'new_model_calls':0,'scope':'actual independent local Consumer thread applications;not browser/network delivery or crash-after-client-ack evidence',
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
