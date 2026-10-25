import hashlib,json,subprocess,sys,time
from pathlib import Path
B=Path(sys.argv[1]);S=Path(__file__).resolve().parents[1];O=B/'results/revtrace/phaseD_20261021';CODE=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit'];done=[]
def cell(stage,name,mode,keep,view,n=16,arrival='sync',independent=False,standard=False,barrier='decoupled',legacy=False):
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip();root=O/stage;root.mkdir(exist_ok=True);out=root/name;assert not out.exists()
 command=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(B/('datasets/revtrace/phaseD_20261021/manifest.json' if independent else 'datasets/tc_live_20260906/manifest.json')),'--output',str(out),'--code-commit',CODE,'--study-id','PHASE-D-EXACT-STATE-CONTINUITY','--mode',mode,'--sessions',str(n),'--arrival',arrival,'--proposal-barrier','decoupled','--proposal-reconciliation','lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--trusted-text-binding','--consumer-policy',view,'--phase-n-instrumentation','--capture-model-inputs','--durable-journal-path',str(root/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
 if keep:command+=['--retain-verified-private-prefix']
 command[command.index('--proposal-barrier')+1]=barrier
 if standard:command+=['--async-implementation','standard']
 if legacy:command[command.index('--proposal-reconciliation')+1]='legacy'
 (root/(name+'.COMMAND.json')).write_text(json.dumps({'code_commit':CODE,'command':command,'frozen_before_start':time.time()},indent=2))
 with (root/(name+'.log')).open('w') as f:r=subprocess.run(['/usr/bin/time','-v','-o',str(root/(name+'.CPU_IO.txt'))]+command,cwd=S,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(name+' failed; preserve raw')
 done.append(stage+'/'+name);(O/'CONTINUITY_PROGRESS.json').write_text(json.dumps(done));print(name,flush=True)
try:
 matrix=[(r,m,k,p) for r in range(3) for m in ['fine_certified','coarse'] for k in [False,True] for p in ['snapshot','two_lane']]
 (O/'CONTINUITY_DESIGN_FREEZE.json').write_text(json.dumps({'expected_development_cells':24,'expected_strong_async_cells':6,'expected_transfer_cells':6,'expected_strict_capacity_and_corrected_baselines':54,'matrix':matrix,'source_commit':CODE,'origin':'CPU replay showed Fine hides displays, while75/77 rollback boundaries match selected P but prior rebases break ancestry; test prevention rather than splice. Existing retention flag credited, strict chain proof added. Standard safe async receives the SAME retention and consumer rules. LA v1 defective rolling-character adaptation retained but excluded; replace with full-word confirmation and no blanking. All new methods use synthetic warmup, never test-source warmup. Recheck full matched capacity matrix under one repaired carrier; loads remain selected8/4, no outcome-driven threshold change.','no_KV_reuse':True},indent=2))
 for repeat,mode,keep,policy in matrix:cell('R2_continuity',f'{mode}-keep{int(keep)}-{policy}-r{repeat}',mode,keep,policy)
 for repeat in range(3):
  for mode in ['fine_certified','coarse']:cell('R2_strong_async',f'{mode}-keep1-two_lane-r{repeat}',mode,True,'two_lane',standard=True)
 chosen=json.loads((O/'R4_formal/DESIGN_FREEZE.json').read_text())['selected_by_predeclared_rule']
 for repeat in range(3):
  for arrival,n in chosen.items():cell('R2_transfer',f'coarse-keep1-two_lane-c{n}-{arrival}-r{repeat}','coarse',True,'two_lane',n,arrival,True)
 policies=[('Fine-B','fine_certified',False,'snapshot',False,'segment',False),('Fine-D','fine_certified',False,'snapshot',False,'decoupled',False),('Coarse-B','coarse',False,'snapshot',False,'segment',False),('Coarse-D','coarse',False,'snapshot',False,'decoupled',False),('Two-lane','coarse',False,'two_lane',False,'decoupled',False),('Safe-Async','coarse',True,'two_lane',True,'decoupled',False),('LA2','coarse',True,'localagreement2',False,'decoupled',False),('LA3','coarse',True,'localagreement3',False,'decoupled',False),('Naive-ablation','coarse',False,'snapshot',False,'decoupled',True)]
 for repeat in range(3):
  for arrival,n in chosen.items():
   for name,mode,keep,policy,standard,barrier,legacy in (policies if repeat%2==0 else list(reversed(policies))):cell('R4_strict',f'{name}-c{n}-{arrival}-r{repeat}',mode,keep,policy,n,arrival,True,standard,barrier,legacy)
 (O/'CONTINUITY_SUMMARY.json').write_text(json.dumps({'status':'COMPLETE','completed':done,'expected':90},indent=2))
except BaseException as e:(O/'CONTINUITY_STOP.json').write_text(json.dumps({'error':repr(e),'completed':done}));raise
