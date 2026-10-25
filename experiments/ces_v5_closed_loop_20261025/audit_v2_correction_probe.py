"""Preserve the audit-only correction as bounded CPU raw trace evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback

from test_audit_closed_v2 import owner_with_released_backlog, run_audit, released_contexts
import audit_closed_helpers as old
import audit_closed_helpers_v2 as new


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    args.output.mkdir(parents=True, exist_ok=False)
    before = {name: sha(root/name) for name in ('audit_closed.py', 'audit_closed_helpers.py')}
    cases = []
    for mode in ('service_cost', 'reserved_progress', 'inherit', 'causal'):
        trace = owner_with_released_backlog(mode)
        cfg, events, records, sessions, initial, _, result = trace
        packed = json.dumps({'evidence_type': 'CPU_actual_owner_with_explicit_fake_model_only',
            'config': cfg, 'events': events, 'worker_records': records,
            'sessions': sessions, 'initial_states': initial, 'result': result},
            sort_keys=True, allow_nan=False).encode()
        artifact = args.output/(mode+'_CPU_TRACE.json.gz')
        artifact.write_bytes(gzip.compress(packed, mtime=0))
        old_failure = None
        try:
            run_audit(old, trace)
        except AssertionError:
            old_failure = traceback.format_exc()
        assert old_failure is not None, 'Original audit did not exercise the claimed first-successor rejection'
        started = time.perf_counter()
        corrected = run_audit(new, trace)
        contexts = released_contexts(trace)
        cases.append({'mode': mode, 'original_audit_status': 'EXPECTED_FALSE_REJECTION_REPRODUCED',
            'original_traceback': old_failure, 'corrected_audit': corrected,
            'corrected_CPU_audit_seconds': time.perf_counter()-started,
            'observations_with_released_children': len(contexts),
            'observations_with_two_released_layers': sum(len(c['target_context']['successors']) == 2 for c in contexts),
            'CPU_TRACE_path': artifact.name, 'CPU_TRACE_sha256': sha(artifact),
            'GPU_model_calls': 0, 'no_neural_or_serving_performance_claim': True})
    assert before == {name: sha(root/name) for name in before}, 'Original frozen audit was modified'
    report = {'experiment_id': 'REVTRACE-CLOSED-AUDIT-V2-CPU-CORRECTION-20261025',
        'evidence_type': 'CPU_actual_owner_interleaving_fixture_not_GPU',
        'runtime_commit': subprocess.check_output(['git', '-C', str(root/'runtime'), 'rev-parse', 'HEAD'], text=True).strip(),
        'frozen_original_audit_hashes': before,
        'new_audit_hashes': {name: sha(root/name) for name in ('audit_closed_v2.py', 'audit_closed_helpers_v2.py')},
        'fixture_source_hashes': {name: sha(root/name) for name in ('test_audit_closed_v2.py', 'test_controller_audit.py')},
        'scope': 'Only the first-successor audit expectation/import changed; runtime and GPU histories are unchanged',
        'cases': cases, 'decision': 'PASS_AUDIT_CORRECTION_REGRESSION_NOT_A_GPU_PERFORMANCE_RESULT'}
    (args.output/'SUMMARY.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print(json.dumps({'decision': report['decision'], 'cases': len(cases),
        'summary': str(args.output/'SUMMARY.json'), 'GPU_model_calls': 0}))


if __name__ == '__main__':
    main()
