"""Serial, frozen service cells; execution acceptance is not a benefit claim."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from retirement_service import W, DISK, verify_source, value_sha


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, value, *, replace=False):
    path = Path(path)
    data = json.dumps(value, indent=2, allow_nan=False)+'\n'
    if replace:
        tmp = path.with_name(path.name+'.tmp')
        with tmp.open('x', encoding='utf8') as stream:
            stream.write(data)
        os.replace(tmp, path)
    else:
        with path.open('x', encoding='utf8') as stream:
            stream.write(data)


def validate_cells(plan):
    cells = plan['cells']
    if not cells or len({c['cell_id'] for c in cells}) != len(cells):
        raise ValueError('nonempty uniquely named frozen cells required')
    outputs = set()
    for cell in cells:
        name = cell['cell_id']
        if not name or any(x not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for x in name):
            raise ValueError('simple cell ID required')
        argv = cell['argv']
        script = argv.index(str(W/'retirement_service.py'))
        if Path(argv[0]).resolve() != Path(sys.executable).resolve() or script not in (1, 2, 3):
            raise ValueError('each cell must execute the frozen local service controller')
        output = Path(argv[argv.index('--out')+1]).resolve()
        if output in outputs or not output.is_relative_to(DISK/'results/revtrace/physical_retirement_20261028'):
            raise ValueError('distinct scoped output paths required')
        if '--defer-audit' in argv:
            raise ValueError('campaign cannot accept deferred audits')
        outputs.add(output)
        if cell.get('output') is not None and Path(cell['output']).resolve() != output:
            raise ValueError('cell metadata/actual command output mismatch')
    return cells


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--plan-sha256', required=True)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    if sha(a.plan) != a.plan_sha256:
        raise ValueError('frozen plan bytes changed')
    source = verify_source(a.source_manifest)
    plan = read(a.plan)
    if plan['code_commit'] != source['code_commit'] or plan['source_manifest_sha256'] != source['source_manifest_sha256']:
        raise ValueError('frozen campaign refers to a different source')
    cells = validate_cells(plan)
    out = a.out.resolve()
    if not out.is_relative_to(DISK/'results/revtrace/physical_retirement_20261028'):
        raise ValueError('campaign record must remain on experiment disk')
    identity = dict(code_commit=source['code_commit'], source_manifest_sha256=source['source_manifest_sha256'],
                    plan=str(a.plan.resolve()), plan_sha256=a.plan_sha256, cells=len(cells))
    if a.resume:
        prior = read(out/'RUN_RECORD.json')
        if any(prior[k] != v for k, v in identity.items()):
            raise ValueError('resume requires the exact original frozen campaign')
        if (out/'STOP.json').exists():
            raise ValueError('failed campaigns remain preserved; use a fresh frozen plan and output')
    else:
        out.mkdir(parents=True, exist_ok=False)
        put(out/'ENVIRONMENT.json', dict(python=sys.version, executable=sys.executable,
            hostname=platform.node(), platform=platform.platform(),
            process_environment={k:os.environ.get(k) for k in ('HF_HOME','HF_HUB_OFFLINE','TMPDIR','PYTHONPATH')}))
        put(out/'RUN_RECORD.json', dict(identity, experiment_id=plan['experiment_id'],
            frozen_config=str(a.plan.resolve()), frozen_config_sha256=a.plan_sha256,
            environment_record=str(out/'ENVIRONMENT.json'), environment_record_sha256=sha(out/'ENVIRONMENT.json'),
            raw_result_location=[c['output'] for c in cells],
            aggregate_summary_location=str(out/'SUMMARY.json'), gate_decision_location=str(out/'GATE.json')))
    completed = []
    for cell in cells:
        episode = Path(cell['output'])
        try:
            if sha(a.plan) != a.plan_sha256:
                raise ValueError('campaign plan changed between cells')
            if episode.exists():
                if not a.resume:
                    raise FileExistsError('never overwrite an existing episode: '+str(episode))
                record = read(episode/'RUN_RECORD.json')
                if record['code_commit'] != source['code_commit']:
                    raise ValueError('resume encountered another execution source')
                command = read(episode/'COMMAND.json')
                # Service main generates its own internal runner command; its
                # immutable FREEZE still has every externally selected setting.
                if command['code_commit'] != source['code_commit']:
                    raise ValueError('resume command identity changed')
                rc = 0
            else:
                put(out/'PROGRESS.json', dict(status='RUNNING', completed=len(completed), total=len(cells),
                    current=cell['cell_id'], started_unix=time.time()), replace=True)
                with (out/(cell['cell_id']+'.log')).open('x', encoding='utf8') as log:
                    child = subprocess.Popen(cell['argv'], cwd=W, stdout=log, stderr=subprocess.STDOUT,
                                             start_new_session=True)
                    rc = child.wait()
            gate = read(episode/'GATE.json')
            if rc != 0 or gate.get('gate') != 'PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT':
                raise RuntimeError('cell did not complete its independent execution gate: '+cell['cell_id'])
            record = read(episode/'RUN_RECORD.json')
            completed.append(dict(cell_id=cell['cell_id'], output=str(episode),
                run_record_sha256=sha(episode/'RUN_RECORD.json'), summary_sha256=sha(episode/'SUMMARY.json'),
                config_sha256=record['frozen_config_sha256'], command_sha256=value_sha(cell['argv']), gate=gate))
            put(out/'PROGRESS.json', dict(status='RUNNING', completed=len(completed), total=len(cells),
                last_complete=cell['cell_id'], updated_unix=time.time()), replace=True)
        except BaseException as exc:
            put(out/'STOP.json', dict(status='FAILED_PRESERVED', cell_id=cell['cell_id'],
                error=repr(exc), completed=len(completed), total=len(cells), completed_records=completed,
                scientific_interpretation='execution failure, not an effect estimate'))
            put(out/'GATE.json', dict(gate='FAIL_EXECUTION_CELL_PRESERVED', cell_id=cell['cell_id']))
            raise
    verify_source(a.source_manifest)
    put(out/'SUMMARY.json', dict(status='COMPLETE_EXECUTION_AND_INDEPENDENT_AUDITS', cells=completed,
        scientific_interpretation='factorial/paired aggregation and benefit decision remain separate'))
    put(out/'GATE.json', dict(gate='PASS_ALL_FROZEN_EXECUTION_CELLS', completed=len(completed),
        superiority='NOT_INFERRED_BY_EXECUTION_CONTROLLER'))
    put(out/'PROGRESS.json', dict(status='COMPLETE', completed=len(completed), total=len(cells)), replace=True)


if __name__ == '__main__':
    main()
