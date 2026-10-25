set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v2';O=B/'results/revtrace/dependability_20261025/n5_v2'
cpu=list(P.glob('*.xml'));print('CPU_XML',[(p.name,p.stat().st_size) for p in cpu]);assert len(cpu)==1
out=O/'development_evidence_v2.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as t:
 t.add(O/'development',arcname='development')
 for name in ['DEVELOPMENT_RELEASE.json','DEVELOPMENT_RAW_INDEX_v1.json','DEVELOPMENT_LAUNCH.json']:t.add(O/name,arcname=name)
 t.add(P/'DEVELOPMENT_MANIFEST.json',arcname='DEVELOPMENT_MANIFEST.json')
 t.add(cpu[0],arcname=cpu[0].name)
print(json.dumps(dict(archive=str(out),bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest())))
PY
"$B/envs/revbatch-cu128/bin/python" "$B/projects/revtrace_dependability_20261025/n5_v2/prepare_n5_heldout.py"
