"""Same-input trusted-recovery startup experiment; actual owned SIGKILL only.

Run only after review, source commit/manifest freeze and CPU gates. This file
does not import a model or production scheduler. Its independent audit checks
recorded real-worker/Consumer evidence; it never synthesizes GPU outputs.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import traceback

B = Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
W = Path(__file__).resolve().parent
MODES = ('full_first', 'descriptor_workers_first')
METHODS = ('dgft_original', 'standard_fair')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def put(path, value):
    """Exclusive new evidence file: never replace a prior result."""
    with Path(path).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def proc_identity(pid, proc_root=Path('/proc')):
    p = proc_root / str(int(pid))
    raw = (p / 'stat').read_text()
    stat_pid, _ = raw.split('(', 1)
    fields = raw.rsplit(')', 1)[1].split()
    if int(stat_pid) != int(pid):
        raise RuntimeError('proc PID mismatch')
    return dict(pid=int(pid), state=fields[0], parent_pid=int(fields[1]),
                pgid=int(fields[2]), linux_start_ticks=fields[19],
                command_sha256=hashlib.sha256((p / 'cmdline').read_bytes()).hexdigest())


def live_identity(expected, proc_root=Path('/proc')):
    try:
        now = proc_identity(expected['pid'], proc_root)
    except (FileNotFoundError, ProcessLookupError):
        return False
    return (now['linux_start_ticks'] == str(expected['linux_start_ticks']) and
            now['state'] != 'Z')


def require_same_process(expected, actual):
    for key in ('pid', 'linux_start_ticks', 'pgid', 'command_sha256'):
        if str(expected[key]) != str(actual[key]):
            raise RuntimeError('owned process changed: ' + key)
    if actual['state'] == 'Z':
        raise RuntimeError('owned process is already a zombie')


def validate_group(owner, workers, snapshot):
    """Reject PID reuse, foreign group members and wrong worker identity."""
    by_pid = {p['pid']: p for p in snapshot}
    require_same_process(owner, by_pid[owner['pid']])
    if owner['pgid'] != owner['pid']:
        raise RuntimeError('owner must create its own isolated process group')
    if {w['name'] for w in workers} != {'proposal-0', 'authority-1'}:
        raise RuntimeError('expected exactly the two frozen workers')
    if len(workers) != 2:
        raise RuntimeError('duplicate or additional worker handles')
    for worker in workers:
        now = by_pid[worker['pid']]
        expected = dict(worker, pgid=owner['pgid'])
        require_same_process(expected, now)
        if now['parent_pid'] != owner['pid'] or worker['parent_pid'] != owner['pid']:
            raise RuntimeError('worker is not owned by this coordinator')
    members = [p for p in snapshot if p['pgid'] == owner['pgid']]
    for member in members:
        seen = set()
        pid = member['pid']
        while pid != owner['pid']:
            if pid in seen or pid not in by_pid:
                raise RuntimeError('unowned process shares target group')
            seen.add(pid)
            pid = by_pid[pid]['parent_pid']
    return members


def process_snapshot():
    result = []
    for p in Path('/proc').iterdir():
        if p.name.isdecimal():
            try:
                result.append(proc_identity(int(p.name)))
            except (FileNotFoundError, ProcessLookupError):
                pass
    return result


def gpu_apps():
    return subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid,used_memory',
                                    '--format=csv,noheader'], text=True).strip()


def require_idle():
    apps = gpu_apps()
    if apps:
        raise RuntimeError('GPU belongs to a live task; queue stopped without killing it: ' + apps)


def wait_released(handles, timeout=40):
    deadline = time.perf_counter() + timeout
    owned = {str(h['pid']) for h in handles}
    while time.perf_counter() < deadline:
        running = [h for h in handles if live_identity(h)]
        active = {line.split(',')[0].strip() for line in gpu_apps().splitlines() if line.strip()}
        if not running and not (active & owned):
            return
        time.sleep(.1)
    raise TimeoutError('owned workers or their driver allocations did not release; no next launch')


def kill_owned(proc, owner, attempt):
    if proc.poll() is not None:
        raise RuntimeError('owner exited before fault injection')
    workers = read(attempt / 'OWNED_WORKER_HANDLES.json')
    members = validate_group(owner, workers, process_snapshot())
    # Recheck the group leader at the last possible point before the signal.
    require_same_process(owner, proc_identity(owner['pid']))
    before = gpu_apps()
    requested = time.perf_counter()
    os.killpg(owner['pgid'], signal.SIGKILL)
    sent = time.perf_counter()
    rc = proc.wait(timeout=30)
    exited = time.perf_counter()
    if rc != -signal.SIGKILL:
        raise RuntimeError('fault did not terminate the owner by SIGKILL')
    wait_released(members)
    return dict(kill_perf=requested, kill_signal_sent_perf=sent, owner_exit_perf=exited,
                owner_returncode=rc, owner=owner, owned_workers=workers,
                verified_group=members, prekill_GPU_processes=before,
                scope='verified-owned coordinator and its workers; process fault, not host/power loss')


def launch(cmd, E, attempt):
    log = (E / f'runner_{attempt}.log').open('x', encoding='utf8')
    launched = time.perf_counter()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    owner = proc_identity(proc.pid)
    owner['launch_perf'] = launched
    if owner['pgid'] != proc.pid:
        raise RuntimeError('failed to isolate the experiment process group')
    put(E / f'OWNER_HANDLE_{attempt}.json', owner)
    return proc, owner, log


def cells(repeats, start_repeat=0):
    result = []
    base = [(method, mode) for method in METHODS for mode in MODES]
    for repeat in range(start_repeat, start_repeat + repeats):
        order = base[repeat % 4:] + base[:repeat % 4]
        if repeat % 2:
            order = list(reversed(order))
        result.extend(dict(method=m, restart_startup_order=s, repeat=repeat,
                           prefix_startup_order='full_first', processor_mode='reuse') for m, s in order)
    return result


def command(source, a, D, E, cell, attempt):
    mode = 'full_first' if attempt == 0 else cell['restart_startup_order']
    cmd = [sys.executable, str(W / 'runtime/scripts/run_tc_live_qwen.py'),
           '--model', str(a.model), '--manifest', str(D / 'manifest.json'),
           '--output', str(E / f'attempt{attempt}'), '--code-commit', source['code_commit'],
           '--study-id', 'REVTRACE-TRUSTED-RECOVERY-PAIR-20261027',
           '--sessions', str(a.sessions), '--microbatch', '16', '--max-new-tokens', '256',
           '--timeout', str(a.runtime_timeout), '--trusted-text-binding', '--capture-model-inputs',
           '--result-delivery', 'row', '--receipt-trace', '--protocol-kernel',
           '--kernel-copy-mode', 'event-cow', '--phase-n-instrumentation',
           '--journal-sync-mode', 'group_ready', '--recovery-readiness', 'early',
           '--startup-processor-mode', 'reuse', '--startup-order', mode,
           '--render-descriptor', str(a.render_descriptor),
           '--render-descriptor-sha256', a.render_descriptor_sha256,
           '--envelope-config', str(E / 'envelope.json'),
           '--arrival-schedule', str(E / 'arrivals.json'),
           '--episode-context', str(E / 'episode.json'),
           '--input-journal-path', str(E / 'input.wal'),
           '--durable-journal-path', str(E / 'canonical.wal')]
    if attempt == 0:
        cmd += ['--pause-post-sync-target', a.fault_target]
    return cmd


def logical_cut(E, trigger):
    from paired_recovery_audit import frames
    journal, tail = frames(E / 'canonical.wal.pre-recovery')
    inputs, input_tail = frames(E / 'input.wal.pre-recovery', True, True)
    if tail or input_tail:
        raise RuntimeError('post-sync fault unexpectedly left incomplete durable frames')
    transitions = [r for r in journal if r['kind'] == 'commit']
    snapshot = next(r['snapshot'] for r in reversed(inputs) if r['kind'] == 'envelope-snapshot')
    states = {int(k):dict(F=v['audio_frontier_window'], P=v['prompt_tokens'], version=v['checkpoint_id'])
              for k, v in journal[0]['states'].items()}
    history = []
    for row in transitions:
        sid = row['session_id']; d = row['state_delta']; e = row['event']
        if d['audio_start_sample'] != states[sid]['F']:
            raise RuntimeError('canonical interval gap at fault cutoff')
        states[sid] = dict(F=d['audio_end_sample'], P=d['next_prompt_tokens'], version=e['checkpoint_id'])
        history.append(dict(sid=sid, transaction=row['transaction_id'], parent=row['parent_checkpoint_id'],
                            start=d['audio_start_sample'], end=d['audio_end_sample'],
                            Z=d['segment_tokens'], P=d['next_prompt_tokens'], text=e['committed_text']))
    A = {int(k):v['accepted'] for k,v in snapshot['sessions'].items()}
    if {str(sid):s['F'] for sid,s in states.items()} != trigger['durable_frontiers']:
        raise RuntimeError('fault marker durable frontier differs from actual retained WAL')
    # Strip absolute timing/epoch identities but keep actual model outcomes and
    # complete global logical cut. Unequal cuts are NOT silently called pairs.
    input_resume={sid:{k:v.get(k) for k in ('offered','accepted','reserved','rejected','eof',
                                          'rejection_reason','accepted_prefix_sha256')}
                  for sid,v in snapshot['sessions'].items()}
    matching = dict(history=sorted(history,key=lambda h:(h['sid'],h['start'])), states=states, accepted=A,
                    input_resume_obligations=input_resume,
                    target_transactions=sorted(trigger['transactions']),
                    rejected={k:v['rejected'] for k,v in snapshot['sessions'].items()})
    return dict(wal_records=len(journal), wal_last_sequence=journal[-1]['sequence'],
                wal_sha256=file_sha(E / 'canonical.wal.pre-recovery'),
                input_records=len(inputs), input_last_sequence=inputs[-1]['sequence'],
                accepted_frontiers=A, durable_frontiers={sid:s['F'] for sid,s in states.items()},
                precrash_debt_samples={sid:A[sid]-s['F'] for sid,s in states.items()},
                exact_logical_cut_sha256=object_sha(matching), matching_cut=matching,
                scope='WAL sequence and input debt plus model history; no clock-normalized byte identity claim')


def convert_power(power, started, ended, E):
    # Force an enclosing real sample, then preserve CK5-compatible raw rows.
    joules = power.joules(started, ended)
    with power.lock:
        raw = list(power.rows)
    converted = [dict(gpu=int(gpu), t=row['observed_perf'], power_w=value['watts'],
                      memory_MiB=value['memory_MiB'], query_seconds=row['query_seconds'])
                 for row in raw for gpu,value in row['GPUs'].items() if int(gpu) in (0,1)]
    put(E / 'EPISODE_POWER.json', dict(samples=converted, outer_launch_perf=started,
        outer_end_perf=ended, GPU_joules_launch_to_exit=joules,
        scope='GPU board power, including killed work and both model reloads; CPU energy not measured'))


def run_cell(a, D, E, cell, source):
    from memory_gpu_pilot import Power
    from paired_recovery_audit import rows, episode, recovery_clocks
    E.mkdir()
    put(E / 'envelope.json', dict(method=cell['method'], budget_audio_seconds=1000.,
        warning_age=100., critical_age=200., clear_age=10., display_slo=2.,
        commit_slo=8., queue_threshold=10000, reject_new_after_seconds=1000., tick_seconds=.001,
        model_weight_sha256=read(D/'ENVIRONMENT.json')['model_weight_sha256']))
    put(E / 'arrivals.json', dict(offsets=[0. if a.arrival=='sync' else sid*.25 for sid in range(a.sessions)]))
    cmds = [command(source,a,D,E,cell,k) for k in (0,1)]
    for k,cmd in enumerate(cmds):
        put(E / f'COMMAND_{k}.json', dict(argv=cmd, code_commit=source['code_commit']))
    put(E / 'CONFIG_FREEZE.json', dict(cell=cell, sessions=a.sessions, arrival=a.arrival,
        envelope_sha256=file_sha(E/'envelope.json'), arrivals_sha256=file_sha(E/'arrivals.json'),
        source_commit=source['code_commit'], source_manifest_sha256=file_sha(a.source_manifest),
        environment_sha256=file_sha(D/'ENVIRONMENT.json'), descriptor_sha256=a.render_descriptor_sha256,
        experiment_id='REVTRACE-TRUSTED-RECOVERY-PAIR-20261027/'+E.name,
        raw_result_location=str(E), aggregate_summary_location=str(E/'AUDIT.json'),
        gate_decision_location=str(E/'GATE.json'), fault_target=a.fault_target))
    power=Power(E/'episode_power.jsonl');started=time.perf_counter();proc=owner=log=None
    try:
        require_idle()
        proc,owner,log=launch(cmds[0],E,0)
        until=time.perf_counter()+a.fault_timeout
        marker=E/'attempt0/POST_SYNC_KILL_READY.json'
        while not marker.exists():
            if proc.poll() is not None:
                raise RuntimeError('coordinator ended before frozen logical post-sync target')
            if time.perf_counter()>until:
                raise TimeoutError('frozen logical fault target unavailable; do not substitute another point')
            time.sleep(.02)
        trigger=read(marker)
        if trigger.get('logical_target')!=a.fault_target:
            raise RuntimeError('unexpected logical fault identity')
        killed=kill_owned(proc,owner,E/'attempt0');log.close();log=None;proc=None
        context=read(E/'episode.json');events,lost=rows(E/'attempt0/events.jsonl',True)
        killed.update(trigger=trigger,episode_origin_perf=context['origin_perf'],
                      server_input_ACKs=[e for e in events if e['kind']=='input-ack'],
                      published_commits=[e for e in events if e['kind']=='commit'],
                      partial_event_tail_bytes=lost)
        for name in ('input.wal','canonical.wal'):
            shutil.copyfile(E/name,E/(name+'.pre-recovery'))
        put(E/'KILL.json',killed)
        put(E/'FAULT_CUT.json',logical_cut(E,trigger))
        require_idle()
        proc,owner,log=launch(cmds[1],E,1)
        rc=proc.wait(timeout=a.resume_timeout)
        log.close();log=None
        if rc:raise RuntimeError('resume failed rc='+str(rc))
        wait_released(read(E/'attempt1/OWNED_WORKER_HANDLES.json'))
        ended=time.perf_counter()
        put(E/'RUN_COMPLETE_PENDING_AUDIT.json',dict(cell=cell,source=source['code_commit'],
              actual_episode_end_perf=ended,final_attempt=1))
        convert_power(power,started,ended,E)
        service=episode(E,read(D/'manifest.json'));recovery=recovery_clocks(E)
        for attempt in (0,1):
            cfg=read(E/f'attempt{attempt}/config.json')
            if cfg['rho']!=3 or cfg['fine_seconds']!=2. or cfg['envelope']['method']!=cell['method']:
                raise RuntimeError('frozen resource/rho contract changed')
            init=read(E/f'attempt{attempt}/initialization.json')
            expected='full_first' if attempt==0 else cell['restart_startup_order']
            if init['startup_order']!=expected or init['startup_processor_mode']!='reuse':
                raise RuntimeError('initialization intervention mismatch')
            provenance=read(E/f'attempt{attempt}/provenance.json')
            if provenance['code_commit']!=source['code_commit']:
                raise RuntimeError('runtime source label differs from byte-checked source')
            shas={f['path']:f['sha256'] for f in source['files']}
            for path,digest in provenance['source_sha256'].items():
                if shas['runtime/'+path]!=digest:
                    raise RuntimeError('executed source byte mismatch: '+path)
        final=read(E/'attempt1/result.json')
        measured_restart=dict(input_fsync_calls=final['input_fsync_calls'],
            input_fsync_seconds=final['input_fsync_seconds'],
            consumer_cpu_seconds=final['consumer']['consumer_cpu_seconds'],
            input_journal_bytes=(E/'input.wal').stat().st_size,
            canonical_journal_bytes=(E/'canonical.wal').stat().st_size,
            startup_profile=read(E/'attempt1/startup_summary.json'),
            scope='attempt1 counters only; killed-prefix host counters are not reconstructed as measurements')
        summary=dict(cell=cell,service=service,recovery=recovery,restart_cost=measured_restart,
                     fault_cut_sha256=read(E/'FAULT_CUT.json')['exact_logical_cut_sha256'])
        put(E/'AUDIT.json',summary)
        put(E/'GATE.json',dict(gate='PASS_RECORDED_RECOVERY_PENDING_SEPARATE_ASSET_REPLAY',
            full_scope='actual job and model-input receipts, WAL ancestry, actual Consumer and preserved input debt',
            independent_asset_replay='NOT_PERFORMED_BY_THIS_CONTROLLER',
            performance='single repeat is descriptive, not statistical superiority'))
        return summary
    finally:
        if proc is not None and proc.poll() is None:
            try:
                cleanup=kill_owned(proc,owner,E/f'attempt{1 if (E/"OWNER_HANDLE_1.json").exists() else 0}')
                put(E/'FAILURE_OWNED_CLEANUP.json',cleanup)
            except BaseException:
                # Never bypass identity validation to clean up an unknown group.
                put(E/'CLEANUP_REQUIRES_INSPECTION.json',dict(error=traceback.format_exc(),owner=owner))
        if log is not None:log.close()
        power.close()


def paired_rows(summaries):
    lookup={(r['cell']['method'],r['cell']['repeat'],r['cell']['restart_startup_order']):r for r in summaries}
    out=[]
    for method,repeat in sorted({(r['cell']['method'],r['cell']['repeat']) for r in summaries}):
        a=lookup.get((method,repeat,'full_first'));b=lookup.get((method,repeat,'descriptor_workers_first'))
        if a is None or b is None:continue
        match=a['fault_cut_sha256']==b['fault_cut_sha256']
        row=dict(method=method,repeat=repeat,exact_fault_cut_match=match,
                 decision='PAIRED_DESCRIPTIVE' if match else 'UNMATCHED_CUT_NO_PAIRED_CLAIM',
                 full_first=a['recovery'],descriptor_workers_first=b['recovery'])
        if match:
            row['paired_seconds_difference_overlap_minus_full']={
                k:(b['recovery'][k]-a['recovery'][k] if a['recovery'][k] is not None and b['recovery'][k] is not None else None)
                for k in ('RTO_old_all_durable_facts','RTO_new_first_certified_fact','RTO_precrash_accepted_debt')}
        out.append(row)
    return out


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--model',type=Path,default=B/'models/Qwen3-ASR-1.7B')
    p.add_argument('--render-descriptor',type=Path,required=True);p.add_argument('--render-descriptor-sha256',required=True)
    p.add_argument('--sessions',type=int,default=4);p.add_argument('--arrival',choices=['sync','staggered'],default='staggered')
    p.add_argument('--repeats',type=int,default=1);p.add_argument('--start-repeat',type=int,default=0)
    p.add_argument('--fault-target',default='0:192000')
    p.add_argument('--runtime-timeout',type=float,default=240.);p.add_argument('--fault-timeout',type=float,default=160.)
    p.add_argument('--resume-timeout',type=float,default=420.)
    a=p.parse_args();D=a.output.resolve()
    if sys.flags.optimize:
        raise RuntimeError('audit assertions require normal Python, not -O')
    if not D.is_relative_to(B/'results/revtrace/freeze_boundary_20261027') or D.exists():
        raise ValueError('new scoped8TB result path required')
    if a.sessions!=4 or a.repeats<1 or a.start_repeat<0:
        raise ValueError('this bounded pilot freezes c4 and positive repeat count')
    sys.path.insert(0,str(W/'runtime/src'))
    from revtrace.recovery_fault import parse_post_sync_target
    target=parse_post_sync_target(a.fault_target)
    if target[0]>=a.sessions or target[1]%96000:
        raise ValueError('target must be a frozen coarse frontier in one selected session')
    source=read(a.source_manifest)
    if len(source['code_commit'])!=40:raise ValueError('full source commit required')
    for f in source['files']:
        path=(W/f['path']).resolve()
        if not path.is_relative_to(W) or file_sha(path)!=f['sha256']:
            raise RuntimeError('complete source manifest mismatch: '+f['path'])
    if file_sha(a.render_descriptor)!=a.render_descriptor_sha256:
        raise RuntimeError('descriptor bytes do not match the frozen trust anchor')
    selected=read(a.manifest)['sessions'][:a.sessions]
    if len(selected)!=a.sessions or len({s['source_id'] for s in selected})!=a.sessions:
        raise ValueError('four independent metadata-selected sources required')
    require_idle();D.mkdir(parents=True)
    completed=[];summaries=[]
    try:
        put(D/'manifest.json',dict(sessions=selected,scope='fixed metadata-first c4 development sources, no outcome selection'))
        weights={p.name:file_sha(p) for p in sorted(a.model.iterdir()) if p.suffix in ('.safetensors','.bin')}
        if not weights:raise ValueError('actual model weight inventory required')
        env=dict(python=sys.version,platform=platform.platform(),hostname=platform.node(),
            packages={x:importlib.metadata.version(x) for x in ('torch','transformers','qwen-asr','numpy','soundfile')},
            hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True),
            model_weight_sha256=weights,
            cache_condition='cold processes and GPU weights reloaded; existing filesystem caches, no disk-cache eviction',
            cpu_energy='not measured')
        put(D/'ENVIRONMENT.json',env)
        plan=cells(a.repeats,a.start_repeat)
        put(D/'FREEZE.json',dict(experiment_id='REVTRACE-TRUSTED-RECOVERY-PAIR-20261027',
            code_commit=source['code_commit'],source_manifest_sha256=file_sha(a.source_manifest),
            original_manifest_sha256=file_sha(a.manifest),manifest_sha256=file_sha(D/'manifest.json'),
            descriptor_sha256=a.render_descriptor_sha256,environment_sha256=file_sha(D/'ENVIRONMENT.json'),
            cells=plan,expected=len(plan),fault_target=a.fault_target,
            prefix='full_first/reuse for every arm; restart order alone changes',
            contract='fine2s/rho3, P FP16 GPU0 + A FP32 GPU1, MB16, 256tokens, row, full kernel, D1, group-ready WAL, local Consumer, D2/C8',
            clock='original arrival perf_counter preserved across SIGKILL; no deadline reset',
            gate='logical target must be reached; exact full logical cuts required for paired inference',
            raw_result_location=str(D),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json')))
        for i,cell in enumerate(plan):
            require_idle()
            name=f'{i:02}-{cell["method"]}-{cell["restart_startup_order"]}-r{cell["repeat"]}'
            put(D/f'PROGRESS_{i:02}.json',dict(status='RUNNING',current=name,completed=completed,expected=len(plan)))
            summaries.append(run_cell(a,D,D/name,cell,source));completed.append(name)
            require_idle()
        for f in source['files']:
            if file_sha(W/f['path'])!=f['sha256']:
                raise RuntimeError('source changed during experiment: '+f['path'])
        paired=paired_rows(summaries)
        put(D/'SUMMARY.json',dict(status='COMPLETE_DEVELOPMENT_RECOVERY_PILOT',expected=len(plan),
            completed=completed,rows=summaries,pairs=paired))
        put(D/'GATE.json',dict(gate='RECOVERY_PILOT_RECORDED_PENDING_INDEPENDENT_REVIEW',
            exact_fault_cut_pairs=sum(r['exact_fault_cut_match'] for r in paired),total_pairs=len(paired),
            statistical_superiority='NOT_ESTABLISHED_BY_PILOT',GPU_workers_released=True,
            source_commit=source['code_commit']))
    except BaseException:
        put(D/'STOP.json',dict(status='FAILED_PRESERVED',completed=completed,error=traceback.format_exc()))
        raise


if __name__=='__main__':
    main()
