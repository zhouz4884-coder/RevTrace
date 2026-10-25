set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025"
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025'
archive=P/'SOURCE_N1_v1.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b76db622300aca674bef4fd4bda95cdf236c6ce227c205de3d1cb13e725b5164'
assert not (P/'runtime').exists()
with tarfile.open(archive) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.issym() and not m.islnk()
  (P/m.name).resolve().relative_to(P.resolve())
 t.extractall(P)
m=json.loads((P/'runtime/SOURCE_MANIFEST.json').read_text())
for r in m['files']:assert hashlib.sha256((P/'runtime'/r['path']).read_bytes()).hexdigest()==r['sha256']
source=B/'datasets/revtrace/phaseD_20261021/manifest.json'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='ad6a8b714d87fdae9d09249f4915e27c59131aca5600629d334d16476d026a9f'
d=json.loads(source.read_text());d['sessions']=d['sessions'][:4]
assert [r['source_id'] for r in d['sessions']]==['3729-6852-0003','4970-29095-0021','1995-1836-0010','4077-13751-0021']
d['N1_selection']='first four metadata ordered PhaseD sources; no outcome selection'
(P/'MANIFEST.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'source_files':len(m['files']),'source_commit':m['code_commit'],'data_sha256':hashlib.sha256((P/'MANIFEST.json').read_bytes()).hexdigest()}))
PY
cd "$P/runtime"
"$B/envs/revbatch-cu128/bin/python" -m pytest tests/test_post_compute_order.py tests/test_live_qwen.py tests/test_lazy_reconciliation.py tests/test_properties_abc.py tests/test_certified_display.py tests/test_continuity_proof.py tests/test_standard_async.py tests/test_durable_journal.py tests/test_consumer_bound_identity.py tests/test_row_lifecycle_transport.py -q --junitxml=../CPU_N1_LINUX_v1.xml
