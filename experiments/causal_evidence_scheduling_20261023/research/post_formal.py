"""Wait on the existing formal matrix, then CPU-only independent analysis."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/ces_20261023';S=P/'runtime_v4'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
done=[]
try:
 while not (O/'FORMAL_EXECUTION_SUMMARY.json').exists():
  if (O/'FORMAL_STOP.json').exists():raise RuntimeError('formal stopped; no duplicate launch or silent repair')
  time.sleep(15)
 assert read(O/'FORMAL_EXECUTION_SUMMARY.json')['status']=='ALL180_GPU_CELLS_EXECUTED_PENDING_AUDIT'
 stages=[('safety_metrics',[str(P/'audit_ces_final.py'),str(B),'formal_v1','180',str(S)]),
  ('processed_inputs',[str(P/'replay_ces_inputs.py'),str(B),'formal_v1']),
  ('consumer_clock',[str(P/'consumer_commit_addendum.py'),str(B)]),
  ('paired_statistics',[str(P/'summarize_formal.py'),str(B)])]
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 for name,args in stages:
  save(O/'POST_PROGRESS.json',{'status':'RUNNING_CPU_ONLY','stage':name,'completed':done})
  with (O/('POST_'+name+'.log')).open('w') as f:r=subprocess.run([sys.executable,'-u',*args],cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError('independent stage failed, no overwrite:'+name)
  done.append(name);print('COMPLETE_CPU_STAGE',name,flush=True)
 save(O/'POST_SUMMARY.json',{'status':'ALL_FORMAL_CPU_AUDITS_AND_STATISTICS_COMPLETE','completed':done,'new_GPU_calls':0,
   'still_requires_final_recomputation_index_and_GitHub_delivery':True,'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
except BaseException as e:save(O/'POST_STOP.json',{'error':repr(e),'completed':done,'new_GPU_calls':0});raise
