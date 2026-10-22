"""Freeze bounded audited evidence only after serving and diagnostic completion."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile


def main():
    B = Path(sys.argv[1]); P = B / 'projects/revtrace_online_admission_20261022'
    O = B / 'results/revtrace/online_admission_20261022'; D = O / 'delivery_evidence_v1'
    def read(p): return json.loads(p.read_text())
    def sha(p):
        with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
    def save(path, x): path.write_text(json.dumps(x, indent=2, allow_nan=False) + '\n')
    assert read(O / 'POSTPROCESS_SUMMARY.json')['status'] == 'COMPLETE_FORMAL_ORACLE_AND_CPU_AUDITS'
    assert read(O / 'FORMAL_RESULTS_v1/GONOGO.json')['status'] == 'COMPLETE_PREDECLARED_FORMAL_COMPARISONS'
    assert read(O / 'FAULT_CHAINS_v1/SUMMARY.json')['status'] == 'COMPLETE_ACTUAL_ONLINE_FAULT_CHAIN_RECONSTRUCTION'
    assert read(O / 'NEURAL_FEEDBACK_CHAINS_v1/SUMMARY.json')['status'] == 'COMPLETE_POST_INSTALL_NEURAL_CONSUMPTION_AUDIT'
    assert not (O / 'STOP_FORMAL_v1.json').exists() and not (O / 'STOP_POSTPROCESS_v1.json').exists()
    D.mkdir(exist_ok=False)
    try:
        frozen = read(O / 'FORMAL_FREEZE.json'); S = P / 'pilot_sdk_v3'
        source = read(S / 'SOURCE_MANIFEST.json')
        assert source['code_commit'] == frozen['runtime_code_commit'] == '55cd52dfdbab71298cdb7eae3b0c08c9424020c6'
        code_rows = [{'path': r['path'], 'expected_sha256': r['sha256'], 'actual_sha256': sha(S / r['path'])} for r in source['files']]
        assert all(r['expected_sha256'] == r['actual_sha256'] for r in code_rows)
        weight_rows = [{'file': r['file'], 'expected_sha256': r['sha256'], 'actual_sha256': sha(B / 'models/Qwen3-ASR-1.7B' / r['file'])} for r in frozen['weights']]
        assert all(r['expected_sha256'] == r['actual_sha256'] for r in weight_rows)
        manifest_path = B / 'datasets/revtrace/phaseD_20261021/manifest.json'
        assert sha(manifest_path) == frozen['source_manifest_sha256']
        import numpy as np
        import soundfile as sf
        audio_rows = []
        for r in read(manifest_path)['sessions']:
            wave, rate = sf.read(r['path'], dtype='float32'); assert rate == 16000 and wave.ndim == 1
            observed = hashlib.sha256(np.asarray(wave, dtype='<f4').tobytes()).hexdigest()
            assert observed == r['audio_sha256']
            audio_rows.append({'source_id': r['source_id'], 'actual_PCM_sha256': observed, 'reference': r['reference']})
        save(D / 'FINAL_CODE_MODEL_DATA_IDENTITY.json', {'status': 'PASS_REHASHED_AFTER_MEASUREMENTS',
            'code': code_rows, 'model_weights': weight_rows, 'audio': audio_rows,
            'source_manifest_sha256': sha(manifest_path), 'no_model_weights_or_audio_in_package': True})
        shutil.copyfile(manifest_path, D / 'FORMAL_SOURCE_MANIFEST.json')
        shutil.copyfile(S / 'SOURCE_MANIFEST.json', D / 'RUNTIME_SOURCE_MANIFEST.json')

        # Raw logs, power, neural records and journals remain on8TB. Metadata and
        # independent tables are copied byte-for-byte; no measurements rewritten.
        analysis_dirs = {'formal_v1_audit_v3', 'FORMAL_RESULTS_v1', 'FAULT_CHAINS_v1',
                         'pilot_v2_audit', 'pilot_v3_audit', 'NEURAL_FEEDBACK_CHAINS_v1'}
        live_dirs = {'formal_v1', 'pilot_v1', 'pilot_v2', 'pilot_v3'}
        operator_dirs = {'trace_oracle_v1', 'trace_oracle_v2', 'formal_oracles_v1',
                         'selective_protocol_v1', 'batch16_protocol_v1'}
        metadata_names = {'config.json', 'provenance.json', 'sessions.json', 'workers.json',
                          'result.json', 'initial_states.json', 'failure.json'}
        operator_metadata = {'RUN.json', 'SUMMARY.json', 'STOP.json', 'ENVIRONMENT.json',
                             'ACTUAL_BATCH16_INPUTS.json'}
        raw = []; included = []; total = 0
        for f in sorted(O.rglob('*')):
            if not f.is_file() or f.is_relative_to(D) or '__pycache__' in f.parts: continue
            if f.is_symlink(): raise ValueError('Unreviewed evidence symlink: ' + str(f))
            rel = f.relative_to(O); head = rel.parts[0]
            # This very controller writes its own operational log/progress
            # after the pack returns. Never claim an in-progress log has a
            # final immutable hash. Collect closure metadata separately later.
            if len(rel.parts) == 1 and (f.name.startswith('CLOSURE_') or f.name.startswith('STOP_CLOSURE_')): continue
            keep = len(rel.parts) == 1 and f.suffix in ['.json', '.log', '.txt']
            keep |= head in analysis_dirs
            keep |= head in live_dirs and (f.name in metadata_names or f.name.endswith(('.COMMAND.json', '.CPU_IO.txt', '.log')))
            keep |= head in operator_dirs and (f.name in operator_metadata or f.name.startswith('WORKER-'))
            size = f.stat().st_size; before = f.stat().st_mtime_ns; checksum = sha(f)
            assert before == f.stat().st_mtime_ns and size == f.stat().st_size, 'Evidence still being written'
            assert not keep or size < 20_000_000, 'Bounded evidence file requires explicit review'
            raw.append({'path': rel.as_posix(), 'bytes': size, 'sha256': checksum, 'included_bounded': bool(keep)})
            if keep:
                target = D / 'collected' / rel; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, target); assert sha(target) == checksum
                included.append(rel.as_posix()); total += size
        assert total < 90_000_000, 'Review package too large; no silent truncation'
        save(D / 'RAW_EVIDENCE_INDEX.json', {'remote_result_root': str(O), 'files': raw,
            'raw_file_count': len(raw), 'full_raw_bytes': sum(r['bytes'] for r in raw),
            'current_CLOSURE_operational_logs_excluded_until_terminal': True,
            'raw_neural_logs_audio_power_journals_not_replaced_by_summary': True})
        save(D / 'BOUNDED_SELECTION.json', {'files': included, 'included_bytes': total,
            'selection_rule': 'All formal/pilot configurations/results/provenance and independent tables; operators retain summary/environment; full raw files indexed on8TB',
            'all_failed_campaigns_indexed': True, 'not_anonymous_delivery': True})
        manifest = [{'path': f.relative_to(D).as_posix(), 'bytes': f.stat().st_size, 'sha256': sha(f)}
                    for f in sorted(D.rglob('*')) if f.is_file()]
        save(D / 'MANIFEST.json', {'files': manifest, 'data_sources_not_new_speakers_per_repeat': 16})
        archive = D / 'BOUNDED_EVIDENCE.tar.gz'
        with tarfile.open(archive, 'w:gz') as tf:
            for f in sorted(D.rglob('*')):
                if f.is_file() and f != archive: tf.add(f, arcname=f.relative_to(D).as_posix(), recursive=False)
        assert archive.stat().st_size < 95_000_000
        save(D / 'PACK_SUMMARY.json', {'status': 'COMPLETE_BOUNDED_MEASURED_EVIDENCE_PACKAGE',
            'source_commit': source['code_commit'], 'raw_files_indexed': len(raw),
            'bounded_files': len(manifest), 'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
            'manifest_sha256': sha(D / 'MANIFEST.json'), 'all_original_measurement_bytes_retained': True,
            'not_goal_complete': 'Local independent inspection, contribution decisions and GitHub verification remain'})
        print(json.dumps(read(D / 'PACK_SUMMARY.json')))
    except BaseException as e:
        save(D / 'STOP.json', {'error': repr(e), 'no_raw_measurement_deleted': True})
        raise


if __name__ == '__main__': main()
