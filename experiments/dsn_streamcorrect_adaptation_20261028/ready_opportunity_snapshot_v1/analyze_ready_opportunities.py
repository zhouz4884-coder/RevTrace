"""Actual complete-input/ready-opportunity recount; no candidate-handoff claim."""
import pathlib,json,hashlib,subprocess,sys,argparse,collections,statistics,datetime,platform
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text())
def lines(p):return [json.loads(x) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def stats(xs):return dict(n=len(xs),mean=statistics.mean(xs) if xs else None,median=statistics.median(xs) if xs else None,minimum=min(xs) if xs else None,maximum=max(xs) if xs else None)
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True)
 plan=read(a.plan);env=a.out/'ENVIRONMENT.json';env.write_text(json.dumps(dict(python=sys.version,platform=platform.platform(),dependencies='Python standard library only'),indent=2));config=a.out/'CONFIG.json';config.write_text(json.dumps(dict(native_plan=str(a.plan),native_plan_sha256=sha(a.plan),criterion='complete source/start state JSON equality, same end frontier/is_last; primary ready=private-admission journal row before Authority dispatch row; no full top-k candidate packet recorded'),indent=2))
 (a.out/'RUN_RECORD.json').write_text(json.dumps(dict(experiment_id='SC_NATIVE_ACTUAL_READY_OPPORTUNITIES_V1',code_commit=commit,frozen_config=str(config),frozen_config_sha256=sha(config),environment_record=str(env),environment_record_sha256=sha(env),raw_result_location='original14 native jobs/events journals on designated disk',aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2))
 cells=[];allpairs=[];timing=collections.defaultdict(list)
 for cell in plan['cells']:
  out=pathlib.Path(cell['out']);jobs=lines(out/'native_jobs.jsonl');events=lines(out/'events.jsonl');dispatch={x['job_id']:(i,x) for i,x in enumerate(events) if x['kind']=='dispatch'};admission={x['job_id']:(i,x) for i,x in enumerate(events) if x['kind']=='private-admission'};private=collections.defaultdict(list);pairs=[];authority=[]
  for j in jobs:
   r=j['record'];role=r['role'];key=(j['source_id'],encode(j['start']),r['end'],r['is_last'])
   if role=='private':private[key].append(j)
   else:authority.append(j)
   if r['native_model_evaluated']:timing[(cell['stage'],cell['arm'],role)].append(r['model_seconds'])
  for j in authority:
   r=j['record'];key=(j['source_id'],encode(j['start']),r['end'],r['is_last']);di,de=dispatch[j['job_id']]
   for q in private.get(key,[]):
    qr=q['record'];pi,pe=admission[q['job_id']];assert q['start']==j['start']
    pairs.append(dict(cell_id=cell['cell_id'],stage=cell['stage'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],source_id=j['source_id'],start=r['start'],end=r['end'],authority_job=j['job_id'],private_job=q['job_id'],complete_start_state_equal=True,complete_end_state_equal=j['end']==q['end'],both_native_model_evaluated=r['native_model_evaluated'] and qr['native_model_evaluated'],private_nonempty_text=bool(qr['text'].strip()),
     controller_received_before_authority_dispatch=pi<di,private_admission_eligible=pe['eligible'],worker_model_end_before_authority_model_start=qr['model_end']<=r['model_start'],worker_return_before_authority_model_start=q['returned']<=r['model_start'],authority_total_model_seconds=r['model_seconds'],private_total_model_seconds=qr['model_seconds'],authority_dispatch=de['dispatched'],private_model_end=qr['model_end'],private_worker_return=q['returned'],authority_model_start=r['model_start']))
  active=[x for x in pairs if x['both_native_model_evaluated']];ready=[x for x in active if x['controller_received_before_authority_dispatch']]
  cells.append(dict(cell_id=cell['cell_id'],stage=cell['stage'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],authority_completions=len(authority),authority_model_evaluated=sum(j['record']['native_model_evaluated'] for j in authority),same_input_pairs=len(pairs),model_evaluated_same_input_pairs=len(active),complete_end_equal_pairs=sum(x['complete_end_state_equal'] for x in active),controller_ready_pairs=len(ready),unique_authority_jobs_with_ready_private=len({x['authority_job'] for x in ready}),ready_private_rejected_by_conservative_admission=sum(not x['private_admission_eligible'] for x in ready),actual_native_jobs_sha256=sha(out/'native_jobs.jsonl'),actual_events_sha256=sha(out/'events.jsonl')));allpairs.extend(pairs)
 evaluated=[x for x in allpairs if x['both_native_model_evaluated']];ready=[x for x in evaluated if x['controller_received_before_authority_dispatch']];unique={(x['cell_id'],x['authority_job']) for x in ready}
 summary=dict(status='PASS_ACTUAL_COMPLETE_INPUT_READY_OPPORTUNITIES_RECOUNTED',native_execution_source=plan['source_commit'],analysis_source=commit,cells=cells,total_pairs=len(allpairs),model_evaluated_pairs=len(evaluated),controller_ready_pairs=len(ready),unique_authority_jobs_with_controller_ready_private=len(unique),full_end_state_equal_among_model_pairs=sum(x['complete_end_state_equal'] for x in evaluated),timings=[dict(stage=k[0],arm=k[1],role=k[2],seconds=stats(v)) for k,v in sorted(timing.items())],matched_same_input_total_timings=dict(authority_seconds=stats([x['authority_total_model_seconds'] for x in evaluated]),private_seconds=stats([x['private_total_model_seconds'] for x in evaluated])),pairs=allpairs,
  limitations=['Complete top-k beam tokens/ASR-stage mutable packet is not recorded; these are observed readiness opportunities, not valid handoff admissions.','Model seconds are full original infer calls; Authority minus Private is not exact C (different GPU/path/tail).','Private-admission returned uses loop-now and is not a fresh receipt timestamp; primary readiness uses journal ordering.','No new GPU/model work, no filtering of sources, choices, raw service data or original gates.'])
 (a.out/'SUMMARY.json').write_text(json.dumps(summary,indent=2));(a.out/'GATE.json').write_text(json.dumps(dict(status=summary['status']),indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['pairs','cells','timings']},indent=2))
if __name__=='__main__':main()
