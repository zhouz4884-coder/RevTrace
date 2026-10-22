"""Nine matched static-scope scouts; never synthesize dynamic neural outputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
B=Path(sys.argv[1]);P=B/'projects/revtrace_elastic_20261022';S=P/'fixed_sdk';O=B/'results/revtrace/elastic_20261022';F=O/'fixed_scout';F.mkdir(exist_ok=True)
CODE=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit'];mf=B/'datasets/revtrace/phaseD_20261021/manifest.json'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
matrix=[]
for i,arrival in enumerate(['sync','staggered','low-high-low']):
 for rho in ([1,2,3][i:]+[1,2,3][:i]):matrix.append({'arrival':arrival,'rho':rho,'repeat':0})
assert not (O/'FIXED_SCOUT_SUMMARY.json').exists() and not list(F.glob('*/result.json'))
weights=[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((B/'models/Qwen3-ASR-1.7B').glob('*.safetensors'))]
old=json.loads((B/'results/revtrace/phaseD_20261021/State-continuity_PREFLIGHT.json').read_text())['model_assets'];assert {r['file']:r['sha256'] for r in weights}=={r['file']:r['sha256'] for r in old}
manifest=json.loads(mf.read_text());assert len(manifest['sessions'])==16 and len({r['speaker'] for r in manifest['sessions']})==16
(O/'FIXED_SCOUT_FREEZE.json').write_text(json.dumps({'matrix':matrix,'code_commit':CODE,'manifest_sha256':sha(mf),'weights_verified_before_GPU':weights,'same_16_full_sources':True,'source_sha256':sha(Path(__file__)),'main_SLO':[2,8],'quality_delta_pp':[.5,.5],'scout_not_formal_statistical_claim':True},indent=2)+'\n')
done=[]
try:
 for r in matrix:
  assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
  name=f"rho{r['rho']}-{r['arrival']}-r0";out=F/name;assert not out.exists()
  cmd=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(mf),'--output',str(out),'--code-commit',CODE,'--study-id','ELASTIC-STATIC-SPACE-SCOUT','--mode','coarse','--authority-rho',str(r['rho']),'--sessions','16','--arrival',r['arrival'],'--arrival-stagger-step','2','--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--trusted-text-binding','--consumer-policy','two_lane','--retain-verified-private-prefix','--phase-n-instrumentation','--capture-model-inputs','--durable-journal-path',str(F/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
  (F/(name+'.COMMAND.json')).write_text(json.dumps({'command':cmd,'frozen_unix':time.time(),'code_commit':CODE},indent=2)+'\n')
  with (F/(name+'.log')).open('w') as f:q=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT)
  if q.returncode:raise RuntimeError('Cell failure: '+name)
  done.append(name);(O/'FIXED_SCOUT_PROGRESS.json').write_text(json.dumps({'completed':done,'expected':9}));print(name,flush=True)
 (O/'FIXED_SCOUT_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE_9_STATIC_SCOUTS','completed':done},indent=2)+'\n')
except BaseException as e:(O/'STOP_FIXED.json').write_text(json.dumps({'error':repr(e),'completed':done}));raise
