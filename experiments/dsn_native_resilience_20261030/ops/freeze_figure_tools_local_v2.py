"""Independent tools freeze plus declared synthetic CPU development gate.

No CURRENT write, remote access, model import or service queue ownership.
"""
from __future__ import annotations
import datetime
import hashlib
import importlib.util
import json
import pathlib
import platform
import subprocess
import sys

F = pathlib.Path(__file__).resolve().parents[1]
R = F.parents[1]
DEV = F/'figure_tools_source_dev'
SOURCE = F/'figure_tools_source_v2'
MANIFEST = F/'packages/FIGURE_TOOLS_SOURCE_v2.json'
BUNDLE = F/'packages/FIGURE_TOOLS_SOURCE_v2.bundle'
OUT = F/'figure_tools_cpu_local_v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(path, value):
    if path.exists():
        raise ValueError('never overwrite freeze evidence: '+str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def git(folder, *args):
    return subprocess.check_output(['git', '-C', str(folder), *args], text=True,
                                   stderr=subprocess.PIPE).strip()


for path in (SOURCE, MANIFEST, BUNDLE, OUT, F/'figure_tools_snapshot_v2', F/'FIGURE_TOOLS_FREEZE_v2.json'):
    if path.exists():
        raise ValueError('new independent freeze paths required: '+str(path))
if not (DEV/'.git').exists() or git(DEV, 'rev-parse', 'HEAD') != 'ae2677f2b68aa0c7de06820316dbeb0383322e47':
    raise ValueError('v2 narrow compatibility freeze requires preserved v1 development predecessor')
git(DEV, 'checkout', '-qb', 'codex/dsn-resilience-figure-tools-v2')
git(DEV, 'config', 'core.autocrlf', 'false')
git(DEV, 'add', '.')
git(DEV, 'commit', '-qm', 'Freeze independent bounded service evidence and figure tools v2')
commit = git(DEV, 'rev-parse', 'HEAD')
if git(DEV, 'status', '--porcelain', '--untracked-files=all'):
    raise ValueError('development source is not clean after freeze')
names = sorted(git(DEV, 'ls-files').splitlines())
rows = [dict(path=name, bytes=(DEV/name).stat().st_size, sha256=sha(DEV/name)) for name in names]
put(MANIFEST, dict(source_commit=commit, code_commit=commit,
    role='independent_posthoc_bounded_evidence_tools_no_neural_calls',
    neural_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47', files=rows))
git(DEV, 'bundle', 'create', str(BUNDLE.resolve()), 'HEAD')
git(R, 'fetch', str(BUNDLE.resolve()), 'HEAD:refs/research/dsn-resilience-figure-tools-v2')
subprocess.run(['git', 'clone', '-q', '--no-checkout', str(BUNDLE.resolve()), str(SOURCE)], check=True)
git(SOURCE, 'config', 'core.autocrlf', 'false')
git(SOURCE, 'checkout', '-q', commit)
snapshot = F/'figure_tools_snapshot_v2'
snapshot.mkdir()
for row in rows:
    target = snapshot/row['path']; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((SOURCE/row['path']).read_bytes())
OUT.mkdir()
environment = dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    host=platform.node(), platform=platform.platform(), python=sys.version,
    executable=sys.executable, CPU_controls_only=True, model_imports=0,
    source_commit=commit, neural_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47')
put(OUT/'ENVIRONMENT.json', environment)
config = dict(experiment_id='SC_RESILIENCE_FIGURE_TOOLS_LOCAL_CPU5_DEV_V1',
    code_commit=commit, source_root=str(SOURCE.resolve()), source_manifest=str(MANIFEST.resolve()),
    source_manifest_sha256=sha(MANIFEST),
    command=[sys.executable, '-B', '-m', 'unittest', '-v', 'test_evidence_controls.py'],
    environment_record=str((OUT/'ENVIRONMENT.json').resolve()), environment_sha256=sha(OUT/'ENVIRONMENT.json'),
    actual_serving_inputs='NOT_BOUND_YET_WAIT_FOR_COMPLETE_FROZEN_FORMAL36',
    synthetic_fixture_scope='CPU-only tiny counts/cuts; no native model/state fidelity or serving result',
    raw_result_location=str((OUT/'unittest.log').resolve()),
    aggregate_summary_location=str((OUT/'SUMMARY.json').resolve()),
    gate_decision_location=str((OUT/'GATE.json').resolve()),
    global_CURRENT_changed=False, GPU_launched=False)
put(OUT/'CONFIG.json', config)
record = dict(config, frozen_config=str((OUT/'CONFIG.json').resolve()),
    frozen_config_sha256=sha(OUT/'CONFIG.json'),
    started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
put(OUT/'RUN_RECORD.json', record)
spec = importlib.util.spec_from_file_location('explicit_source_preflight', R/'experiments/repository_identity_20261027/preflight.py')
preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
identity = preflight.check(SOURCE, MANIFEST)
put(OUT/'EXPLICIT_SOURCE_PREFLIGHT.json', identity)
result = subprocess.run(config['command'], cwd=SOURCE, capture_output=True, text=True,
                        encoding='utf8', errors='replace')
(OUT/'unittest.log').write_text(result.stdout+result.stderr, encoding='utf8')
passed = (result.returncode == 0 and 'Ran 5 tests' in result.stderr and '\nOK\n' in result.stderr
          and 'skipped' not in result.stderr.lower())
post_identity = preflight.check(SOURCE, MANIFEST)
put(OUT/'POST_EXPLICIT_SOURCE_PREFLIGHT.json', post_identity)
summary = dict(status='PASS_FROZEN_SOURCE_SYNTHETIC_CPU5_ZERO_SKIP' if passed else 'FAIL_SYNTHETIC_CPU_CONTROLS_PRESERVED',
    code_commit=commit, source_commit=commit, neural_source_commit=config.get('neural_source_commit', environment['neural_source_commit']),
    tests=5, skipped=0, exit_code=result.returncode,
    new_model_calls=0, CPU_controls_only=True, actual_serving_inputs_bound=False,
    source_preflight=identity['gate'], post_source_preflight=post_identity['gate'],
    source_manifest_sha256=sha(MANIFEST), config_sha256=sha(OUT/'CONFIG.json'),
    environment_sha256=sha(OUT/'ENVIRONMENT.json'), log_sha256=sha(OUT/'unittest.log'),
    scope='Synthetic posthoc-export/aggregation controls only; not neural or formal36 results.')
put(OUT/'SUMMARY.json', summary)
put(OUT/'GATE.json', summary)
freeze = dict(source_commit=commit, source=str(SOURCE.resolve()), snapshot=str(snapshot.resolve()),
    files=len(rows), source_manifest=str(MANIFEST.resolve()), source_manifest_sha256=sha(MANIFEST),
    bundle=str(BUNDLE.resolve()), bundle_sha256=sha(BUNDLE),
    synthetic_CPU_gate=summary['status'], CPU_raw_result=str(OUT.resolve()),
    actual_serving_inputs_bound=False, global_CURRENT_changed=False, GPU_launched=False)
put(F/'FIGURE_TOOLS_FREEZE_v2.json', freeze)
print(json.dumps(freeze, indent=2))
if not passed:
    raise SystemExit(1)
