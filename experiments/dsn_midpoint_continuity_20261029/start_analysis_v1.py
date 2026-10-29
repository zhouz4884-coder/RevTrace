"""After all twelve terminal gates, launch the unchanged frozen CPU analysis."""
from pathlib import Path
import shlex,sys
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
program=r'''
from pathlib import Path
import hashlib,json,os,subprocess,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dsn_midpoint_continuity_20261029';O=B/'results/revtrace/physical_retirement_20261028';S=P/'analysis_source_v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
controller=O/'dsn_midpoint_controller_v1';gate=json.loads((controller/'GATE.json').read_text())
assert gate['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS' and gate['completed']==12
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'no analysis IO during timed GPU work'
plan=P/'PLAN_v1_FROZEN.json';M=P/'ANALYSIS_SOURCE_v1.json'
assert sha(plan)=='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84'
assert sha(M)=='bfc3d1a3fe0d819c93e3cda4a4959491efb520ba06cf8b304aec47223a5388c0'
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='fb8a429d95ab682002bc39aedca8bcbec8942b67'
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all'],text=True).strip()
out=O/'dsn_midpoint_analysis_v1';log=O/'dsn_midpoint_analysis_v1.log';handle=P/'CPU_HANDLE_v1.json'
assert not out.exists() and not log.exists() and not handle.exists()
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(S/'midpoint_analysis.py'),'--plan',str(plan),'--plan-sha256',sha(plan),'--source-manifest',str(M),'--output',str(out)]
with log.open('x') as f:p=subprocess.Popen(argv,cwd=S,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(p.pid));h=dict(experiment_id='REVTRACE-DSN-MIDPOINT-CONTINUITY-20261029-V1-CPU-RECOUNT',pid=p.pid,start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),argv=argv,result=str(out),log=str(log),launched_unix=time.time(),code_commit='fb8a429d95ab682002bc39aedca8bcbec8942b67',new_GPU_calls=0)
with handle.open('x') as f:json.dump(h,f,indent=2);f.write('\n')
print(json.dumps(h))
'''
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(B+'/envs/revbatch-cu128/bin/python')+' -B -',timeout=45);i.write(program);i.flush();i.channel.shutdown_write();print(o.read().decode());err=e.read().decode();print(err) if err else None;assert o.channel.recv_exit_status()==0
finally:c.close()
