set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
for name in ['FORMAL_NORMAL_LAUNCH.json','POSTNORMAL_CPU_LAUNCH.json']:
 d=json.loads((O/name).read_text());q=Path('/proc')/str(d['pid'])
 assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']),'previous controller still live'
assert json.loads((O/'formal_normal/SUMMARY.json').read_text())['cells']==105
assert json.loads((O/'postnormal_cpu_v1/SUMMARY.json').read_text())['status']=='PASS105_PRIMARY_WAL_ASSETS_AND_RECOVERY_ASSETS'
gate=json.loads((O/'RECOVERY_DEVELOPMENT_INDEPENDENT_GATE.json').read_text())
assert gate['decision']=='GO_SAFETY_ONLY' and gate['runtime_commit']=='408d75624104e7e11af3f0f2832263c632b10ed8'
for rel,want in gate['required_file_sha256'].items():
 p=O/rel;p.resolve().relative_to(O.resolve());assert hashlib.sha256(p.read_bytes()).hexdigest()==want
assert not (O/'FORMAL_FAULT_LAUNCH.json').exists() and not (O/'formal_fault').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
assert hashlib.sha256((P/'run_n5_validation_v2.py').read_bytes()).hexdigest()=='11fdc2526249c1c828d5f34a1c7fafbd0d33288bf93667dc9f703393f6ffa436'
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_n5_validation_v2.py'),'--stage','formal_fault']
with (O/'formal_fault_controller.log').open('xb') as f:
 child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(child.pid)
 d=dict(pid=child.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],expected=21,
  source_commit='408d75624104e7e11af3f0f2832263c632b10ed8',gate_sha256=hashlib.sha256((O/'RECOVERY_DEVELOPMENT_INDEPENDENT_GATE.json').read_bytes()).hexdigest())
 (O/'FORMAL_FAULT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
