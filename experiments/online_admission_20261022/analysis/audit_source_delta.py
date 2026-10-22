"""Local byte identity/delta audit against the already-frozen Phase-D runtime."""
from pathlib import Path
import difflib
import hashlib
import json

W = Path(__file__).resolve().parent
base = Path(r'D:\StreamTxn\outputs\revtrace_phaseD_20261021\public_release\runtime')
current = W / 'runtime'
assert base.is_dir()
manifest = json.loads((current / 'SOURCE_MANIFEST.json').read_text())
assert manifest['code_commit'] == '55cd52dfdbab71298cdb7eae3b0c08c9424020c6'
entries = []; patch = []
for item in manifest['files']:
    rel = item['path']; new = (current / rel).read_bytes()
    assert hashlib.sha256(new).hexdigest() == item['sha256'], 'Frozen measured source changed'
    old = (base / rel).read_bytes() if (base / rel).exists() else None
    status = 'unchanged' if old == new else 'added' if old is None else 'changed'
    entries.append({'path': rel, 'status': status, 'old_sha256': hashlib.sha256(old).hexdigest() if old is not None else None,
                    'new_sha256': hashlib.sha256(new).hexdigest(), 'measured_manifest_match': True})
    if status != 'unchanged':
        try:
            patch.extend(difflib.unified_diff((old or b'').decode('utf-8').splitlines(True), new.decode('utf-8').splitlines(True),
                         fromfile='phaseD/' + rel, tofile='measured_online/' + rel))
        except UnicodeDecodeError:
            patch.append('Binary delta: ' + rel + '\n')
out = {'status': 'PASS_ALL_MEASURED_SOURCE_BYTES_AND_BASE_DELTA',
       'base_phaseD_commit': manifest['base_phaseD'], 'measured_commit': manifest['code_commit'],
       'files_verified': len(entries), 'counts': {k: sum(r['status'] == k for r in entries) for k in ['unchanged', 'changed', 'added']},
       'scope': 'Current119-file source subset compared with frozen Phase-D baseline; omitted baseline files are not claimed deleted',
       'entries': entries}
(W / 'SOURCE_DELTA_TO_PHASE_D.json').write_text(json.dumps(out, indent=2) + '\n')
(W / 'SOURCE_DELTA_TO_PHASE_D.patch').write_text(''.join(patch), encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k != 'entries'}))
print('changed_or_added', json.dumps([r['path'] for r in entries if r['status'] != 'unchanged']))
