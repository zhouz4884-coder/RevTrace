set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/n5_v2"
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
P=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dependability_20261025/n5_v2')
p=P/'SOURCE_N5_v2.tar.gz';assert hashlib.sha256(p.read_bytes()).hexdigest()=='fc28cb5f9df8b81f6d677b08210c6ffa42cea904093c8370cddb6f8b8e44fb95'
assert not (P/'runtime').exists()
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile();(P/m.name).resolve().relative_to(P.resolve())
 t.extractall(P,filter='data')
m=json.loads((P/'runtime/SOURCE_MANIFEST.json').read_text())
for r in m['files']:assert hashlib.sha256((P/'runtime'/r['path']).read_bytes()).hexdigest()==r['sha256']
print(json.dumps({'commit':m['code_commit'],'files':len(m['files'])}))
PY
cd "$P/runtime"
"$B/envs/revbatch-cu128/bin/python" -m pytest tests/test_certified_envelope.py tests/test_envelope_snapshot.py tests/test_envelope_event_driven.py tests/test_envelope_failure_controls.py tests/test_post_compute_order.py tests/test_live_qwen.py tests/test_lazy_reconciliation.py tests/test_properties_abc.py tests/test_certified_display.py tests/test_continuity_proof.py tests/test_standard_async.py tests/test_durable_journal.py tests/test_consumer_bound_identity.py tests/test_row_lifecycle_transport.py tests/test_dgft.py tests/test_online_coordinator.py tests/test_row_executor_protocol.py tests/test_row_worker_provenance.py tests/test_row_progress_integration.py tests/test_terminal_recovery_contract.py tests/test_localagreement_display.py -q --junitxml=../CPU_N5_V2_LINUX_v1.xml
