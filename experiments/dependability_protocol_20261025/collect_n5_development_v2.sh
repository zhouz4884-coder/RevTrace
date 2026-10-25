set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v2';O=B/'results/revtrace/dependability_20261025/n5_v2'
s=json.loads((O/'development/SUMMARY.json').read_text());assert s['cells']==s['expected']==12 and len(set(s['completed']))==12
assert not (O/'development/STOP.json').exists()
d=json.loads((O/'DEVELOPMENT_LAUNCH.json').read_text());q=Path('/proc')/str(d['pid'])
assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
handles=[]
for name in s['completed']:
 C=O/'development'/name/'attempt0';r=json.loads((C/'result.json').read_text());assert r['fine_window_accounting_complete']
 for h in json.loads((C/'OWNED_WORKER_HANDLES.json').read_text()):
  q=Path('/proc')/str(h['pid']);assert not (q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']))
  handles.append(dict(h,verified_exited=True))
release=O/'DEVELOPMENT_RELEASE.json';assert not release.exists()
release.write_text(json.dumps(dict(status='PASS12_RUN_COMPLETENESS_24_OWNED_WORKERS_EXITED_PENDING_AUDIT',workers=handles,
 current_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)),indent=2)+'\n')
files=[dict(path=p.relative_to(O).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in (O/'development').rglob('*') if p.is_file()]
index=O/'DEVELOPMENT_RAW_INDEX_v1.json';assert not index.exists();index.write_text(json.dumps(dict(files=files),indent=2)+'\n')
out=O/'development_evidence_v1.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 t.add(O/'development',arcname='development')
 for name in ['DEVELOPMENT_RELEASE.json','DEVELOPMENT_RAW_INDEX_v1.json','DEVELOPMENT_LAUNCH.json']:t.add(O/name,arcname=name)
 for name in ['DEVELOPMENT_MANIFEST.json','CPU_N5_LINUX_v1.xml']:t.add(P/name,arcname=name)
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),files=len(files))))
PY
