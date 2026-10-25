"""Actual selected outcomes only; no labels or future lengths become features."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args();B=a.base
old=B/'results/revtrace/ces_v5_closed_loop_20261025';P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
target=O/'training_v1';assert not target.exists();target.mkdir()
read=lambda p:json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def batch_features(ts):
 n=len(ts);return [max(t['audio_seconds'] for t in ts)/20.,max(t['prompt_tokens'] for t in ts)/256.,
  max(t['candidate_tokens'] for t in ts)/256.,sum(t['candidate_tokens'] for t in ts)/n/256.,
  sum(t['same_birth'] for t in ts)/n,sum(t['previous_reject'] for t in ts)/n]
bank={'generate':[],'verify':[]};inputs=[]
for cell in sorted((old/'formal').iterdir()):
 if not (cell/'result.json').is_file():continue
 es=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()];rs=[json.loads(x) for x in (cell/'worker_records.jsonl').read_text().splitlines()]
 byid={r['job']['job_id']:r for r in rs};features={}
 for e in es:
  if e['kind']=='ces-decision' and e['operation']:
   for t in e['features']:
    if t['sid'] in e['sids']:features[t['sid'],t['window'],e['observed_perf']]=t
 accounts=[json.loads(x) for x in (cell/'worker_batch_accounting.jsonl').read_text().splitlines()]
 for batch in accounts:
  selected=[byid[j] for j in batch['job_ids']]
  if selected[0]['job']['role']!='authority':continue
  rows=[];ts=[];start=batch['worker_started_perf'];lease=batch['batch_drained_perf']-start
  phases=batch['phases'];v=next((p for p in phases if p['phase'].startswith('correct-context')),None)
  f=next((p for p in phases if p['phase']=='fresh-FP32-fallback'),None)
  for rec in selected:
   j,r=rec['job'],rec['result'];matches=[(clock,t) for (sid,w,clock),t in features.items() if sid==j['session_id'] and w==j['end_window'] and clock<=j['enqueue_perf']]
   t=max(matches,key=lambda z:z[0])[1] if matches else {'audio_seconds':j['audio_end_sample']/16000.,'prompt_tokens':len(j['prompt_tokens']),
     'candidate_tokens':len(j.get('candidate_token_ids',[])),'same_birth':False,'previous_reject':False}
   ts.append(t);bad=r.get('online_verification',{}).get('fallback_used',False)
   phase=f if bad else v
   relative=r['completed_perf']-(phase['started_perf'] if phase else start)
   phase_time=(phase['completed_perf']-phase['started_perf']) if phase else lease
   rows.append({'x':[t['audio_seconds']/20.,t['prompt_tokens']/256.,t['candidate_tokens']/256.,float(t['same_birth']),float(t['previous_reject'])],
       'fraction':min(1.,max(0.,relative/max(1e-9,phase_time))),'failed':bool(bad),
       'render_overhead':max(0.,relative-phase_time),'source_id':j['source_id']})
  op=selected[0]['job']['ces_operation'];bank[op].append({'n':len(selected),'x':batch_features(ts),'lease':lease,'K':sum(r['failed'] for r in rows),
   'verify_start':v['started_perf']-start if v else 0.,'verify_time':v['completed_perf']-v['started_perf'] if v else 0.,
   'fallback_start':f['started_perf']-start if f else 0.,'fallback_time':f['completed_perf']-f['started_perf'] if f else 0.,
   'rows':rows,'source_cell':cell.name,'batch_id':batch['batch_id']})
 for n in ['events.jsonl','worker_records.jsonl','worker_batch_accounting.jsonl']:
  inputs.append({'cell':cell.name,'file':n,'sha256':sha(cell/n)})
cal=read(B/'projects/revtrace_ces_v5_closed_loop_20261025/CALIBRATION.json');cal['v6_joint_risk']=bank
(target/'CALIBRATION.json').write_text(json.dumps(cal,indent=2)+'\n')
report={'status':'PASS_SELECTED_TRAINING_EXTRACTION','actual_batches':{k:len(v) for k,v in bank.items()},'same_n_support':{k:{str(n):sum(b['n']==n for b in v) for n in sorted({b['n'] for b in v})} for k,v in bank.items()},
 'features':'known audio/prompt/candidate length, birth relation and observed recent reject; no future length or fault label',
 'outputs_are_training_labels':['K','phase and lease times','row conditional render fractions'],
 'scope':'old72 reused development; selected outcomes are not unchosen counterfactuals or held-out confirmation','new_GPU_calls':0,
 'calibration_sha256':sha(target/'CALIBRATION.json'),'input_files':inputs}
(target/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='input_files'}))
