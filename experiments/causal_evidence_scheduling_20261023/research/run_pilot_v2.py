"""Bounded true-GPU CES feasibility, no automatic formal phase."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;S=P/'runtime_v2';O=B/'results/revtrace/ces_20261023'
D=O/'pilot_v2';assert not D.exists();D.mkdir();(D/'journals').mkdir()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=read(S/'SOURCE_MANIFEST.json')
for x in m['files']:assert sha(S/x['path'])==x['sha256']
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'foreign GPU owner; no takeover'
env={'python':sys.version,'packages':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),
 'hardware':subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True),
 'model_weights':{n:sha(B/'models/Qwen3-ASR-1.7B'/n) for n in ['model-00001-of-00002.safetensors','model-00002-of-00002.safetensors']}}
save(D/'ENVIRONMENT.json',env)
plan=[{'name':'oracle-ces-mixed','method':'ces','traffic':'mixed','sessions':16,'oracle':True}]
for mode in ['standard','ces','causal_only','cost','readiness','strict','fine']:
 plan.append({'name':mode+'-mixed','method':mode,'traffic':'mixed','sessions':16,'oracle':False})
plan.append({'name':'ces-mixed-repeat','method':'ces','traffic':'mixed','sessions':16,'oracle':False})
save(D/'PLAN.json',{'source_commit':m['code_commit'],'plan':plan,'config_frozen_before_execution':True,
 'source_manifest':str(S/'SOURCE_MANIFEST.json'),'calibration_sha256':sha(O/'calibration_v3/CALIBRATION.json'),
 'not_formal_or_independent_validation':True,'timeout_each_seconds':900})
done=[]
try:
 for item in plan:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
  name=item['name'];cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),
   '--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(B/'datasets/revtrace/phaseD_20261021/manifest.json'),
   '--output',str(D/name),'--code-commit',m['code_commit'],'--study-id','REVTRACE-CES-PILOT-v2',
   '--sessions',str(item['sessions']),'--arrival','sync','--seed','20261023',
   '--trusted-text-binding','--display-protocol','canonical-snapshot-v1','--publish-canonical-display',
   '--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs',
   '--ces-method',item['method'],'--ces-traffic',item['traffic'],'--ces-calibration',str(O/'calibration_v3/CALIBRATION.json'),
   '--online-donors',str(B/'projects/revtrace_online_admission_20261022/DONORS.json'),'--online-fallback-layout','selective',
   '--durable-journal-path',str(D/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready','--result-delivery','row']
  if item['oracle']:cmd+=['--online-oracle-diagnostic']
  save(D/(name+'.COMMAND.json'),{'argv':cmd,'item':item})
  with (D/(name+'.log')).open('w') as f:r=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.CPU_IO.txt'))]+cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  if r.returncode:raise RuntimeError('PILOT_FAILED_NO_FORMAL:'+name)
  result=read(D/name/'result.json');assert result['fine_window_accounting_complete']
  done.append(name);save(D/'PROGRESS.json',{'status':'RUNNING','completed':done,'expected':len(plan)})
  print('COMPLETE',name,flush=True)
 save(D/'SUMMARY.json',{'status':'ALL9_GPU_PILOTS_EXECUTED_PENDING_INDEPENDENT_AUDIT','completed':done,'source_commit':m['code_commit'],'formal_launched':False})
except BaseException as e:
 save(D/'STOP.json',{'error':repr(e),'completed':done,'no_silent_retry':True});raise
