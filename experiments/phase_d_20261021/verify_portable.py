"""Hashes plus standalone CPU invariants; no server access, no GPU startup."""
from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).resolve().parent;manifest=json.loads((W/'MANIFEST.json').read_text())
for row in manifest['files']:
 p=W/row['path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
runtime=W/'runtime'
tests=['test_consumer_bound_identity.py','test_continuity_proof.py','test_localagreement_display.py','test_certified_display.py','test_properties_abc.py','test_live_qwen.py','test_standard_async.py']
print('All published byte hashes match. Running explicitly CPU-only fixtures.',flush=True)
raise SystemExit(subprocess.call([sys.executable,'-B','-m','pytest',*[str(runtime/'tests'/n) for n in tests],'-q','-p','no:cacheprovider'],cwd=runtime))
