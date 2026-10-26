set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/role_probe_v2';P=B/'projects/revtrace_dependability_20261025/role_probe_v2'
done=json.loads((O/'formal/SUMMARY.json').read_text());assert done['cells']==done['expected']==len(set(done['completed']))==64
assert not (O/'formal/STOP.json').exists();d=json.loads((O/'FORMAL_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
owned=[]
for name in done['completed']:
 E=O/'formal'/name;assert (E/'RUN_COMPLETE_PENDING_AUDIT.json').exists()
 for h in json.loads((E/'OWNED_WORKERS.json').read_text()):
  q=Path('/proc')/str(h['pid'])
  assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']))
  owned.append(dict(h,exited=True))
assert len(owned)==128
release=O/'FORMAL_RELEASE.json';assert not release.exists();release.write_text(json.dumps(dict(owned=owned,GPU_empty=True,cases=64),indent=2)+'\n')
files=sorted(p for p in (O/'formal').rglob('*') if p.is_file())
idx=O/'FORMAL_RAW_INDEX_v1.json';assert not idx.exists();idx.write_text(json.dumps(dict(files=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]),indent=2)+'\n')
out=O/'formal_evidence_v2.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 t.add(O/'formal',arcname='formal')
 for name in ['FORMAL_LAUNCH.json','UPSTREAM_N5_INDEPENDENT_GATE.json','PILOT_INDEPENDENT_GATE.json','FORMAL_RELEASE.json','FORMAL_RAW_INDEX_v1.json']:t.add(O/name,arcname=name)
 for name in ['LINUX_CPU_GATE.json','CPU_LINUX_v1.xml']:t.add(P/name,arcname=name)
assert out.stat().st_size<80_000_000
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),raw_files=len(files),raw_bytes=sum(p.stat().st_size for p in files))))
PY
