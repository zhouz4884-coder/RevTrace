"""Single scoped continuation: wait corrected B, CPU gates, frozen D, stop."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
assert not (O/'NEXT_STAGES_STARTED.json').exists();save(O/'NEXT_STAGES_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'waiting_for':'B_SORTED_SUMMARY.json','scope':'CPU gates then already designed D; no next tuning loop'})
try:
 while not (O/'B_SORTED_SUMMARY.json').exists():
  if any((O/n).exists() for n in ['ABC_STOP.json','B_sorted_STOP.json','B_sorted_WAIT_STOP.json']):raise RuntimeError('Upstream failed; no D launch')
  time.sleep(5)
 assert json.loads((O/'ABC_SUMMARY.json').read_text())['GPU_queue_closed']
 with (O/'POST_ABC.log').open('xb') as f:
  subprocess.run(['bash',str(P/'post_ABC.sh')],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,str(P/'audit_anchor_policy.py'),'--root',str(O),'--stage','A','--source',str(P/'runtime')],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run([sys.executable,str(P/'prepare_D.py'),'--base',str(B)],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (O/'D_SEQUENCE_CONTROLLER.log').open('xb') as f:subprocess.run([sys.executable,'-u',str(P/'run_D_sequence.py'),'--base',str(B)],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
 save(O/'NEXT_STAGES_SUMMARY.json',{'status':'COMPLETE_ABC_AND_D_STAGES','GPU_queue_closed':True,'time_unix':time.time(),'collection_not_yet_started':True})
except BaseException as e:
 save(O/'NEXT_STAGES_STOP.json',{'error':repr(e),'raw_preserved':True,'do_not_duplicate_GPU':True});raise
