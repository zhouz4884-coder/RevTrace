"""Fixed120 core +30 independent validation; no policy/threshold search."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time

B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
S=P/'source_row_sdk_v2';D=O/'formal_row_v1';V=O/'validation_row_v1'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(O/'row_live_pilot_v1/SUMMARY.json')['status']=='COMPLETE_ALL10_LIVE_PILOTS_INDEPENDENT_AUDIT_PASS'
assert read(O/'row_gpu_crash_v1/SUMMARY.json')['acknowledged_segment_survives']
validation=O/'validation_source_v1/MANIFEST.json';assert read(validation)['status']=='FROZEN_INDEPENDENT_VALIDATION16'
assert not D.exists() and not V.exists()
meta=read(S/'SOURCE_MANIFEST.json')
for r in meta['files']:assert sha(S/r['path'])==r['sha256']
control=read(P/'PHASE_CONTROL_SOURCE_v1.json')
assert control['files']['run_formal_row.py']==sha(Path(__file__))
policies=['fine','dgft','standard','strict','score'];strata=[('sync16','clean'),('sync16','F2'),('cohort8','clean'),('cohort8','F2')]
plan=[]
for rep in range(3):
 ordered=strata[rep:]+strata[:rep]
 for si,(load,traffic) in enumerate(ordered):
  shift=(si+rep)%5;ms=policies[shift:]+policies[:shift]
  if rep%2:ms=list(reversed(ms))
  for mi,method in enumerate(ms):
   modes=['batch','row'] if (mi+si+rep)%2==0 else ['row','batch']
   for delivery in modes:plan.append({'phase':'core','repeat':rep,'load':load,'traffic':traffic,'method':method,'delivery':delivery})
vplan=[]
for rep in range(3):
 for ti,traffic in enumerate(['clean','F2'] if rep%2==0 else ['F2','clean']):
  shift=(rep+ti)%5
  for method in policies[shift:]+policies[:shift]:vplan.append({'phase':'validation','repeat':rep,'load':'sync16','traffic':traffic,'method':method,'delivery':'row'})
assert len(plan)==120 and len(vplan)==30
freeze={'experiment_id':'REVTRACE-ROW-FORMAL-20261023-v1','source_commit':meta['code_commit'],
 'controller_code_commit':control['code_commit'],
 'controller_sha256':sha(Path(__file__)),'core_manifest_sha256':sha(B/'datasets/revtrace/phaseD_20261021/manifest.json'),
 'validation_manifest_sha256':sha(validation),'formal_design_sha256':sha(P/'FORMAL_DESIGN_PRE_OUTCOME.md'),
 'core_plan':plan,'validation_plan':vplan,'sources_per_cohort':16,'unique_quality_sources':32,
 'no_new_independent_scheduling_rule_implemented':True,'generic_executor_and_existing_causal_coordination_only':True,
 'no_retuning_or_Rescue_or_Elastic_DAG_V2_KV':True,'primary_D_C':[2,8],'seed':20261022,
 'all_incomplete_requests_retained':True,'paper_unchanged':True}
D.mkdir();V.mkdir();(D/'journals').mkdir();(V/'journals').mkdir();save(O/'FORMAL_ROW_FREEZE_v1.json',freeze)
completed=[]
try:
 for item in plan+vplan:
  # Waiting is a resource state,not permission to touch another experiment.
  announced=False
  while subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
   if not announced:print('WAIT_OTHER_GPU_OWNER',flush=True);announced=True
   time.sleep(15)
  target=D if item['phase']=='core' else V
  manifest=B/'datasets/revtrace/phaseD_20261021/manifest.json' if item['phase']=='core' else validation
  name=f"{item['method']}-{item['delivery']}-{item['load']}-{item['traffic']}-r{item['repeat']}";out=target/name
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
   '--manifest',str(manifest),'--output',str(out),'--code-commit',meta['code_commit'],'--study-id','REVTRACE-ROW-FORMAL-20261023-v1',
   '--sessions','16','--arrival','sync' if item['load']=='sync16' else 'staggered','--seed',str(20261023+item['repeat']),
   '--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy','two_lane',
   '--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--online-study-method',item['method'],
   '--online-traffic',item['traffic'],'--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),
   '--online-fallback-layout','selective','--durable-journal-path',str(target/'journals'/(name+'.wal')),
   '--journal-sync-mode','group_ready','--result-delivery',item['delivery']]
  if item['load']=='cohort8':cmd+=['--online-arrival-cohort','8']
  save(target/(name+'.COMMAND.json'),{'argv':cmd,'frozen_item':item,'source_code_commit':meta['code_commit']})
  with (target/(name+'.log')).open('w') as log:q=subprocess.run(['/usr/bin/time','-v','-o',str(target/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  if q.returncode:raise RuntimeError('formal cell failed, no silent retry: '+name)
  result=read(out/'result.json');assert result['fine_window_accounting_complete']
  completed.append({'phase':item['phase'],'cell':name});save(O/'FORMAL_ROW_PROGRESS_v1.json',{'status':'RUNNING','completed':completed,'expected':150,'last':completed[-1]})
  print(item['phase']+' '+name,flush=True)
 for stage,count in [('formal_row_v1',120),('validation_row_v1',30)]:
  with (O/(stage+'_AUDIT_v2.log')).open('w') as log:q=subprocess.run([sys.executable,str(P/'audit_row_cells_v2.py'),str(B),stage,str(count),str(S)],cwd=S,stdout=log,stderr=subprocess.STDOUT)
  assert q.returncode==0,'formal independent audit failure: '+stage
 save(O/'FORMAL_ROW_SUMMARY_v1.json',{'status':'COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS','completed':completed,
  'core':120,'independent_validation':30,'source_code_commit':meta['code_commit'],'no_more_GPU_auto_issuance':True,
  'not_an_independent_new_algorithm_claim':True})
except BaseException as e:
 save(O/'STOP_FORMAL_ROW_v1.json',{'error':repr(e),'completed':completed,'unexecuted_plan_not_silently_dropped':True});raise
