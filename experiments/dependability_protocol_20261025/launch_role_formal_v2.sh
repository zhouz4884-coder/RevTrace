set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/role_probe_v2';O=B/'results/revtrace/dependability_20261025/role_probe_v2'
g=json.loads((O/'PILOT_INDEPENDENT_GATE.json').read_text());assert g['decision']=='GO_BOUNDED_ROLE_PROBE' and g['permits64formal']
for rel,digest in g['required_remote_sha256'].items():assert hashlib.sha256((O/rel).read_bytes()).hexdigest()==digest
for name in ['PILOT_LAUNCH.json','PILOT_ASSET_LAUNCH.json']:
 d=json.loads((O/name).read_text());q=Path('/proc')/str(d['pid'])
 assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert not (O/'formal').exists() and not (O/'FORMAL_LAUNCH.json').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_role_probe_controller_v2.py'),'--stage','formal']
with (O/'formal_controller.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],expected=64,
 harness_commit=g['harness_commit'],core_runtime='408d75624104e7e11af3f0f2832263c632b10ed8',
 controller_sha256=hashlib.sha256((P/'run_role_probe_controller_v2.py').read_bytes()).hexdigest(),
 gate_sha256=hashlib.sha256((O/'PILOT_INDEPENDENT_GATE.json').read_bytes()).hexdigest(),scope=g['scope'])
 (O/'FORMAL_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
