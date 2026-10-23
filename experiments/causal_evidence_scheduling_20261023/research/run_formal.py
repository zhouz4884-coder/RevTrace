"""Frozen180-cell CES comparison; Mixed3 repeats, clean/high1 descriptive."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime_v4';O=B/'results/revtrace/ces_20261023'
D=O/'formal_v1';assert not D.exists()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(O/'pilot_v4_independent_audit_final/SUMMARY.json')['cells']==6
assert read(O/'CPU_SIGKILL_v4/SUMMARY.json')['status']=='PASS_CES_CPU_SIGKILL_WAL'
assert read(O/'FORMAL_RELEASE.json')['authorized_formal_cells']==180
meta=read(S/'SOURCE_MANIFEST.json')
for r in meta['files']:assert sha(S/r['path'])==r['sha256']
methods=['fine','strict','readiness','ready_any','cost_gate','cost','causal_only','ces','standard']
strata=[(pool,arrival,traffic) for pool in ['development','validation'] for arrival in ['sync','staggered'] for traffic in ['clean','mixed','high']]
plan=[]
for rep in range(3):
 ordered=strata[rep:]+strata[:rep]
 for si,(pool,arrival,traffic) in enumerate(ordered):
  if rep>0 and traffic!='mixed':continue
  shift=(si+rep)%len(methods);order=methods[shift:]+methods[:shift]
  if rep%2:order=list(reversed(order))
  for mode in order:plan.append({'repeat':rep,'pool':pool,'arrival':arrival,'traffic':traffic,'method':mode})
assert len(plan)==180
manifest={'development':B/'datasets/revtrace/phaseD_20261021/manifest.json',
 'validation':B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'}
freeze={'experiment_id':'REVTRACE-CES-FORMAL-v1','code_commit':meta['code_commit'],'controller_sha256':sha(Path(__file__)),
 'plan':plan,'sources':{k:{'path':str(p),'sha256':sha(p)} for k,p in manifest.items()},
 'calibration_sha256':sha(O/'calibration_v5/CALIBRATION.json'),'formal_design_sha256':sha(P/'FORMAL_FREEZE.md'),
 'source_snapshot_sha256':sha(S/'SOURCE_MANIFEST.json'),'primary_slo':[2,8],'same_input_fresh_process':True,
 'all_incomplete_frontiers_remain_in_denominator':True,'no_retuning_after_validation':True}
D.mkdir();(D/'journals').mkdir();save(O/'FORMAL_FREEZE.json',freeze)
completed=[]
try:
 for item in plan:
  since=time.monotonic();announced=False
  while subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip():
   if not announced:save(D/'WAIT_OTHER_GPU_OWNER.json',{'since_unix':time.time(),'next':item,'no_foreign_process_touched':True});announced=True
   if time.monotonic()-since>8*3600:raise TimeoutError('foreign GPU owner persists; no takeover')
   time.sleep(15)
  name='-'.join([item['pool'],item['arrival'],item['traffic'],item['method'],'r'+str(item['repeat'])]);out=D/name
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
   '--manifest',str(manifest[item['pool']]),'--output',str(out),'--code-commit',meta['code_commit'],
   '--study-id','REVTRACE-CES-FORMAL-v1','--sessions','16','--arrival',item['arrival'],'--seed',str(20261023+item['repeat']),
   '--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy','two_lane',
   '--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--ces-method',item['method'],
   '--ces-traffic',item['traffic'],'--ces-calibration',str(O/'calibration_v5/CALIBRATION.json'),
   '--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),
   '--online-fallback-layout','selective','--durable-journal-path',str(D/'journals'/(name+'.wal')),
   '--journal-sync-mode','group_ready','--result-delivery','row']
  save(D/(name+'.COMMAND.json'),{'argv':cmd,'frozen_item':item,'source_commit':meta['code_commit']})
  with (D/(name+'.log')).open('w') as f:r=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  if r.returncode:raise RuntimeError('formal cell failed, not silently omitted or retried: '+name)
  result=read(out/'result.json');assert result['fine_window_accounting_complete']
  completed.append(name);save(O/'FORMAL_PROGRESS.json',{'status':'RUNNING','completed_count':len(completed),'expected':180,'last':name,'completed':completed})
  print('COMPLETE',name,flush=True)
 save(O/'FORMAL_EXECUTION_SUMMARY.json',{'status':'ALL180_GPU_CELLS_EXECUTED_PENDING_AUDIT','completed':completed,
   'source_commit':meta['code_commit'],'formal_analysis_or_GO_not_yet_claimed':True,'GPU_queue_closed':True})
except BaseException as e:
 save(O/'FORMAL_STOP.json',{'error':repr(e),'completed':completed,'planned':180,'unexecuted_not_removed_from_plan':True});raise
