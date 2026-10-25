set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2')
s=json.loads((O/'postnormal_cpu_v1/SUMMARY.json').read_text());assert s['status']=='PASS105_PRIMARY_WAL_ASSETS_AND_RECOVERY_ASSETS'
d=json.loads((O/'POSTNORMAL_CPU_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
selected=[p for p in (O/'postnormal_cpu_v1').rglob('*') if p.is_file()]
for folder in ['normal_aggregation_v1','normal_budgets_v1']:
 if (O/folder).exists():selected.extend(p for p in (O/folder).rglob('*') if p.is_file())
selected.extend(O/p for p in ['formal_normal/FREEZE.json','formal_normal/SUMMARY.json','FORMAL_NORMAL_LAUNCH.json',
 'POSTNORMAL_CPU_LAUNCH.json','INDEPENDENT_MANIFEST_v1.json','DEVELOPMENT_MANIFEST.json'])
index=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in selected]
idx=O/'CPU_BOUNDED_INDEX_v1.json';assert not idx.exists();idx.write_text(json.dumps(dict(files=index),indent=2)+'\n')
out=O/'postnormal_cpu_bounded_v1.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 for p in selected:t.add(p,arcname=p.relative_to(O).as_posix())
 t.add(idx,arcname=idx.name)
assert out.stat().st_size<80_000_000
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bounded_files=len(index),raw_full_GPU_logs_stay_on8TB=True)))
PY
