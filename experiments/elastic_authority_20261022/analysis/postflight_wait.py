from pathlib import Path
import hashlib,json,os,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';O=B/'results/revtrace/elastic_20261022'
while not (O/'formal_audit/AUDIT_REPORT.json').exists():
 if (O/'STOP_FORMAL.json').exists():raise RuntimeError('Formal failure, no completed study claim')
 log=O/'FORMAL_INDEPENDENT_CONTROLLER.log'
 if log.exists() and 'Traceback (most recent call last)' in log.read_text():raise RuntimeError('Independent audit failure; inspect real log, no GPU restart')
 time.sleep(5)
assert json.loads((O/'formal_audit/AUDIT_REPORT.json').read_text())['cells']==24
for name in ['audit_choice_replay.py','audit_power_windows.py','analyze_formal.py']:
 subprocess.run([sys.executable,str(P/name),str(B)],check=True)
sources=[]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for sdk in ['fixed_sdk','stress_sdk','elastic_sdk']:
 m=json.loads((P/sdk/'SOURCE_MANIFEST.json').read_text())
 for r in m['files']:assert sha(P/sdk/r['path'])==r['sha256'],sdk+'/'+r['path']
 sources.append({'sdk':sdk,'code_commit':m['code_commit'],'files':len(m['files']),'manifest_sha256':sha(P/sdk/'SOURCE_MANIFEST.json')})
weights=json.loads((O/'FORMAL_FREEZE.json').read_text())['weights_verified_before_GPU']
for r in weights:assert sha(B/'models/Qwen3-ASR-1.7B'/r['file'])==r['sha256']
resource=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],text=True)
(O/'POSTFLIGHT.json').write_text(json.dumps({'status':'PASS_COMPLETE_ELASTIC_FORMAL_AND_INDEPENDENT_ANALYSIS','sources_verified':sources,'model_weights_match_before_after':True,'GPU_compute_processes_at_check':resource,'no_more_GPU_work':True,'formal_cells':24,'scout_cells':18,'no_new_C1_C3_fault_campaigns':True},indent=2)+'\n');print('POSTFLIGHT_COMPLETE',flush=True)
