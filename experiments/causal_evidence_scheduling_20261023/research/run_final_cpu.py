"""Wait for existing audit pipeline, then close bounded evidence. No GPU jobs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/ces_20261023'
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
done=[]
try:
 while not (O/'POST_SUMMARY.json').exists():
  if (O/'POST_STOP.json').exists() or (O/'FORMAL_STOP.json').exists():raise RuntimeError('existing prerequisite stopped; do not rerun GPU')
  time.sleep(15)
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
 for stage,script in [('diagnosis','diagnose_formal_v2.py'),('identity','audit_matrix_identity_v2.py'),('pack','pack_bounded_evidence.py'),('index','index_closed_evidence_v2.py')]:
  save(O/'FINAL_CPU_PROGRESS.json',{'status':'RUNNING_CPU_ONLY','stage':stage,'completed':done})
  with (O/('FINAL_CPU_'+stage+'.log')).open('w') as f:r=subprocess.run([sys.executable,'-u',str(P/script),str(B)],cwd=P,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise RuntimeError('final independent evidence stage failed, no overwrite:'+stage)
  done.append(stage);print('COMPLETE_FINAL_CPU_STAGE',stage,flush=True)
 save(O/'FINAL_CPU_SUMMARY.json',{'status':'ALL_BOUNDED_EVIDENCE_AND_RAW_RELEASE_CHECKS_COMPLETE','completed':done,
   'new_GPU_calls':0,'still_requires_local_recompute_report_and_GitHub_delivery':True,
   'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
except BaseException as e:save(O/'FINAL_CPU_STOP.json',{'error':repr(e),'completed':done,'new_GPU_calls':0});raise
