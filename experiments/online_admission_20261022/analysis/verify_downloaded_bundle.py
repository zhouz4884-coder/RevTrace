"""Verify the terminal pack before local extraction; no scientific judgement."""
from pathlib import Path
import json
from archive_integrity import sha256, safe_extract, verify_manifest

W = Path(__file__).resolve().parent
summary = json.loads((W / 'REMOTE_PACK_SUMMARY.json').read_text())
archive = W / 'BOUNDED_EVIDENCE.tar.gz'; destination = W / 'collected_evidence_v1'
assert summary['status'] == 'COMPLETE_BOUNDED_MEASURED_EVIDENCE_PACKAGE'
assert archive.stat().st_size == summary['archive_bytes'] and sha256(archive) == summary['archive_sha256']
extract = safe_extract(archive, destination)
result = verify_manifest(destination)
assert result['manifest_sha256'] == summary['manifest_sha256']
(W / 'LOCAL_EXTRACT_AUDIT.json').write_text(json.dumps({**result, 'extraction': extract,
    'archive_sha256': sha256(archive), 'not_final_goal_completion': True}, indent=2) + '\n')
print(json.dumps(result))
