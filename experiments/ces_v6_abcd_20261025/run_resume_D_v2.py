"""Resume only CPU post-checks after the preserved directory-enumeration failure."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
def read(p):return json.loads(p.read_text())
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
assert (O/'NEXT_STAGES_STOP.json').exists()
assert read(O/'ABC_SUMMARY.json')['GPU_queue_closed'] and read(O/'B_SORTED_SUMMARY.json')['GPU_queue_closed']
assert not (O/'D_SEQUENCE_STARTED.json').exists() and not (P/'PLAN_D_development.json').exists()
save(O/'RESUME_D_v2_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'reason':'CPU checker enumerated journals; original failure retained','A_B_C_not_repeated':True})
try:
 with (O/'POST_ABC_v2.log').open('xb') as f:
  calls=[['analyze_C_v2.py','--root',str(O)],['summarize_v6.py','--root',str(O),'--stage','C'],['analyze_B.py','--root',str(O)],['audit_anchor_policy_v2.py','--root',str(O),'--stage','A','--source',str(P/'runtime')],['prepare_D_v2.py','--base',str(B)]]
  for script,*extra in calls:subprocess.run([sys.executable,str(P/script),*extra],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (O/'D_SEQUENCE_CONTROLLER.log').open('xb') as f:subprocess.run([sys.executable,'-u',str(P/'run_D_sequence_v2.py'),'--base',str(B)],cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
 save(O/'RESUME_D_v2_SUMMARY.json',{'status':'COMPLETE_REPAIRED_CPU_POST_CHECKS_AND_D','GPU_queue_closed':True,'time_unix':time.time(),'no_further_GPU_launched':True})
except BaseException as e:
 save(O/'RESUME_D_v2_STOP.json',{'error':repr(e),'all_raw_preserved':True,'do_not_duplicate_GPU':True});raise
