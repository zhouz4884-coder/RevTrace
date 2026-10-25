"""Finalize completed v2 CPU audits of exactly the original six smoke cells."""
from pathlib import Path
import argparse
import json
import time

from smoke_reaudit_gate_v2 import (STATUS, REQUIRED_RAW, read, sha, within,
    expected_smoke, verify_smoke_reaudit)


def save(path, value):
    if path.exists():
        raise FileExistsError('Audit correction never overwrites an existing artifact: '+str(path))
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf8')


def finalize(root, project, *, performance_audit='smoke_audit_v2', oracle_audit='smoke_oracle_audit_v2'):
    root, project = Path(root).resolve(), Path(project).resolve()
    freeze = read(root/'smoke_FREEZE.json')
    performance, oracle = expected_smoke(freeze)
    audit_paths = {'performance': within(root, performance_audit)/'SUMMARY.json',
                   'oracle': within(root, oracle_audit)/'SUMMARY.json'}
    auditor_sha = sha(project/'audit_closed_v2.py')
    for kind, count, names in (('performance', 4, performance), ('oracle', 2, oracle)):
        audit = read(audit_paths[kind])
        assert audit['status'] == 'PASS_FRESH_ROW_SERVING_SAFETY_AND_METRIC_AUDIT'
        assert audit['cells'] == audit['expected_cells'] == count and not audit['failures']
        assert {x['cell'] for x in audit['checks']} == set(names)
        assert audit['script_sha256'] == auditor_sha
    paths = set()
    for stage, names in (('smoke', performance), ('smoke_oracle', oracle)):
        for cell in names:
            directory = root/stage/cell
            for name in REQUIRED_RAW:
                paths.add(directory/name)
            provenance = read(directory/'provenance.json')
            journal = Path(provenance['durable_journal_path']).resolve()
            journal.relative_to(root)
            paths.add(journal)
    index = {'evidence_scope': 'Existing six actual GPU raw histories; no model rerun in this CPU re-audit',
        'files': [{'path': p.relative_to(root).as_posix(), 'bytes': p.stat().st_size,
                   'sha256': sha(p)} for p in sorted(paths)]}
    index_path = root/'SMOKE_V2_REAUDIT_RAW_INDEX.json'
    save(index_path, index)
    summary = {'status': STATUS, 'source_commit': freeze['runtime_commit'],
        **{key: freeze[key] for key in ('runtime_commit', 'runtime_manifest_sha256',
             'calibration_sha256', 'closed_config_sha256')},
        'original_smoke_freeze_sha256': sha(root/'smoke_FREEZE.json'),
        'original_v1_stop_sha256': sha(root/'smoke_STOP.json') if (root/'smoke_STOP.json').is_file() else None,
        'completed_performance_cells': performance, 'completed_oracle_cells': oracle,
        'v2_audit_sha256': auditor_sha, 'v2_helper_sha256': sha(project/'audit_closed_helpers_v2.py'),
        'raw_input_index_relative': index_path.name, 'raw_input_index_sha256': sha(index_path),
        'no_GPU_rerun': True, 'GPU_model_calls_performed_by_reaudit': 0,
        'same_measured_results_not_a_performance_repair': True,
        'correction': 'First successor intentionally uses actual current transition model; later unknown parents do not inherit it',
        'time_unix': time.time()}
    for kind, path in audit_paths.items():
        summary[kind+'_audit_summary_relative'] = path.relative_to(root).as_posix()
        summary[kind+'_audit_summary_sha256'] = sha(path)
    path = root/'smoke_REAUDITED_SUMMARY.json'
    save(path, summary)
    return verify_smoke_reaudit(root, freeze['plan'], project)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--performance-audit', default='smoke_audit_v2')
    parser.add_argument('--oracle-audit', default='smoke_oracle_audit_v2')
    args = parser.parse_args()
    print(json.dumps(finalize(args.root, args.project, performance_audit=args.performance_audit,
        oracle_audit=args.oracle_audit)))


if __name__ == '__main__':
    main()
