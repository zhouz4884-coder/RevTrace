"""Execute the previously frozen eligible D plan; never tune from confirmation."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
assert not (O/'D_SEQUENCE_STARTED.json').exists();save(O/'D_SEQUENCE_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'stages':['D_development','D_heldout'],'no_auto_retuning':True})
try:
 for stage in ['D_development','D_heldout']:
  with (O/(stage+'_CONTROLLER.log')).open('xb') as f:subprocess.run([sys.executable,'-u',str(P/'run_matrix.py'),'--base',str(B),'--stage',stage,'--plan',str(P/('PLAN_'+stage+'.json'))],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
  assert json.loads((O/(stage+'_SUMMARY.json')).read_text())['GPU_queue_closed']
  with (O/(stage+'_POST.log')).open('xb') as f:
   for script,extra in [('summarize_v6.py',[]),('audit_anchor_policy_v2.py',['--source',str(P/'runtime_D')])]:
    subprocess.run([sys.executable,str(P/script),'--root',str(O),'--stage',stage,*extra],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
 save(O/'D_SEQUENCE_SUMMARY.json',{'status':'COMPLETE_D_GPU_METRICS_AND_POLICY_AUDITS','GPU_queue_closed':True,'time_unix':time.time(),'no_more_experiments_automatically_launched':True})
except BaseException as e:
 save(O/'D_SEQUENCE_STOP.json',{'error':repr(e),'raw_preserved':True,'no_silent_retry':True});raise
