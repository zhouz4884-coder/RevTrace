"""Timing-only observer for unchanged NN4f protocol functions.

No safety predicate, result, exception, durability setting or clock is changed.
Spans stay in RAM and are exported after the original entry point terminates.
Inclusive process CPU may include other threads: only same-thread child spans
are subtracted for exclusive thread CPU / wall. Blocking is never called lock
wait, and these measurements are not a counterfactual protocol-removal tax.
"""
from __future__ import annotations
import collections
import functools
import itertools
import json
import os
import pathlib
import threading
import time


class CostProbe:
    def __init__(self, out, role, enabled=True, max_spans=1000000):
        self.out = pathlib.Path(out)
        self.role = role
        self.enabled = bool(enabled)
        self.max_spans = max_spans
        self.rows = []
        self.counter = itertools.count(1)
        self.local = threading.local()
        self.restore = []
        self.overflow = False
        self.closed = False

    def wrap(self, owner, name, label):
        original = getattr(owner, name)
        if not self.enabled:
            return
        probe = self
        @functools.wraps(original)
        def observed(*args, **kwargs):
            stack = getattr(probe.local, 'stack', None)
            if stack is None:
                stack = probe.local.stack = []
            ident = next(probe.counter)
            parent = stack[-1] if stack else None
            frame = dict(id=ident, child_wall=0, child_thread=0)
            stack.append(frame)
            # Metadata access is deliberately outside this span, but remains
            # inside the caller's inclusive span and the actual off/on trial.
            meta = {}
            if args:
                obj = args[0]
                if hasattr(obj, 'f') and hasattr(obj.f, 'name'):
                    meta['file_name'] = pathlib.Path(str(obj.f.name)).name
                    meta['journal_fsync_enabled'] = getattr(obj, 'fsync', None)
            failed = False
            t0, p0, w0 = time.thread_time_ns(), time.process_time_ns(), time.perf_counter_ns()
            try:
                return original(*args, **kwargs)
            except BaseException:
                failed = True
                raise
            finally:
                w1, p1, t1 = time.perf_counter_ns(), time.process_time_ns(), time.thread_time_ns()
                stack.pop()
                wall, thread = w1-w0, t1-t0
                if parent:
                    parent['child_wall'] += wall
                    parent['child_thread'] += thread
                row = dict(span_id=ident, parent_span_id=parent['id'] if parent else None,
                           label=label, role=probe.role, pid=os.getpid(),
                           thread_id=threading.get_ident(), start_ns=w0, end_ns=w1,
                           wall_ns=wall, thread_cpu_ns=thread, process_cpu_ns=p1-p0,
                           exclusive_wall_ns=max(0, wall-frame['child_wall']),
                           exclusive_thread_cpu_ns=max(0, thread-frame['child_thread']),
                           exclusive_wall_negative_before_clamp=(wall-frame['child_wall']<0),
                           exclusive_thread_negative_before_clamp=(thread-frame['child_thread']<0),
                           exception=failed, **meta)
                if len(probe.rows) < probe.max_spans:
                    probe.rows.append(row)
                else:
                    probe.overflow = True
        self.restore.append((owner, name, original))
        setattr(owner, name, observed)

    def install(self):
        import feedback_contract as fc
        import fullspec_policy as fp
        import stage_policy as sp
        import native_service as ns
        import resilience_policy as rp
        import resilience_inbound as ri
        import resilience_storage as rs
        import resilience_consumer as rc
        targets = [
            (fp.FullSpecCoordinator, 'next_full_start', 'EL.next_full_start'),
            (fp.FullSpecCoordinator, '_dependencies', 'EL.frozen_dependencies'),
            (fp.FullSpecCoordinator, '_reason', 'EL.refutation_or_coverage'),
            (fp.FullSpecCoordinator, '_refresh_active', 'EL.confirmation_scan'),
            (rp.ResilientFullSpecCoordinator, 'register', 'IDENTITY.register_original_job'),
            (ri.ResilientInbound, 'classify', 'IDENTITY.classify_bound_message'),
            (sp.StageCoordinator, 'bind', 'IDENTITY.bind_owned_original_call'),
            (rp.ResilientFullSpecCoordinator, 'receive_event', 'OWNER.receive_validate_select'),
            (sp.StageCoordinator, 'admit_asr', 'EL.admit_original_ASR_projection'),
            (fp.FullSpecCoordinator, 'complete', 'AU.bind_complete_original_result'),
            (rp.ResilientFullSpecCoordinator, '_commit', 'AU.durable_selected_commit'),
            (fp.FullSpecCoordinator, '_commit', 'AU.install_after_durable'),
            (rs.FactStore, '_validate_transition', 'AU.validate_original_C_U_and_parent'),
            (rs.FactStore, 'commit', 'WAL.complete_fact_commit'),
            (rs.FactStore, '_append', 'WAL.encode_write_flush_sync'),
            (rs, 'verify_frame', 'AU.verify_durable_frame'),
            # Consumer imports this function by value, so bind its alias too.
            (rc, 'verify_frame', 'AU.verify_durable_frame'),
            (rc.SurvivorConsumer, '_fact', 'CONSUMER.durable_fact_binding'),
            (rc.SurvivorConsumer, 'apply', 'SUP.complete_consumer_apply'),
            (rc.SurvivorConsumer, 'replay_fact', 'CONSUMER.replay_existing_fact'),
            (fc.Reconciler, 'install', 'SUP.complete_view_install'),
            (fc.Reconciler, 'append', 'SUP.append_whole_dependency_step'),
            (ns.Journal, 'write', 'IO.original_journal_write'),
            (os, 'fsync', 'IO.actual_os_fsync'),
        ]
        for owner, name, label in targets:
            self.wrap(owner, name, label)
        return self

    def close(self):
        if self.closed:
            return
        self.closed = True
        for owner, name, original in reversed(self.restore):
            setattr(owner, name, original)
        export_start_ns = time.perf_counter_ns()
        self.out.mkdir(parents=True, exist_ok=True)
        stem = f'{self.role}_pid{os.getpid()}'
        with (self.out/(stem+'.jsonl')).open('x', encoding='utf8') as handle:
            for row in self.rows:
                handle.write(json.dumps(row, separators=(',', ':'))+'\n')
        by = collections.defaultdict(list)
        for row in self.rows:
            by[row['label']].append(row)
        summary = dict(role=self.role, pid=os.getpid(), enabled=self.enabled,
                       span_count=len(self.rows), overflow=self.overflow,
                       negative_exclusive_wall_before_clamp=sum(r['exclusive_wall_negative_before_clamp'] for r in self.rows),
                       negative_exclusive_thread_before_clamp=sum(r['exclusive_thread_negative_before_clamp'] for r in self.rows),
                       export_after_original_entry_return=True,
                       export_start_ns=export_start_ns,
                       owner_export_precedes_supervisor_service_end=(self.role == 'owner'),
                       process_cpu_is_inclusive_and_may_include_background_threads=True,
                       explicit_protocol_lock_wait_measured=False,
                       wall_minus_thread_cpu_is_unattributed_not_lock_wait=True,
                       families={key: dict(count=len(rows),
                           inclusive_wall_ns=sum(x['wall_ns'] for x in rows),
                           inclusive_thread_cpu_ns=sum(x['thread_cpu_ns'] for x in rows),
                           exclusive_wall_ns=sum(x['exclusive_wall_ns'] for x in rows),
                           exclusive_thread_cpu_ns=sum(x['exclusive_thread_cpu_ns'] for x in rows),
                           exceptions=sum(x['exception'] for x in rows))
                           for key, rows in by.items()})
        summary['span_file_bytes'] = (self.out/(stem+'.jsonl')).stat().st_size
        summary['export_end_ns_before_summary_write'] = time.perf_counter_ns()
        (self.out/(stem+'_SUMMARY.json')).write_text(json.dumps(summary, indent=2), encoding='utf8')
        if self.overflow:
            raise RuntimeError('cost observer span limit exceeded; timing study invalid')

