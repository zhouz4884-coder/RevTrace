set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/role_probe_v1';P=B/'projects/revtrace_dependability_20261025/role_probe_v1'
done=json.loads((O/'pilot/SUMMARY.json').read_text());assert done['cells']==done['expected']==len(set(done['completed']))==8
assert not (O/'pilot/STOP.json').exists();d=json.loads((O/'PILOT_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
owned=[]
for name in done['completed']:
 E=O/'pilot'/name;assert (E/'RUN_COMPLETE_PENDING_AUDIT.json').exists()
 for h in json.loads((E/'OWNED_WORKERS.json').read_text()):
  q=Path('/proc')/str(h['pid'])
  assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']))
  owned.append(dict(h,exited=True))
release=O/'PILOT_RELEASE.json';assert not release.exists();release.write_text(json.dumps(dict(owned=owned,GPU_empty=True,cases=8),indent=2)+'\n')
files=[p for p in (O/'pilot').rglob('*') if p.is_file()]
idx=O/'PILOT_RAW_INDEX_v1.json';assert not idx.exists();idx.write_text(json.dumps(dict(files=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),indent=2)+'\n')
out=O/'pilot_evidence_v1.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 t.add(O/'pilot',arcname='pilot')
 for name in ['PILOT_LAUNCH.json','UPSTREAM_N5_INDEPENDENT_GATE.json','PILOT_RELEASE.json','PILOT_RAW_INDEX_v1.json']:t.add(O/name,arcname=name)
 for name in ['LINUX_CPU_GATE.json','CPU_LINUX_v1.xml']:t.add(P/name,arcname=name)
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),raw_files=len(files))))
PY
