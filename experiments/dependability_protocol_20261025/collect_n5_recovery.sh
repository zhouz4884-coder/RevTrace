set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
s=json.loads((O/'recovery_development/SUMMARY.json').read_text());assert s['cells']==s['expected']==2 and not (O/'recovery_development/STOP.json').exists()
d=json.loads((O/'RECOVERY_DEVELOPMENT_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
items=[]
for p in (O/'recovery_development').rglob('*'):
 if p.is_file():items.append(dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
index=O/'RECOVERY_RAW_INDEX_v1.json';assert not index.exists();index.write_text(json.dumps(dict(files=items),indent=2)+'\n')
out=O/'recovery_development_evidence_v1.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 t.add(O/'recovery_development',arcname='recovery_development')
 for name in ['RECOVERY_RAW_INDEX_v1.json','RECOVERY_DEVELOPMENT_LAUNCH.json']:t.add(O/name,arcname=name)
 for name in ['DEVELOPMENT_MANIFEST.json','CPU_N5_V3_LINUX_v1.xml','CPU_SUPERVISOR_V2_LINUX.xml']:t.add(P/name,arcname=name)
 failed=O.parent/'n5_v3/recovery_development';t.add(failed,arcname='failed_supervisor_v1')
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),files=len(items))))
PY
