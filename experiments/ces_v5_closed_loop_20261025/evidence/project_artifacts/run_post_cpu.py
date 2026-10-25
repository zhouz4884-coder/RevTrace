"""CPU-only after complete formal serving; never starts inference or rewrites raw."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args()
B=a.base;P=B/'projects/revtrace_ces_v5_closed_loop_20261025';O=B/'results/revtrace/ces_v5_closed_loop_20261025'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    assert not p.exists();p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
summary=read(O/'formal_SUMMARY.json');audit=read(O/'formal_audit/SUMMARY.json')
assert summary['performance_cells']==72 and summary['GPU_queue_closed']
assert audit['cells']==72 and not audit['failures']
assert not (O/'POST_CPU_STARTED.json').exists()
save(O/'POST_CPU_STARTED.json',{'pid':os.getpid(),'time_unix':time.time(),'formal_summary_sha256':sha(O/'formal_SUMMARY.json'),
 'new_GPU_calls':0,'scripts':{f:sha(P/f) for f in ['analyze_closed_diagnostics.py','profile_closed_snapshots.py']}})
def run(name,command):
    with (O/(name+'.log')).open('xb') as f:subprocess.run(command,cwd=P,stdout=f,stderr=subprocess.STDOUT,check=True)
try:
    run('formal_independent_diagnostics_v1',[sys.executable,str(P/'analyze_closed_diagnostics.py'),'--root',str(O),'--stage','formal',
        '--plan',str(P/'PLAN.formal.json'),'--output',str(O/'formal_independent_diagnostics_v1')])
    assert read(O/'formal_independent_diagnostics_v1/SUMMARY.json')['status']=='PASS_COMPLETE_OBSERVED_DIAGNOSTICS'
    run('formal_cpu_snapshot_profile_v1',[sys.executable,str(P/'profile_closed_snapshots.py'),'--root',str(O),'--stage','formal',
        '--source',str(P/'runtime'),'--source-manifest',str(P/'runtime/SOURCE_MANIFEST.json'),
        '--plan',str(P/'PLAN.formal.json'),'--output',str(O/'formal_cpu_snapshot_profile_v1')])
    assert read(O/'formal_cpu_snapshot_profile_v1/SUMMARY.json')['status']=='PASS_EXACT_BOUNDED_CPU_REPLAY'
    save(O/'POST_CPU_SUMMARY.json',{'status':'COMPLETE_INDEPENDENT_DIAGNOSTICS_AND_EXACT_CPU_SNAPSHOT_PROFILE',
        'new_GPU_calls':0,'time_unix':time.time(),'raw_rewritten':False,'manuscript_edits':False,
        'diagnostics':read(O/'formal_independent_diagnostics_v1/SUMMARY.json'),
        'CPU_profile':read(O/'formal_cpu_snapshot_profile_v1/SUMMARY.json')})
except BaseException as e:
    save(O/'POST_CPU_STOP.json',{'error':repr(e),'raw_preserved':True,'no_silent_retry':True,'new_GPU_calls':0});raise
