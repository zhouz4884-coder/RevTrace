"""Bounded operator/oracle/online sequence; no automatic formal expansion."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time

B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime'
O=B/'results/revtrace/ces_v5_20261025';PY=sys.executable
def read(p):return json.loads(p.read_text())
def save(p,x):
 tmp=p.with_suffix(p.suffix+'.partial');tmp.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def free_gpu():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def run(cmd,log,cwd=S):
 with log.open('w') as f:r=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 if r.returncode:raise RuntimeError('Stage failed, no silent retry: '+str(log))
def audit(stage,names):
 expected=O/(stage+'_EXPECTED.json');save(expected,{'cells':names})
 out=O/(stage+'_audit')
 cmd=[PY,str(P/'audit_v5.py'),'--root',str(O),'--stage',stage,'--source',str(S),'--output',str(out),
  '--model',str(B/'models/Qwen3-ASR-1.7B'),'--references',str(manifest),'--expected-cells',str(expected)]
 run(cmd,O/(stage+'_audit.log'),P)
 a=read(out/'SUMMARY.json');assert not a['failures'] and a['cells']==len(names),a
 return out

manifest=B/'results/revtrace/row_completion_20261023/validation_source_v1/MANIFEST.json'
cal=P/'CALIBRATION.json';source=read(S/'SOURCE_MANIFEST.json')
oracle=[{'label':'strict','method':'strict','traffic':traffic,'sessions':4,'arrival':'staggered','repeat':0,'oracle':True}
 for traffic in ['clean','mixed']]
methods=[('fine','fine',None),('standard','standard',None),('cost','cost',None),('risk_cost','risk_cost',None),
 ('progress','progress',None),('progress_joint','progress_joint','deadline'),('fine_deadline','fine','deadline'),('standard_deadline','standard','deadline')]
plan=[]
for rep in range(3):
 for ai,arrival in enumerate(['sync','staggered']):
  shift=(rep*3+ai)%len(methods);ordered=methods[shift:]+methods[:shift]
  if rep%2:ordered=list(reversed(ordered))
  for label,method,order in ordered:plan.append({'label':label,'method':method,'order':order,'traffic':'mixed','sessions':16,'arrival':arrival,'repeat':rep,'oracle':False})
assert len(plan)==48

def cell(item,stage):
 assert free_gpu(),'Foreign GPU owner detected; no takeover'
 for row in source['files']:assert sha(S/row['path'])==row['sha256']
 name='-'.join(['validation',item['arrival'],item['traffic'],item['label'],'r'+str(item['repeat'])]);D=O/stage
 D.mkdir(exist_ok=True);(D/'journals').mkdir(exist_ok=True)
 cmd=[PY,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),
  '--manifest',str(manifest),'--output',str(D/name),'--code-commit',source['code_commit'],'--study-id','REVTRACE-CES-V5-GPU-20261025',
  '--sessions',str(item['sessions']),'--arrival',item['arrival'],'--seed',str(20261025+item['repeat']),
  '--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
  '--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs',
  '--ces-method',item['method'],'--ces-traffic',item['traffic'],'--ces-calibration',str(cal),
  '--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),'--online-fallback-layout','selective',
  '--durable-journal-path',str(D/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready','--result-delivery','row']
 if item.get('order'):cmd+=['--ces-proposer-order',item['order']]
 if item['oracle']:cmd+=['--online-oracle-diagnostic']
 save(D/(name+'.COMMAND.json'),{'item':item,'argv':cmd,'source_commit':source['code_commit']})
 run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,D/(name+'.log'))
 result=read(D/name/'result.json');assert result['fine_window_accounting_complete']
 assert free_gpu(),'Owned workers have not released GPU at normal cell exit'
 return name

def main():
 assert not (O/'GPU_STARTED.json').exists(),'Never relaunch an existing controller'
 assert source['code_commit']=='126dc815962e8f726b0cbdf214a19318b28a3629'
 assert sha(cal)=='35aa67579c04018c42f65d8a180c79b60d1941ae53cc87b1177d3ddb49866e55'
 assert free_gpu()
 save(O/'FREEZE.json',{'experiment_id':'REVTRACE-CES-V5-GPU-20261025','runtime_commit':source['code_commit'],
  'runtime_manifest_sha256':sha(S/'SOURCE_MANIFEST.json'),'calibration_sha256':sha(cal),
  'controllers':{n:sha(P/n) for n in ['run_stage.py','operation_probe.py','audit_v5.py','summarize_v5.py']},
  'protocol_sha256':sha(P/'PROTOCOL.md'),'manifest_sha256':sha(manifest),'oracle_plan':oracle,'online_plan':plan,
  'old_sources_reused_for_diagnosis':True,'independent_confirmation':False,'larger_formal_matrix':False,
  'primary_slo_seconds':[2,8],'all_unfinished_frontiers_retained':True})
 save(O/'ENVIRONMENT.json',{'python':sys.version,'packages':subprocess.check_output([PY,'-m','pip','freeze'],text=True),
  'uname':subprocess.check_output(['uname','-a'],text=True),'hardware':subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True),
  'model_sha256':{n:sha(B/'models/Qwen3-ASR-1.7B'/n) for n in ['model-00001-of-00002.safetensors','model-00002-of-00002.safetensors']}})
 save(O/'GPU_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'source_commit':source['code_commit']})
 completed=[];stage='operator'
 try:
  save(O/'PROGRESS.json',{'stage':'operator','status':'RUNNING','completed_online':0,'expected_online':48})
  run([PY,'-u',str(P/'operation_probe.py'),str(B)],O/'operation_probe.log',P)
  assert read(O/'operation_probe_v1/SUMMARY.json')['status']=='PASS_PAID_OPERATOR_REPEAT_AND_D1'
  stage='oracle_v1';names=[]
  for item in oracle:
   name=cell(item,stage);names.append(name);print('ORACLE_COMPLETE',name,flush=True)
  audit(stage,names)
  stage='pilot_v1'
  for item in plan:
   name=cell(item,stage);completed.append(name)
   save(O/'PROGRESS.json',{'stage':stage,'status':'RUNNING','completed_online':len(completed),'expected_online':48,'last':name,'completed':completed})
   print('PILOT_COMPLETE',len(completed),name,flush=True)
  out=audit(stage,completed)
  run([PY,str(P/'summarize_v5.py'),'--audit',str(out),'--output',str(O/'pilot_v1_summary'),'--samples','2000'],O/'pilot_v1_summary.log',P)
  assert free_gpu()
  save(O/'SUMMARY.json',{'status':'COMPLETE_BOUNDED_V5_GPU_PILOT_AND_AUDIT','operator_actions':4,'oracle_cells':2,
   'online_cells':48,'completed_online':completed,'source_commit':source['code_commit'],'GPU_queue_closed':True,
   'larger_formal_matrix':False,'no_automatic_tuning':True})
 except BaseException as e:
  save(O/'STOP.json',{'error':repr(e),'stage':stage,'completed_online':completed,'all_raw_retained':True,'no_silent_retry':True});raise

if __name__=='__main__':main()
