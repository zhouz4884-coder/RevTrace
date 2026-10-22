"""All formal/neural-control raw records, no outcome filtering or model/audio."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

B = Path(sys.argv[1]); O = B / 'results/revtrace/online_admission_20261022'; D = O / 'raw_export_v1'
assert json.loads((O / 'CLOSURE_SUMMARY.json').read_text())['status'] == 'COMPLETE_CPU_NEURAL_CHAIN_AND_REMOTE_EVIDENCE_CLOSURE'
D.mkdir(exist_ok=False)
index = json.loads((O / 'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())
roots = {'formal_v1', 'formal_oracles_v1', 'trace_oracle_v2', 'selective_protocol_v1', 'batch16_protocol_v1'}
selected = [r for r in index['files'] if Path(r['path']).parts[0] in roots]


def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


try:
    assert len(json.loads((O / 'FORMAL_SUMMARY.json').read_text())['completed']) == 72
    for r in selected:
        p = O / r['path']; assert p.is_file() and not p.is_symlink() and p.stat().st_size == r['bytes'] and sha(p) == r['sha256']
    metadata = {'files': selected, 'scope': sorted(roots), 'all_formal_cells': 72,
                'model_weights_audio_and_credentials_not_in_scope': True,
                'not_outcome_selected': True, 'all_raw_inputs_unchanged_since_independent_audit': True}
    (D / 'MANIFEST.json').write_text(json.dumps(metadata, indent=2) + '\n')
    archive = D / 'FORMAL_AND_ORACLE_RAW.tar.gz'
    with tarfile.open(archive, 'w:gz', compresslevel=6) as f:
        f.add(D / 'MANIFEST.json', arcname='MANIFEST.json', recursive=False)
        for r in selected: f.add(O / r['path'], arcname='raw/' + r['path'], recursive=False)
    result = {'status': 'COMPLETE_FULL_FORMAL_AND_ORACLE_RAW_EXPORT', 'files': len(selected),
              'raw_bytes': sum(r['bytes'] for r in selected), 'archive_bytes': archive.stat().st_size,
              'archive_sha256': sha(archive), 'manifest_sha256': sha(D / 'MANIFEST.json'),
              'bounded_publication_size_pass': archive.stat().st_size <= 45_000_000,
              'if_size_fails_keep_on_8TB_do_not_silently_drop_cases': True}
    (D / 'SUMMARY.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
except BaseException as e:
    (D / 'STOP.json').write_text(json.dumps({'error': repr(e), 'original_raw_preserved': True}) + '\n')
    raise
