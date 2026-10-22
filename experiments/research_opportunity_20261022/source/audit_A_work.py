"""Independent bounded examples and actual old reexecution budget, not projected gain."""
from pathlib import Path
import csv,hashlib,json,sys
from collections import defaultdict
B=Path(sys.argv[1]);O=B/'results/revtrace/opportunity_20261022';D=B/'results/revtrace/phaseD_20261021'
rows=list(csv.DictReader((O/'A_OPPORTUNITIES.csv').open()));groups=defaultdict(list)
for r in rows:groups[r['stage'],r['cell']].append(r)
unique=set();batches=set();replays=0;examples=[];descendant_jobs=set();calls=[]
for (stage,cell),cases in groups.items():
 c=D/stage/cell;es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];rs={}
 for l in (c/'worker_records.jsonl').open():
  x=json.loads(l);rs[x['job']['job_id']]=x
 for case in cases:
  sid=int(case['session_id']);v=int(case['version']);F=int(case['F']);window=int(case['root_window']);checki=next(i for i,e in enumerate(es) if e['kind']=='private-continuity-proof' and e['session_id']==sid and e['canonical_version']==v)
  cm=next(e for e in es if e['kind']=='commit' and e['session_id']==sid and e['version']==v);r=next(rs[e['job_id']] for e in reversed(es[:checki]) if e['kind']=='display' and e['session_id']==sid and e['audio_end_sample']==F)
  old,new=r['result']['state_tokens'],cm['next_prompt_tokens'];source=case['source_id'];unique.add((source,F,tuple(old),tuple(new)))
  if len(examples)<8:examples.append({'stage':stage,'cell':cell,'session_id':sid,'version':v,'F':F,'old_P':old,'new_P':new,'root_input_equivalent':False,'recorded_private_job_id':r['job']['job_id'],'existing_descendant_depth':int(case['actual_existing_descendants']),'evidence':'real frozen records; negative pair, no model regeneration'})
  displays=[e for e in es[:checki] if e['kind']=='display' and e['session_id']==sid and window<rs[e['job_id']]['job']['end_window']<=int(next(e for e in es[checki:] if e['kind']=='private-continuity-proof')['branch_chunk'])]
  for e in displays:
   node=rs[e['job_id']];j,z=node['job'],node['result']
   if j.get('branch_generation')!=r['job'].get('branch_generation'):continue
   key=(stage,cell,j['job_id']);descendant_jobs.add(key)
   a,b=z.get('model_started_perf'),z.get('model_completed_perf')
   if a is not None and b is not None:batches.add((stage,cell,a,b))
  for e in es[checki+1:]:
   if e['kind']=='enqueue' and e['role']=='proposal' and e['session_id']==sid and any(e['audio_start_sample']==rs[d['job_id']]['job']['audio_start_sample'] and e['audio_end_sample']==rs[d['job_id']]['job']['audio_end_sample'] for d in displays):replays+=1
out={'status':'COMPLETE_ACTUAL_WORK_BUDGET','mismatch_observations':len(rows),'unique_source_frontier_oldP_newP_pairs':len(unique),'distinct_completed_descendant_jobs':len(descendant_jobs),'distinct_shared_GPU_batches_containing_those_descendants':len(batches),'deduplicated_GPU_model_interval_seconds':sum(b-a for st,c,a,b in batches),'observed_later_same_interval_reexecutions':replays,'extra_proven_legal_reusable_roots':0,'saved_GPU_work_supported_by_actual_trace':0,'saved_critical_path_seconds_supported_by_actual_trace':0,'upper_bound_warning':'existing descendant batch seconds are already executed, not automatically reexecuted; cannot subtract them from end-to-end time','examples':examples,'no_GPU_calls':True}
(O/'A_WORK_BUDGET.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='examples'}))
