"""Launch only in the root-allocated idle interval after native asset IO ends."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_physical_retirement_20261028';S=P/'source_v3';O=B/'results/revtrace/physical_retirement_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=P/'DSN_JOINT_PLAN_v1_FROZEN.json';digest='d5da167c84b185dc38c2f5db345b7ba9bd0b501b087fcb06216e8f449a7a7f8e'
assert sha(plan)==digest and sha(P/'SOURCE_v3.json')=='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
sys.path.insert(0,str(S));from retirement_service import verify_source
source=verify_source(P/'SOURCE_v3.json');assert source['code_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
assert json.loads((O/'dsn_service_stability_controller_v1/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
py=str(B/'envs/revbatch-cu128/bin/python');out=O/'dsn_joint_controller_v1'
argv=[py,'-B','-u',str(S/'retirement_campaign.py'),'--plan',str(plan),'--plan-sha256',digest,'--source-manifest',str(P/'SOURCE_v3.json'),'--out',str(out)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',HF_HOME=str(B/'cache/huggingface'),XDG_CACHE_HOME=str(B/'cache'),TMPDIR=str(B/'tmp/physical_retirement_20261028'))
logpath=O/'dsn_joint_controller_v1.log';handle=P/'DSN_JOINT_GPU_HANDLE_v1.json'
assert not out.exists() and not logpath.exists() and not handle.exists()
with logpath.open('x') as f:child=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id=json.loads(plan.read_text())['experiment_id'],pid=child.pid,start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),argv=argv,launched_unix=time.time(),result=str(out),log=str(logpath),planned_cells=24,resource_note='Root must finish native acquisition/environment heavy IO before executing this launch')
with handle.open('x') as f:json.dump(h,f,indent=2);f.write('\n')
print(json.dumps(h))
