import hashlib,json,subprocess,sys,time,importlib.metadata,platform,os
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';O=B/'results/revtrace/phaseD_20261021';S=P/'final_tools_v4'
while not (O/'D_CONTROLLER_SUMMARY.json').exists():
 if (O/'D_CONTROLLER_STOP.json').exists():raise RuntimeError('Earlier study failure: no new GPU work')
 time.sleep(10)
assert json.loads((O/'D_CONTROLLER_SUMMARY.json').read_text())['status']=='COMPLETE_R2_R3_R4'
def idle():assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
idle();ident=[]
for name in ['whisper-small.en','Qwen3-ASR-1.7B']:
 for file in sorted((B/'models'/name).glob('*.safetensors')):
  with file.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  ident.append({'model':name,'file':file.name,'bytes':file.stat().st_size,'sha256':h,'ctime':file.stat().st_ctime})
(O/'FINAL_STUDIES_MODEL_INTEGRITY.json').write_text(json.dumps({'checked_unix':time.time(),'files':ident},indent=2))
for script,phase in [(P/'continuity_v6/scripts/continuity_controller.py','State-continuity'),(S/'whisper_f2.py','R5'),(S/'r6_realization.py','R6'),(P/'gpu_display_recovery_v6.py','D-Recovery')]:
 idle()
 model_name='whisper-small.en' if phase=='R5' else 'Qwen3-ASR-1.7B';assets=[]
 for file in sorted((B/'models'/model_name).glob('*.safetensors')):
  with file.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  expected=next(r for r in ident if r['model']==model_name and r['file']==file.name);assert h==expected['sha256']
  assets.append({'file':file.name,'sha256':h,'bytes':file.stat().st_size})
 (O/(phase+'_PREFLIGHT.json')).write_text(json.dumps({'phase':phase,'time_unix':time.time(),'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'hostname':platform.node(),'python':sys.version,'software':{k:importlib.metadata.version(k) for k in ['torch','transformers','qwen-asr','tokenizers','numpy']},'model_assets':assets,'hardware':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True).splitlines(),'environment':{k:os.environ.get(k) for k in ['CUDA_VISIBLE_DEVICES','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','HF_HOME','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']}},indent=2)+'\n')
 with (O/(phase+'_controller.log')).open('w') as log:r=subprocess.run([sys.executable,'-u',str(script),str(B)],stdout=log,stderr=subprocess.STDOUT,cwd=S)
 if r.returncode:
  (O/'FINAL_STUDIES_STOP.json').write_text(json.dumps({'phase':phase,'status':r.returncode}));raise RuntimeError(phase+' failed; preserve raw')
idle();(O/'FINAL_STUDIES_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_R5_R6_AND_D_RECOVERY','gpu_workers_released':True}))
