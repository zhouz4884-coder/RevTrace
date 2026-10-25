set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/role_probe_v2';O=B/'results/revtrace/dependability_20261025/role_probe_v2'
N=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
assert json.loads((N/'postfault_cpu_v2/SUMMARY.json').read_text())['status']=='PASS21_FORMAL_RECOVERY_WAL_PRIMARY_AND_ACTUAL_ASSETS'
assert json.loads((P/'LINUX_CPU_GATE.json').read_text())['status']=='PASS_SOURCE_AND_CPU_ONLY'
for name in ['FORMAL_FAULT_LAUNCH.json','POSTFAULT_CPU_V2_LAUNCH.json']:
 d=json.loads((N/name).read_text());p=Path('/proc')/str(d['pid'])
 assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks']),'upstream task still live'
gate=json.loads((O/'UPSTREAM_N5_INDEPENDENT_GATE.json').read_text());assert gate['decision']=='GO_BOUNDED_ROLE_PILOT_ONLY'
assert gate['harness_commit']=='b08fa4262d1c3ab7e07137eea340d0bb92be200c'
assert gate['measurement_repair_only'] and not gate['permits64formal']
for rel,digest in gate['required_upstream_sha256'].items():
 p=N/rel;p.resolve().relative_to(N.resolve());assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
assert not (O/'pilot').exists() and not (O/'PILOT_LAUNCH.json').exists()
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=[str(B/'envs/revbatch-cu128/bin/python'),'-u',str(P/'run_role_probe_controller_v2.py'),'--stage','pilot']
with (O/'pilot_controller.log').open('xb') as f:
 p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);q=Path('/proc')/str(p.pid)
 d=dict(pid=p.pid,start_ticks=q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],expected=8,
  harness_commit='b08fa4262d1c3ab7e07137eea340d0bb92be200c',core_runtime='408d75624104e7e11af3f0f2832263c632b10ed8',
  controller_sha256=hashlib.sha256((P/'run_role_probe_controller_v2.py').read_bytes()).hexdigest(),scope='same8input measurement repair, prepared operator no online SLO claim')
 (O/'PILOT_LAUNCH.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
PY
