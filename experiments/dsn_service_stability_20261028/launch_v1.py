"""Parent-authorized serial GPU launch after source/plan/resource validation."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_dsn_service_stability_20261028';N=B/'projects/revtrace_physical_retirement_20261028';S=N/'source_v3';O=B/'results/revtrace/physical_retirement_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=P/'PLAN_v1_FROZEN.json';expected='bd06a99155b2f962b0ba9e832424ee84c9ce7d98cff79fad2091c756792fe39f'
assert sha(plan)==expected and sha(N/'SOURCE_v3.json')=='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'
sys.path.insert(0,str(S));from retirement_service import verify_source
source=verify_source(N/'SOURCE_v3.json');assert source['code_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
assert json.loads((O/'confirmation_controller_v3/GATE.json').read_text())['gate']=='PASS_ALL_FROZEN_EXECUTION_CELLS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
py=str(B/'envs/revbatch-cu128/bin/python');out=O/'dsn_service_stability_controller_v1'
argv=[py,'-B','-u',str(S/'retirement_campaign.py'),'--plan',str(plan),'--plan-sha256',expected,'--source-manifest',str(N/'SOURCE_v3.json'),'--out',str(out)]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',HF_HOME=str(B/'cache/huggingface'),XDG_CACHE_HOME=str(B/'cache'),TMPDIR=str(B/'tmp/physical_retirement_20261028'))
logpath=O/'dsn_service_stability_controller_v1.log';handle=P/'GPU_HANDLE_v1.json'
assert not out.exists() and not logpath.exists() and not handle.exists()
with logpath.open('x') as log:child=subprocess.Popen(argv,cwd=S,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
proc=Path('/proc',str(child.pid));h=dict(experiment_id=json.loads(plan.read_text())['experiment_id'],pid=child.pid,start_ticks=(proc/'stat').read_text().rsplit(')',1)[1].split()[19],command_sha256=sha(proc/'cmdline'),argv=argv,launched_unix=time.time(),result=str(out),log=str(logpath),planned_cells=36,resource_note='No concurrent model downloads, decompression, other GPU or heavy remote CPU work during timed cells')
with handle.open('x') as f:json.dump(h,f,indent=2);f.write('\n')
print(json.dumps(h))
