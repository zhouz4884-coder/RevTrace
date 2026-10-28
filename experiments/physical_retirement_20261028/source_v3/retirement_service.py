"""One frozen, complete dual-GPU retirement service episode.

No CES, dispatch waiting, prefix backend, replayed output, or implicit retries.
The controller identifies a clean source commit and all inputs before launch,
owns one isolated runner process group, and audits actual Consumer/input/WAL
evidence after the real worker processes have exited.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

W = Path(__file__).resolve().parent
DISK = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
POLICIES = ('row_complete', 'no_cancel', 'watchdog', 'parent', 'covered', 'causal')
METHODS = ('fine_fair', 'standard_fair', 'dgft_original')
GPU_IDS = (0, 1)
EXPERIMENT = 'REVTRACE-PHYSICAL-RETIREMENT-20261028-SERVICE'
REQUIRED_SOURCES = (
    'retirement_service.py', 'retirement_audit.py', 'x_service_metrics.py',
    'runtime/scripts/run_tc_live_qwen.py', 'runtime/scripts/tc_live_worker.py',
    'runtime/scripts/row_delivery_worker.py', 'runtime/scripts/row_delivery_executor.py',
    'runtime/src/revtrace/live_qwen.py', 'runtime/src/revtrace/row_lifecycle.py',
    'runtime/src/revtrace/row_stream.py', 'runtime/src/revtrace/certified_envelope.py',
    'runtime/src/revtrace/input_debt_journal.py', 'runtime/src/revtrace/composed_kernel.py',
    'runtime/src/revtrace/certified_display.py', 'runtime/src/revtrace/kernel_runtime.py',
)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def put(path, value):
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
                                   stderr=subprocess.PIPE).decode().strip()


def verify_source(manifest_path, root=W):
    """Require the actual execution checkout, a complete manifest and full HEAD."""
    root = Path(root).resolve(strict=True)
    manifest_path = Path(manifest_path).resolve(strict=True)
    source = read(manifest_path)
    commit = source.get('code_commit', source.get('source_commit', ''))
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('full execution source commit required')
    if git(root, 'rev-parse', '--show-toplevel').replace('\\', '/').lower() != root.as_posix().lower():
        raise ValueError('execution source must be its own Git checkout root')
    if git(root, 'cat-file', '-t', commit) != 'commit' or git(root, 'rev-parse', 'HEAD') != commit:
        raise ValueError('full execution commit must resolve and equal checkout HEAD')
    if git(root, 'config', '--get', 'core.autocrlf') != 'false':
        raise ValueError('byte-exact source requires core.autocrlf=false')
    if git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('dirty source checkout; commit and freeze again')
    tracked = set(git(root, 'ls-files', '-z').split('\x00')) - {''}
    rows = source.get('files')
    if not isinstance(rows, list) or not rows:
        raise ValueError('complete source manifest required')
    names = [row['path'] for row in rows]
    if len(set(names)) != len(names) or set(names) != tracked:
        raise ValueError('complete source manifest and tracked file sets differ')
    if not set(REQUIRED_SOURCES).issubset(names):
        raise ValueError('source manifest omits complete service mechanisms')
    for row in rows:
        target = root / row['path']
        resolved = target.resolve(strict=True)
        if target.is_symlink() or not resolved.is_relative_to(root) or not target.is_file():
            raise ValueError('unsafe source manifest path: ' + row['path'])
        if target.stat().st_size != row['bytes'] or file_sha(target) != row['sha256']:
            raise ValueError('source bytes changed: ' + row['path'])
    return dict(gate='SOURCE_IDENTITY_PASS', source=str(root), code_commit=commit,
        source_manifest=str(manifest_path), source_manifest_sha256=file_sha(manifest_path),
        files_verified=len(rows), git_clean=True, full_commit_resolvable=True,
        scope='source identity only; not environment or GPU validation')


def selected_manifest(manifest, count, *, disk=DISK):
    if count < 1 or count > len(manifest.get('sessions', [])):
        raise ValueError('positive metadata-first independent session count required')
    rows = copy.deepcopy(manifest['sessions'][:count])
    ids, hashes, paths = set(), set(), set()
    for row in rows:
        sid, digest = row['source_id'], row['audio_sha256']
        duration = float(row['duration'])
        path = Path(row['path']).resolve(strict=True)
        if not isinstance(sid, str) or not sid or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('source ID and full immutable audio SHA required')
        if not math.isfinite(duration) or duration <= 0 or not path.is_file():
            raise ValueError('positive full audio duration and existing asset required')
        if not path.is_relative_to(Path(disk).resolve()):
            raise ValueError('audio must reside on the designated experiment disk')
        if sid in ids or digest in hashes or path in paths:
            raise ValueError('session/audio duplication is forbidden')
        ids.add(sid); hashes.add(digest); paths.add(path)
    return dict(sessions=rows, selection='first N rows of supplied frozen metadata; original order',
        parent_manifest_scope=manifest.get('scope', manifest.get('status', manifest.get('study'))),
        scope='metadata-selected full audio; source independence is determined by parent history, not this process repeat')


def require_idle():
    apps = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid,used_memory',
                                    '--format=csv,noheader'], text=True).strip()
    if apps:
        raise RuntimeError('GPU already in use; no child launched and no foreign process terminated: ' + apps)


def collect_environment(model, adapter):
    packages = ['torch', 'transformers', 'numpy', 'soundfile']
    if adapter == 'qwen':
        packages.append('qwen-asr')
    weights = {str(path.relative_to(model)): file_sha(path) for path in sorted(model.rglob('*'))
               if path.is_file() and path.suffix in ('.safetensors', '.bin')}
    if not weights:
        raise ValueError('actual model weight inventory required')
    assets = {path.name: file_sha(path) for path in sorted(model.iterdir())
              if path.is_file() and path.suffix in ('.json', '.txt', '.model', '.tiktoken')}
    hardware = subprocess.check_output(['nvidia-smi', '--query-gpu=index,name,uuid,driver_version,memory.total',
                                        '--format=csv,noheader'], text=True)
    present = {int(row.split(',', 1)[0]) for row in hardware.splitlines() if row.strip()}
    if not set(GPU_IDS).issubset(present):
        raise ValueError('both declared physical GPUs 0 and 1 are required')
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
        hostname=platform.node(), packages={name:importlib.metadata.version(name) for name in packages},
        hardware=hardware, measured_gpu_ids=list(GPU_IDS), model_path=str(model), adapter=adapter,
        model_weight_sha256=weights, model_asset_sha256=assets,
        process_environment={name:os.environ.get(name) for name in ('CUBLAS_WORKSPACE_CONFIG',
            'CUDA_VISIBLE_DEVICES', 'HF_HUB_OFFLINE', 'TOKENIZERS_PARALLELISM')},
        cache_condition='new processes and GPU weights; existing filesystem caches, no eviction',
        energy_scope='actual GPU0+GPU1 board power; CPU energy not measured')


def integrate_power(rows, start, end, gpu_ids=GPU_IDS):
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError('positive actual power measurement interval required')
    if len(rows) < 2 or rows[0]['observed_perf'] > start or rows[-1]['observed_perf'] < end:
        raise ValueError('power samples must bracket the complete interval')
    total = 0.0
    for a, b in zip(rows, rows[1:]):
        dt = b['observed_perf'] - a['observed_perf']
        if dt <= 0:
            raise ValueError('nonmonotone power observation clock')
        lo, hi = max(start, a['observed_perf']), min(end, b['observed_perf'])
        if hi <= lo:
            continue
        pa = sum(float(a['GPUs'][gpu]['watts']) for gpu in gpu_ids)
        pb = sum(float(b['GPUs'][gpu]['watts']) for gpu in gpu_ids)
        if not all(math.isfinite(x) and x >= 0 for x in (pa, pb)):
            raise ValueError('invalid actual GPU power sample')
        plo = pa + (pb-pa)*(lo-a['observed_perf'])/dt
        phi = pa + (pb-pa)*(hi-a['observed_perf'])/dt
        total += (plo+phi)/2*(hi-lo)
    return total


class DualPower:
    """Actual, bracketing board-power observations for exactly GPUs 0 and 1."""
    def __init__(self, path):
        self.path = Path(path); self.rows = []; self.error = None
        self.stop = threading.Event(); self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        try:
            self._await(lambda:len(self.rows) >= 2)
        except BaseException:
            self.close()
            raise

    def _await(self, condition):
        deadline = time.perf_counter() + 10
        while not condition():
            if self.error is not None:
                raise RuntimeError('actual power sampler failed') from self.error
            if time.perf_counter() >= deadline:
                raise TimeoutError('actual dual-GPU power samples unavailable')
            time.sleep(.025)

    def _run(self):
        try:
            with self.path.open('x', encoding='utf8') as stream:
                while not self.stop.is_set():
                    before = time.perf_counter()
                    raw = subprocess.check_output(['nvidia-smi', '--id=0,1',
                        '--query-gpu=index,power.draw,memory.used', '--format=csv,noheader,nounits'],
                        text=True, timeout=8)
                    after = time.perf_counter(); values = {}
                    for line in raw.splitlines():
                        gpu, watts, memory = line.split(',')
                        values[int(gpu)] = dict(watts=float(watts), memory_MiB=float(memory))
                    if set(values) != set(GPU_IDS):
                        raise ValueError('power sampler did not observe exactly GPU0 and GPU1')
                    row = dict(observed_perf=(before+after)/2, query_seconds=after-before, GPUs=values)
                    with self.lock:
                        self.rows.append(row)
                    stream.write(json.dumps(row, allow_nan=False)+'\n'); stream.flush()
                    self.stop.wait(.18)
        except BaseException as exc:
            self.error = exc

    def joules(self, start, end):
        self._await(lambda:bool(self.rows) and self.rows[-1]['observed_perf'] >= end)
        with self.lock:
            rows = list(self.rows)
        return integrate_power(rows, start, end)

    def close(self):
        self.stop.set(); self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise TimeoutError('owned power sampler did not exit')


def process_identity(pid, proc_root=Path('/proc')):
    raw = (Path(proc_root)/str(pid)/'stat').read_text()
    fields = raw.rsplit(')', 1)[1].split()
    if int(raw.split('(', 1)[0]) != pid:
        raise RuntimeError('owned process identity mismatch')
    return dict(pid=pid, parent_pid=int(fields[1]), process_group=int(fields[2]),
                session=int(fields[3]), linux_start_ticks=fields[19], state=fields[0])


def terminate_owned(child, identity):
    """Signal only the isolated group created by this Popen object."""
    if child.poll() is not None:
        return
    current = process_identity(child.pid)
    if any(str(current[key]) != str(identity[key]) for key in ('pid', 'process_group', 'session', 'linux_start_ticks')):
        raise RuntimeError('refuse to signal changed owned process identity')
    if current['process_group'] != child.pid or current['session'] != child.pid:
        raise RuntimeError('refuse to signal a nonisolated process group')
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=20)
    except subprocess.TimeoutExpired:
        # Same child still has an unreaped Popen handle; revalidate before KILL.
        current = process_identity(child.pid)
        if str(current['linux_start_ticks']) != str(identity['linux_start_ticks']):
            raise RuntimeError('owned process identity changed during termination')
        os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=20)


def run_child(command, episode, timeout):
    started = time.perf_counter()
    with (episode/'runner.log').open('x', encoding='utf8') as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 cwd=W, start_new_session=True)
        try:
            identity = process_identity(child.pid)
            if identity['process_group'] != child.pid or identity['session'] != child.pid:
                raise RuntimeError('runner did not acquire its own isolated session')
            put(episode/'OWNED_RUNNER.json', dict(identity, launch_perf=started, argv_sha256=value_sha(command)))
            try:
                rc = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                terminate_owned(child, identity)
                raise TimeoutError('bounded service cell timeout; offered work retained as unfinished') from exc
        except BaseException:
            if child.poll() is None:
                # On Linux the pre-exec setsid belongs to this exact child.
                if 'identity' not in locals():
                    identity = process_identity(child.pid)
                terminate_owned(child, identity)
            raise
    return dict(returncode=rc, launch_perf=started, exit_perf=time.perf_counter(), pid=child.pid)


def build_command(a, episode, source, *, root=W):
    command = [sys.executable, str(root/'runtime/scripts/run_tc_live_qwen.py'),
        '--model', str(a.model), '--model-adapter', a.adapter,
        '--manifest', str(episode/'manifest.json'), '--output', str(episode/'attempt0'),
        '--code-commit', source['code_commit'], '--study-id', EXPERIMENT,
        '--sessions', str(a.sessions), '--arrival', a.arrival, '--seed', str(20261028+a.repeat),
        '--microbatch', '16', '--max-new-tokens', '256', '--timeout', str(a.service_timeout),
        '--proposal-gpus', '0', '--authority-gpus', '1',
        '--trusted-text-binding', '--capture-model-inputs', '--result-delivery', 'row',
        '--protocol-kernel', '--kernel-copy-mode', 'event-cow', '--phase-n-instrumentation',
        '--display-protocol', 'canonical-snapshot-v1', '--publish-canonical-display',
        '--consumer-policy', getattr(a,'confirmation_consumer','two_lane'),
        '--confirmation-consumer', getattr(a,'confirmation_consumer','two_lane'), '--proposal-barrier', 'decoupled',
        '--proposal-reconciliation', 'lazy', '--journal-sync-mode', 'group_ready',
        '--physical-retirement', a.policy, '--retirement-watchdog-seconds', str(a.watchdog_seconds),
        '--study-authority-rho', str(a.rho),
        '--envelope-config', str(episode/'envelope.json'), '--arrival-schedule', str(episode/'arrivals.json'),
        '--episode-context', str(episode/'episode.json'), '--input-journal-path', str(episode/'input.wal'),
        '--durable-journal-path', str(episode/'canonical.wal')]
    if a.retain == 'no':
        command.append('--disable-private-retention')
    else:
        command.append('--retain-verified-private-prefix')
    if a.fixture is not None:
        command += ['--retirement-fault-fixture', str(episode/'fixture.json')]
    if a.adapter == 'whisper':
        command += ['--whisper-context-policy', 'reserve-generation-tail-v1']
    return command


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--adapter', choices=['qwen', 'whisper'], default='qwen')
    p.add_argument('--policy', choices=POLICIES, required=True)
    p.add_argument('--method', choices=METHODS, required=True)
    p.add_argument('--rho', type=int, choices=[1, 3], default=1)
    p.add_argument('--sessions', type=int, default=16)
    p.add_argument('--arrival', choices=['sync', 'staggered'], default='sync')
    p.add_argument('--repeat', type=int, default=0)
    p.add_argument('--fixture', type=Path)
    p.add_argument('--retain', choices=['yes', 'no'], default='yes')
    p.add_argument('--confirmation-consumer', choices=['checked_snapshot','two_lane'], default='two_lane')
    p.add_argument('--watchdog-seconds', type=float, default=2.)
    p.add_argument('--service-timeout', type=float, default=240.)
    p.add_argument('--wall-timeout', type=float, default=420.)
    p.add_argument('--defer-audit', action='store_true', help='smoke only: final gate explicitly remains incomplete')
    return p


def validate_options(a, *, disk=DISK, root=W):
    a.out = a.out.resolve()
    a.model = a.model.resolve(strict=True)
    if a.out == Path(disk).resolve() or not a.out.is_relative_to(Path(disk).resolve()/'results/revtrace/physical_retirement_20261028'):
        raise ValueError('new scoped result directory on designated 8TB disk required')
    if a.out.exists() or a.out.is_relative_to(Path(root).resolve()):
        raise ValueError('new output outside frozen source required; never overwrite a run')
    if not a.model.is_dir() or not a.model.is_relative_to(Path(disk).resolve()):
        raise ValueError('actual model must remain on designated experiment disk')
    if a.sessions < 1 or a.repeat < 0:
        raise ValueError('one-cell carrier requires positive sessions and nonnegative repeat')
    for name in ('watchdog_seconds', 'service_timeout', 'wall_timeout'):
        if not math.isfinite(getattr(a, name)) or getattr(a, name) <= 0:
            raise ValueError('positive finite frozen '+name+' required')
    if a.wall_timeout <= a.service_timeout:
        raise ValueError('wall timeout must allow model startup outside service timeout')
    if a.adapter == 'whisper' and (a.policy != 'row_complete' or a.fixture is not None):
        raise ValueError('Whisper confirmation supports original row-complete without Qwen fault fixture')
    if sys.flags.optimize:
        raise ValueError('independent audits require Python without -O')


def main(argv=None):
    a = parser().parse_args(argv)
    validate_options(a)
    episode = a.out
    episode.mkdir(parents=True)
    runner = None
    try:
        require_idle()
        source = verify_source(a.source_manifest)
        put(episode/'SOURCE_IDENTITY.json', source)
        selected = selected_manifest(read(a.manifest), a.sessions)
        put(episode/'manifest.json', selected)
        fixture = None
        if a.fixture is not None:
            fixture = read(a.fixture)
            if fixture.get('schema') != 'physical-retirement-f2-input-fixture-v1':
                raise ValueError('frozen input-only retirement fixture required')
            put(episode/'fixture.json', fixture)
        environment = collect_environment(a.model, a.adapter)
        put(episode/'ENVIRONMENT.json', environment)
        # Budget covers the entire offered cohort. No overload credit/rejection
        # intervention participates in this retirement experiment.
        audio_total = sum(float(row['duration']) for row in selected['sessions'])
        put(episode/'envelope.json', dict(method=a.method,
            budget_audio_seconds=max(1000., audio_total+2*a.rho*a.sessions),
            warning_age=100., critical_age=200., clear_age=10., display_slo=2.,
            queue_threshold=10000, reject_new_after_seconds=1000., tick_seconds=.001))
        put(episode/'arrivals.json', dict(offsets=[0. if a.arrival=='sync' else sid*.25 for sid in range(a.sessions)]))
        command = build_command(a, episode, source)
        put(episode/'COMMAND.json', dict(argv=command, argv_sha256=value_sha(command), code_commit=source['code_commit']))
        config = dict(policy=a.policy, method=a.method, rho=a.rho, sessions=a.sessions,
            arrival=a.arrival, repeat=a.repeat, seed=20261028+a.repeat, adapter=a.adapter,
            retain_private_prefix=a.retain, confirmation_consumer=a.confirmation_consumer,
            consumer_policy=a.confirmation_consumer, watchdog_seconds=a.watchdog_seconds,
            service_timeout_seconds=a.service_timeout, wall_timeout_seconds=a.wall_timeout,
            display_slo_seconds=2., commit_slo_seconds=8., microbatch=16, max_new_tokens=256,
            source_manifest_sha256=source['source_manifest_sha256'],
            original_manifest_sha256=file_sha(a.manifest), selected_manifest_sha256=file_sha(episode/'manifest.json'),
            environment_sha256=file_sha(episode/'ENVIRONMENT.json'), command_sha256=file_sha(episode/'COMMAND.json'),
            envelope_sha256=file_sha(episode/'envelope.json'), arrival_sha256=file_sha(episode/'arrivals.json'),
            fixture_sha256=None if fixture is None else file_sha(episode/'fixture.json'),
            deferred_audit=a.defer_audit,
            resources='same FP16 Proposer GPU0 + FP32 Authority GPU1; full kernel/event-COW/D1/Row, canonical+input WAL and actual Consumer',
            source_independence='fresh processes/repeats are not new independent source audio',
            performance_claim='one cell records evidence; benefit requires frozen cross-arm comparison')
        experiment_id=f'{EXPERIMENT}-{a.adapter}-{a.method}-{a.policy}-rho{a.rho}-c{a.sessions}-{a.arrival}-r{a.repeat}-{a.confirmation_consumer}-retain{a.retain}'
        put(episode/'FREEZE.json', dict(experiment_id=experiment_id, code_commit=source['code_commit'],
            frozen_config=config, raw_result_location=str(episode/'attempt0'),
            aggregate_summary_location=str(episode/'SUMMARY.json'), gate_decision_location=str(episode/'GATE.json')))
        record = dict(experiment_id=experiment_id, code_commit=source['code_commit'],
            frozen_config=str(episode/'FREEZE.json'), frozen_config_sha256=file_sha(episode/'FREEZE.json'),
            environment_record=str(episode/'ENVIRONMENT.json'), environment_record_sha256=file_sha(episode/'ENVIRONMENT.json'),
            source_manifest=str(a.source_manifest.resolve()), source_manifest_sha256=source['source_manifest_sha256'],
            raw_result_location=str(episode/'attempt0'), aggregate_summary_location=str(episode/'SUMMARY.json'),
            gate_decision_location=str(episode/'GATE.json'), command_record=str(episode/'COMMAND.json'),
            command_record_sha256=file_sha(episode/'COMMAND.json'))
        put(episode/'RUN_RECORD.json', record)
        require_idle()
        # External power sampler starts before the cold process and remains live
        # until the complete serving and cold intervals have right-hand samples.
        sampler = DualPower(episode/'episode_power.jsonl')
        try:
            runner = run_child(command, episode, a.wall_timeout)
            put(episode/'RUNNER_EXIT.json', runner)
            if runner['returncode']:
                raise RuntimeError('real service runner failed with rc='+str(runner['returncode']))
            measurement = read(episode/'attempt0/power_samples.json')
            st, en = measurement['measurement_start_perf'], measurement['measurement_end_perf']
            put(episode/'POWER_MEASURED.json', dict(serving_start_perf=st, serving_end_perf=en,
                serving_both_GPU_joules=sampler.joules(st, en),
                cold_launch_to_exit_both_GPU_joules=sampler.joules(runner['launch_perf'], runner['exit_perf']),
                cold_launch_perf=runner['launch_perf'], cold_exit_perf=runner['exit_perf'],
                samples=len(sampler.rows), physical_GPU_ids=list(GPU_IDS),
                scope='actual external board power GPU0+GPU1; serving/cold intervals distinct; no CPU energy'))
        finally:
            sampler.close()
        require_idle()
        verified_after = verify_source(a.source_manifest)
        put(episode/'SOURCE_IDENTITY_AFTER.json', verified_after)
        if verified_after != source:
            raise RuntimeError('source identity changed during service')
        if a.defer_audit:
            summary = dict(status='REAL_RUN_COMPLETE_AUDIT_DEFERRED', experiment_id=experiment_id,
                raw_result_location=str(episode/'attempt0'), evidence_complete=False)
            gate = dict(gate='INCOMPLETE_AUDIT_DEFERRED', source_commit=source['code_commit'],
                        no_performance_or_correctness_acceptance=True)
        else:
            from retirement_audit import audit_episode, write_tables
            independent, tables = audit_episode(episode, selected)
            put(episode/'INDEPENDENT_SUMMARY.json', independent)
            write_tables(episode/'audit', independent, tables)
            summary = dict(status='COMPLETE_SINGLE_CELL_AND_INDEPENDENT_AUDIT', experiment_id=experiment_id,
                source_commit=source['code_commit'], config=config, independent_summary=independent,
                raw_result_location=str(episode/'attempt0'), audit_location=str(episode/'audit'),
                performance_conclusion='NOT_INFERRED_FROM_SINGLE_CELL')
            gate = dict(gate='PASS_SINGLE_CELL_EXECUTION_AND_INDEPENDENT_AUDIT',
                source_commit=source['code_commit'], performance_superiority='REQUIRES_CROSS_ARM_COMPARISON',
                original_deadlines_and_all_offered_inputs_retained=True)
        put(episode/'SUMMARY.json', summary)
        put(episode/'GATE.json', gate)
    except BaseException:
        failure = dict(status='FAILED_PRESERVED', error=traceback.format_exc(),
            runner=runner, raw_result_location=str(episode/'attempt0'),
            unfinished_offered_inputs='retained for analysis; no successful service claim')
        if not (episode/'STOP.json').exists():
            put(episode/'STOP.json', failure)
        if not (episode/'GATE.json').exists():
            put(episode/'GATE.json', dict(gate='NO_GO_SINGLE_CELL_FAILURE_PRESERVED',
                                         stop_record=str(episode/'STOP.json')))
        raise
    print(json.dumps(summary, allow_nan=False))
    return summary


if __name__ == '__main__':
    main()
