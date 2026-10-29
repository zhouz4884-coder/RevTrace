"""Launch frozen offline recount only after all24 execution cells and GPU drain."""
import datetime,hashlib,json,os,subprocess
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_physical_retirement_20261028'
O=B/'results/revtrace/physical_retirement_20261028'
gate=json.loads((O/'dsn_joint_controller_v1/GATE.json').read_text())
assert gate['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
plan=P/'DSN_JOINT_PLAN_v1_FROZEN.json'
assert hashlib.sha256(plan.read_bytes()).hexdigest()=='d5da167c84b185dc38c2f5db345b7ba9bd0b501b087fcb06216e8f449a7a7f8e'
manifest=P/'DSN_JOINT_ANALYSIS_SOURCE_v1.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='b7f31431d15c30534c342aca5bbae6315bd4e58ac0e8ac1d9069c63ee0c92c8a'
source=P/'dsn_joint_analysis_source_v1'
out=O/'dsn_joint_analysis_v1';handle=P/'DSN_JOINT_ANALYSIS_HANDLE_v1.json'
log=O/'dsn_joint_analysis_v1.log'
assert not out.exists() and not handle.exists() and not log.exists()
argv=[str(B/'envs/revbatch-cu128/bin/python'),'-B','-u',str(source/'joint_recount.py'),'--source-manifest',str(manifest),'--plan',str(plan),'--out',str(out)]
with log.open('x') as f:
    child=subprocess.Popen(argv,cwd=source,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''),stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid))
h=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1-OFFLINE-RECOUNT',pid=child.pid,
       start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
       command_sha256=hashlib.sha256(proc.joinpath('cmdline').read_bytes()).hexdigest(),argv=argv,
       started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),output=str(out),log=str(log),
       resource_rule='No native timed GPU until this CPU IO recount finishes')
with handle.open('x') as f:json.dump(h,f,indent=2);f.write('\n')
print(json.dumps(h))
