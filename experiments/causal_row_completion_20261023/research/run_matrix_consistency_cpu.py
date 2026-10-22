"""Serial final plan/config/assets audit. No GPU work or policy changes."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
meta=json.loads((P/'CONSISTENCY_SOURCE_v1.json').read_text())
for n,value in meta['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==value
assert not (O/'MATRIX_CONSISTENCY_CPU_RUN_v1.json').exists()
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
save('MATRIX_CONSISTENCY_CPU_RUN_v1.json',{'status':'WAIT_F2_CPU_SUPPLEMENT','code_commit':meta['code_commit'],'new_model_calls':0})
try:
 while not (O/'F2_EXPOSURE_CPU_SUMMARY_v1.json').exists():
  if (O/'F2_EXPOSURE_CPU_STOP_v1.json').exists():raise RuntimeError('F2 CPU supplement stopped; no bypass')
  time.sleep(15)
 assert json.loads((O/'F2_EXPOSURE_CPU_SUMMARY_v1.json').read_text())['status']=='COMPLETE_ACTUAL_F2_DOSE_AND_LAYOUT_CPU_SUPPLEMENT'
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
 with (O/'MATRIX_CONSISTENCY_CPU_AUDIT_v1.log').open('w') as log:q=subprocess.run([sys.executable,'-B',str(P/'audit_matrix_consistency.py'),str(B)],cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert q.returncode==0,'fixed-plan/config audit failed'
 save('MATRIX_CONSISTENCY_CPU_SUMMARY_v1.json',{'status':'COMPLETE150_FIXED_PLAN_ENV_DATA_SOURCE_AND_BOUNDARY_WEIGHT_AUDIT',
   'code_commit':meta['code_commit'],'new_model_calls':0,'Rescue_not_started':True,'final_decisions_union_index_GitHub_still_required':True})
except BaseException as e:
 save('MATRIX_CONSISTENCY_CPU_STOP_v1.json',{'error':repr(e),'new_model_calls':0,'raw_retained':True});raise
