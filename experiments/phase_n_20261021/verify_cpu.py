"""Portable no-GPU verification of published bounded files and curated regressions."""
import hashlib,json,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'MANIFEST.json').read_text())
for r in manifest['files']:assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'],r['path']
runtime=ROOT/'runtime';code=json.loads((runtime/'SOURCE_MANIFEST.json').read_text())
for r in code['files']:assert hashlib.sha256((runtime/r['path']).read_bytes()).hexdigest()==r['sha256']
archive=ROOT/'PHASE_N_BOUNDED_AUDIT_EVIDENCE.tar.gz'
with tarfile.open(archive) as f:
    member=f.getmember('BOUNDED_DELIVERY_MANIFEST.json');entries=json.load(f.extractfile(member))['files']
    for r in entries:assert hashlib.sha256(f.extractfile(r['path']).read()).hexdigest()==r['sha256']
tests=['test_live_qwen.py','test_lazy_reconciliation.py','test_result_delivery_hold.py','test_execution_context_fault_seam.py',
    'test_properties_abc.py','test_sequence_certificate.py','test_model_lifecycle_telemetry.py','test_diagnostic_switch.py']
print('All release/runtime/bounded-data hashes verified; running CPU ONLY',flush=True)
raise SystemExit(subprocess.run([sys.executable,'-B','-m','pytest',*[str(runtime/'tests'/n) for n in tests],
    '-c',str(runtime/'pytest.ini'),'-q','-p','no:cacheprovider']).returncode)
