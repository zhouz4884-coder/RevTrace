"""Last serial CPU exposure audit; cannot allocate CUDA or issue model work."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,time
B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023'
meta=json.loads((P/'F2_ANALYSIS_SOURCE_v1.json').read_text())
for n,sha in meta['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==sha
assert not (O/'F2_EXPOSURE_CPU_RUN_v1.json').exists()
def save(n,x):(O/n).write_text(json.dumps(x,indent=2)+'\n')
save('F2_EXPOSURE_CPU_RUN_v1.json',{'experiment_id':'REVTRACE-ROW-CPU-F2-EXPOSURE-v1','status':'WAIT_EXISTING_EXTRA_CPU',
 'code_commit':meta['code_commit'],'runtime_code_commit':'2bc71af5457de5d065ff9e771d2fad428c5c6ed9',
 'python':sys.version,'platform':platform.platform(),'frozen_cells':150,'new_model_calls':0})
try:
 while not (O/'EXTRA_ROW_CPU_SUMMARY_v1.json').exists():
  if (O/'EXTRA_ROW_CPU_STOP_v1.json').exists():raise RuntimeError('previous CPU supplement stopped; no silent bypass')
  time.sleep(15)
 assert json.loads((O/'EXTRA_ROW_CPU_SUMMARY_v1.json').read_text())['status']=='COMPLETE_EXTRA_OWNER_AND_ACTUAL_PRIVATE_DECISION_AUDITS'
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false',CUDA_VISIBLE_DEVICES='')
 with (O/'F2_EXPOSURE_CPU_AUDIT_v1.log').open('w') as log:q=subprocess.run([sys.executable,'-B',str(P/'audit_f2_exposure.py'),str(B)],cwd=P,env=env,stdout=log,stderr=subprocess.STDOUT)
 assert q.returncode==0,'F2 CPU exposure audit stopped'
 save('F2_EXPOSURE_CPU_SUMMARY_v1.json',{'status':'COMPLETE_ACTUAL_F2_DOSE_AND_LAYOUT_CPU_SUPPLEMENT','code_commit':meta['code_commit'],
   'new_model_calls':0,'CUDA_disabled_for_counterfactual_input_reconstruction':True,'Rescue_not_started':True,'final_decisions_union_raw_index_and_GitHub_still_required':True})
except BaseException as e:
 save('F2_EXPOSURE_CPU_STOP_v1.json',{'error':repr(e),'new_model_calls':0,'raw_preserved':True});raise
