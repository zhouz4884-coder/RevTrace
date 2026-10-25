set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2')
assert json.loads((O/'postfault_cpu_v2/SUMMARY.json').read_text())['status']=='PASS21_FORMAL_RECOVERY_WAL_PRIMARY_AND_ACTUAL_ASSETS'
d=json.loads((O/'POSTFAULT_CPU_V2_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
files=[p for folder in ['postfault_cpu_v1','postfault_cpu_v2'] for p in (O/folder).rglob('*') if p.is_file()]
if (O/'fault_aggregation_v1').exists():files.extend(p for p in (O/'fault_aggregation_v1').rglob('*') if p.is_file())
files.extend(O/name for name in ['formal_fault/FREEZE.json','formal_fault/SUMMARY.json','FORMAL_FAULT_LAUNCH.json',
 'POSTFAULT_CPU_LAUNCH.json','POSTFAULT_CPU_V2_LAUNCH.json','INDEPENDENT_MANIFEST_v1.json','RECOVERY_DEVELOPMENT_INDEPENDENT_GATE.json'])
index=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
idx=O/'FAULT_CPU_BOUNDED_INDEX_v1.json';assert not idx.exists();idx.write_text(json.dumps(dict(files=index),indent=2)+'\n')
out=O/'postfault_cpu_bounded_v1.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 for p in files:t.add(p,arcname=p.relative_to(O).as_posix())
 t.add(idx,arcname=idx.name)
assert out.stat().st_size<80_000_000
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bounded_files=len(index),full_raw_stays8TB=True)))
PY
