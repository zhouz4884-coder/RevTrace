"""Frozen R2 pilots/cost, R4 scout-selected formal matrix; no V2, no paper edits."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
B=Path(sys.argv[1]);S=Path(__file__).resolve().parents[1];O=B/'results/revtrace/phaseD_20261021';CODE=json.loads((S/'SOURCE_MANIFEST.json').read_text())['code_commit'];DONE=[]
def dump(p,v):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(v,indent=2)+'\n')
def idle():assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def cell(stage,name,mode='coarse',n=4,arrival='sync',barrier='decoupled',consumer='snapshot',standard=False,legacy=False,binding=True,manifest=None):
 idle();folder=O/stage/name;assert not folder.exists()
 c=[sys.executable,'-u',str(S/'scripts/run_tc_live_qwen.py'),'--model',str(B/'models/Qwen3-ASR-1.7B'),'--manifest',str(manifest or B/'datasets/revtrace/phaseD_20261021/manifest.json'),'--output',str(folder),'--code-commit',CODE,'--study-id','PHASE-D-'+stage,'--mode',mode,'--sessions',str(n),'--arrival',arrival,'--proposal-barrier',barrier,'--proposal-reconciliation','legacy' if legacy else 'lazy','--display-protocol','canonical-snapshot-v1','--publish-canonical-display','--consumer-policy',consumer,'--async-implementation','standard' if standard else 'revtrace','--phase-n-instrumentation','--capture-model-inputs','--durable-journal-path',str(O/stage/'journals'/(name+'.wal')),'--journal-sync-mode','group_ready']
 if binding:c+=['--trusted-text-binding']
 dump(O/stage/(name+'.COMMAND.json'),{'code_commit':CODE,'command':c,'frozen_before_start_unix':time.time()})
 with (O/stage/(name+'.log')).open('w') as log:p=subprocess.run(c,cwd=S,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('Cell failure retained: '+str(folder))
 DONE.append(str(folder));dump(O/'D_CONTROLLER_PROGRESS.json',{'completed':DONE,'last':name});print('COMPLETE',stage,name,flush=True)
 return folder
def q99(xs):
 if not xs or any(x is None for x in xs):return None
 xs=sorted(xs);i=(len(xs)-1)*.99;j=int(i);return xs[j]+(xs[min(j+1,len(xs)-1)]-xs[j])*(i-j)
def observed(cell):
 sess=json.loads((cell/'sessions.json').read_text());res=json.loads((cell/'result.json').read_text());ev=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()];views=[json.loads(x) for x in (cell/'consumer.jsonl').read_text().splitlines()]
 ds=[];cs=[]
 for s in sess:
  total=round(s['duration']*16000);qs=list(range(32000,total,32000))+[total]
  for q in qs:
   release=s['offset']+q/16000;ts=[v['observed'] for v in views if v['session_id']==s['session_id'] and v['valid_visible_frontier']>=q];tc=[e['installed'] for e in ev if e['kind']=='commit' and e['session_id']==s['session_id'] and e['audio_end_sample']>=q]
   ds.append(min(ts)-release if ts else None);cs.append(min(tc)-release if tc else None)
 return {'display_p99':q99(ds),'commit_p99':q99(cs),'xrt':res['audio_seconds_per_wall_second'],'frontiers':len(ds),'uncapped':res['token_limit_events']==0}
try:
 assert json.loads((O/'R1_gpu/SUMMARY.json').read_text())['status']=='COMPLETE'
 # Data was selected before outcomes by independent source/speaker hash ordering.
 idle();subprocess.run([sys.executable,str(B/'projects/revtrace_phaseD_20261021/prepare_sources.py'),str(B)],check=True)
 for bound in [False,True]:cell('R2_pilot','textbound'+str(int(bound)),n=2,binding=bound)
 for repeat in range(3):
  for bound in ([False,True] if repeat%2==0 else [True,False]):cell('R2_cost',f'bind{int(bound)}-r{repeat}',binding=bound)
 dump(O/'R2_pilot/SUMMARY.json',{'status':'COMPLETE','text_binding_scout_pass':True})
 scouts=[]
 for arrival in ['sync','staggered']:
  for n in [2,4,8,12,16]:
   p=cell('R4_scout',f'c{n}-{arrival}',n=n,arrival=arrival);m=observed(p);scouts.append(dict(n=n,arrival=arrival,**m))
 dump(O/'R4_scout/SCOUT_METRICS.json',scouts)
 chosen={}
 for arrival in ['sync','staggered']:
  valid=[r['n'] for r in scouts if r['arrival']==arrival and r['display_p99'] is not None and r['commit_p99'] is not None and r['display_p99']<=2 and r['commit_p99']<=8 and r['uncapped']]
  chosen[arrival]=max(valid) if valid else 2
 policies=[('Fine-B','fine_certified','segment','snapshot',False,False),('Fine-D','fine_certified','decoupled','snapshot',False,False),('Coarse-B','coarse','segment','snapshot',False,False),('Coarse-D','coarse','decoupled','snapshot',False,False),('Two-lane','coarse','decoupled','two_lane',False,False),('Safe-Async','coarse','decoupled','two_lane',True,False),('LA2','coarse','decoupled','localagreement2',False,False),('LA3','coarse','decoupled','localagreement3',False,False),('Naive-ablation','coarse','decoupled','snapshot',False,True)]
 dump(O/'R4_formal/DESIGN_FREEZE.json',{'selected_by_predeclared_rule':chosen,'policies':policies,'repeats':3,'expected':54,'no_threshold_changes':True,'selection_time':time.time(),'main_slo':[2,8],'grid_display':[2,5,8],'grid_commit':[4,8,12,16]})
 for repeat in range(3):
  for arrival,n in chosen.items():
   for name,mode,barrier,policy,standard,legacy in (policies if repeat%2==0 else list(reversed(policies))):cell('R4_formal',f'{name}-c{n}-{arrival}-r{repeat}',mode=mode,n=n,arrival=arrival,barrier=barrier,consumer=policy,standard=standard,legacy=legacy)
 dump(O/'R4_formal/SUMMARY.json',{'status':'COMPLETE','expected':54,'chosen':chosen,'completed':[p for p in DONE if '/R4_formal/' in p]})
 dump(O/'D_CONTROLLER_SUMMARY.json',{'status':'COMPLETE_R2_R3_R4','completed':DONE})
except BaseException as exc:
 dump(O/'D_CONTROLLER_STOP.json',{'error':repr(exc),'completed':DONE});raise
