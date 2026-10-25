"""Replay actual anchor decisions, including the pre-fix zero-credit witness."""
from pathlib import Path
import argparse,hashlib,json,math,sys
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--stage',required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args();O=a.root
sys.path.insert(0,str(a.source/'src'))
from revtrace.ces_anchor import ConditionalRiskModel,choose_anchor,quantile
from revtrace.ces_v5_policy import V5Target
out=O/(a.stage+'_policy_audit');out.mkdir();results=[]
for C in sorted(p for p in (O/a.stage).iterdir() if p.is_dir()):
 cfg=json.loads((C/'config.json').read_text());options=cfg['ces_study'].get('v6',{})
 if options.get('policy') not in ['anchor_cost','anchor_causal']:continue
 es=[json.loads(x) for x in (C/'events.jsonl').read_text().splitlines()];ss=json.loads((C/'sessions.json').read_text());spec={s['session_id']:s for s in ss}
 t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');seen={};committed={};credit={};ages={};times=[];verified=deviations=overruns=nonzero=0;model=ConditionalRiskModel(cfg['ces_study']['calibration'].get('v6_joint_risk',{}))
 for e in es:
  if e['kind']=='commit':
   window=math.ceil(e['audio_end_sample']/32000)
   committed[e['session_id'],window]=(t0+e['installed'],t0+e['audio_ready'],(e['audio_end_sample']-e['audio_start_sample'])/16000.)
  if e['kind']=='ces-consumer-ack':
   s=spec[e['session_id']];total=round(s['duration']*16000)
   for w,f in enumerate(list(range(32000,total,32000))+[total],1):
    if f<=e['valid_visible_frontier']:
     key=e['session_id'],w;seen[key]=min(seen.get(key,float('inf')),e['observed_perf'])
  if e['kind']!='ces-decision' or 'v6_policy' not in e:continue
  rows=sorted((V5Target(**r) for r in e['features']),key=lambda t:(t.ready,t.sid))[:cfg['microbatch']]
  now=e['observed_perf'];fixed='v6_observed_credit_rate' in e
  for key,(installed,released,audio) in committed.items():
   if key in seen and seen[key]<=released+2 and installed<=released+8:credit[key]=audio
  rate=sum(credit.values())/max(.01,now-t0) if fixed else 0.
  if fixed:assert abs(e['v6_observed_credit_rate']-rate)<1e-8,(C.name,rate,e['v6_observed_credit_rate'])
  nonzero+=rate>0
  for t in rows:
   for key in list(ages):
    if key[0]==t.sid and key!=(t.sid,t.window):del ages[key]
   ages.setdefault((t.sid,t.window),0)
  budget=max(.0001,quantile(times,.9) if times else options.get('initial_plan_budget_s',.005))+options.get('dispatch_allowance_s',.002)
  assert abs(budget-e['v6_planning_budget_seconds'])<1e-8
  expected=choose_anchor(rows,now=now+budget,cal=cfg['ces_study']['calibration'],options=dict(options,policy='causal' if options['policy']=='anchor_causal' else 'cost'),deferrals={t.sid:ages[t.sid,t.window] for t in rows},risk=e['v6_observable_risk'],observed_rate=rate,predictor=model)
  if e['reason']=='anchor-planning-age-overrun-default':
   assert expected.get('chosen_index',0)>0 and e['v6_issue_check_perf']>now+budget
   assert e['operation']=='generate' and e['sids']==[t.sid for t in rows];overruns+=1
  else:
   for key in ['operation','sids','reason','plan','chosen_index']:
    if key in expected:assert e[key]==expected[key],(C.name,key,e.get(key),expected[key])
   if 'anchor_scores' in expected:assert e['anchor_scores']==expected['anchor_scores']
  selected=set(e['sids'])
  for t in rows:ages[t.sid,t.window]=0 if t.sid in selected else ages[t.sid,t.window]+1
  times.append(e['v6_chooser_wall_seconds']);verified+=1;deviations+=e.get('chosen_index',0)>0
 results.append({'cell':C.name,'decisions_recomputed':verified,'supported_deviations':deviations,'planning_overrun_to_Fine':overruns,'decisions_with_nonzero_actual_rate':nonzero,'pre_fix_zero_rate':not any('v6_observed_credit_rate' in e for e in es if e['kind']=='ces-decision' and 'v6_policy' in e),'source':str(a.source),'safety_permission_unchanged':True})
report={'status':'PASS_ACTUAL_ANCHOR_POLICY_REPLAY','stage':a.stage,'cells':results,'decisions':sum(r['decisions_recomputed'] for r in results),'model_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
