"""Existing-clock feasibility screens only; no synthetic replacement outputs."""
from collections import defaultdict
from pathlib import Path
import csv,hashlib,json,sys

B=Path(sys.argv[1]);O=B/'results/revtrace/online_admission_20261022'
D=O/'C2_RESIDUAL_OPPORTUNITY_v1';D.mkdir(exist_ok=False)
index={r['path']:r for r in json.loads((O/'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())['files']}
def read(p,lines=False):
 raw=p.read_bytes();r=index[p.relative_to(O).as_posix()]
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return [json.loads(x) for x in raw.splitlines()] if lines else json.loads(raw)
rows=[];examples=[];reason_rows=[]
try:
 for C in sorted((O/'formal_v1').iterdir()):
  if not C.is_dir() or not (C/'config.json').is_file():continue
  cfg=read(C/'config.json');method=cfg['online_study']['method']
  if method not in ['fine','dgft','standard']:continue
  es=read(C/'events.jsonl',True);rs=read(C/'worker_records.jsonl',True);vs=read(C/'consumer.jsonl',True)
  t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
  auth=[r for r in rs if r['job']['role']=='authority'];props=[r for r in rs if r['job']['role']=='proposal']
  commits={(e['session_id'],e['version']):e for e in es if e['kind']=='commit'}
  for proof in [e for e in es if e['kind']=='private-continuity-proof']:
   reason='pass' if proof['eligible'] else proof['witness']
   reason_rows.append({'cell':C.name,'method':method,'traffic':cfg['online_study']['traffic'],
     'reason':reason,'version':proof['canonical_version'],'source_session':proof['session_id']})
   if proof['eligible']:continue
   sid=proof['session_id'];detect=t0+proof['time'];F=proof['certified_frontier']
   install=commits[sid,proof['canonical_version']]
   pending=[r for r in props if r['job']['session_id']==sid and r['job']['audio_end_sample']>F
            and r['job']['enqueue_perf']<=detect<r['result']['completed_perf']]
   assert len(pending)<=1
   for r in pending:
    j,z=r['job'],r['result'];pub=next((e for e in es if e['kind']=='display' and e['job_id']==j['job_id']),None)
    observed=next((v for v in vs if pub and v['session_id']==sid and v['source_kind']=='display' and v['server_time']==pub['displayed']),None)
    next_start=min((a['result']['started_perf'] for a in auth if a['result']['started_perf']>detect),default=None)
    item={'cell':C.name,'method':method,'traffic':cfg['online_study']['traffic'],'load':C.name.split('-')[1],
     'source_id':j['source_id'],'reason':reason,'version':proof['canonical_version'],
     'detected_s':proof['time'],'installed_s':install['installed'],
     'new_canonical_audio_s':F/16000,'pending_job_id':j['job_id'],
     'pending_frontier_audio_s':j['audio_end_sample']/16000,
     'pending_enqueued_s':j['enqueue_perf']-t0,'pending_completed_s':z['completed_perf']-t0,
     'remaining_old_job_worker_s':z['completed_perf']-detect,
     'display_deadline_slack_s':j['audio_ready_perf']+2-detect,
     'next_actual_authority_worker_start_gap_s':next_start-detect if next_start is not None else None,
     'pending_later_publication_failed_visibility':bool(pub and (not observed or observed['valid_visible_frontier']<j['audio_end_sample'])),
     'later_publication_or_obsolete':'published' if pub else 'no-publication',
     'not_a_measured_rescue_runtime_or_speedup':True}
    rows.append(item)
  # Full non-text clock witnesses for one source at the lost14s frontier.
  if C.name in ['dgft-sync16-F2-r0','fine-sync16-F2-r0']:
   for e in es:
    if e.get('session_id')!=15 or not (9<=e['time']<=18):continue
    if e['kind'] not in ['enqueue','display','canonical-display','private-continuity-proof','proposal-rebase','commit','proposal-obsolete']:continue
    examples.append({'cell':C.name,**{k:v for k,v in e.items() if k in ['kind','time','job_id','role','parent','chunk_id','end_window','audio_start_sample','audio_end_sample','parent_frontier','next_window','eligible','witness','canonical_version','certified_frontier','installed','displayed','branch_generation']}})
 for name,data in [('PENDING_CONFLICT_AND_SLACK.csv',rows),('PRIVATE_PROOF_REASONS.csv',reason_rows)]:
  with (D/name).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 (D/'TIMELINE_WITNESSES.json').write_text(json.dumps(examples,indent=2)+'\n')
 out={'status':'PASS_OBSERVED_CONFLICT_AND_SLACK_SCREEN','covered_formal_cells':36,
  'pending_conflict_exposures':len(rows),'not_new_independent_sources':True,
  'new_model_calls':0,'scope':'Only observed trigger timing and idle-gap evidence; additional generation time, compatibility and end-to-end benefit must be tested',
  'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
except BaseException as e:
 (D/'STOP.json').write_text(json.dumps({'error':repr(e),'original_raw_unchanged':True})+'\n');raise
