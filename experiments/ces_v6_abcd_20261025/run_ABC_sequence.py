"""One GPU owner for bounded pilot -> A -> C. No D launch or tuning."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
assert not (O/'ABC_STARTED.json').exists()
assert json.loads((O/'B_SUMMARY.json').read_text())['GPU_queue_closed']
save(O/'ABC_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'stages':['A_pilot','A','C'],'D_not_automatically_started':True})
plan=json.loads((P/'PLAN_A.json').read_text());pilot=[]
for label in ['fine','anchor_cost']:
 c=next(x for x in plan['cells'] if x['label']==label and x['repeat']==0 and x['arrival']=='staggered').copy()
 c['sessions']=8;pilot.append(c)
pilot_plan=dict(plan,cells=pilot,expected_repeats=1,scope='safety pilot, not superiority')
save(P/'PLAN_A_pilot.json',pilot_plan)
try:
 for stage in ['A_pilot','A','C']:
  cmd=[sys.executable,'-u',str(P/'run_matrix.py'),'--base',str(B),'--stage',stage,'--plan',str(P/('PLAN_'+stage+'.json'))]
  with (O/(stage+'_CONTROLLER.log')).open('xb') as f:subprocess.run(cmd,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
  s=json.loads((O/(stage+'_SUMMARY.json')).read_text());assert s['status']=='COMPLETE_GPU_MATRIX_AND_SAFETY_AUDIT'
 save(O/'ABC_SUMMARY.json',{'status':'COMPLETE_PILOT_A_C_GPU_AND_SAFETY','GPU_queue_closed':True,'D_not_started':True,'time_unix':time.time()})
except BaseException as e:
 save(O/'ABC_STOP.json',{'error':repr(e),'all_raw_retained':True,'no_silent_retry':True});raise
