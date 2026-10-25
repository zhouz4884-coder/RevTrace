"""Post-compute delivery ordering, not model delay or a serving optimization.

The broker copies completed payloads, frees physically drained worker leases,
and changes only when the owner receives selected results. Selection is fixed
by role/window/session before execution, never by generated content.
"""
from __future__ import annotations
import hashlib
import json
from .live_qwen import LiveQwenScheduler, fingerprint


class PostComputeOrder:
    def __init__(self, scheduler, config):
        self.s=scheduler; self.config=dict(config)
        self.p=int(config['proposal_window']); self.a=int(config['authority_window'])
        self.sids=set(map(int,config['sessions']))
        self.order=config['order']; self.phase='collect'; self.rows={}
        self.started=None; self.completed=False
        if not self.sids or self.p<1 or self.a<1 or self.order not in ['proposal_first','authority_first']:
            raise ValueError('invalid frozen completed-result ordering')
        if any(sid not in scheduler.sessions for sid in self.sids):raise ValueError('unknown target session')
        if scheduler.contract.get('proposal_barrier')!='decoupled':raise ValueError('ordering requires independent lanes')
        if scheduler.contract.get('result_delivery','batch')!='batch':raise ValueError('N1 freezes physical batch return')
        for sid in self.sids:
            if scheduler.sessions[sid].duration < max(self.p,self.a)*scheduler.fine:
                raise ValueError('target outside released audio schedule')

    def offer(self, worker, result):
        j=self.s.jobs[result['job_id']]
        target=self.p if j['role']=='proposal' else self.a
        if j['session_id'] not in self.sids or j['end_window']!=target:
            return [(worker,result)]
        key=j['role'],j['session_id']
        if key in self.rows:raise AssertionError('duplicate completed target')
        if self.phase!='collect':raise AssertionError('target after release')
        raw=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if self.started is None:self.started=self.s.clock()
        self.rows[key]=(worker,raw,hashlib.sha256(raw).hexdigest(),self.s.clock())
        self.s._event('ipc-complete-captured',job_id=j['job_id'],session_id=j['session_id'],role=j['role'],
            target_window=target,payload_sha256=self.rows[key][2],
            frozen_job_sha256=fingerprint(j),worker_completed=result['completed_perf']-self.s.t0,
            physically_drained=worker not in self.s.inflight,order=self.order)
        self.s._event('ipc-complete-payload',worker=worker,job=dict(j),result=json.loads(raw))
        return []

    def _take(self, role):
        out=[]
        for sid in sorted(self.sids):
            worker,raw,sha,captured=self.rows[role,sid]
            if hashlib.sha256(raw).hexdigest()!=sha:raise AssertionError('completed payload mutated')
            r=json.loads(raw);j=self.s.jobs[r['job_id']];s=self.s.sessions[sid]
            self.s._event('ipc-complete-delivered',job_id=j['job_id'],session_id=sid,role=role,
                payload_sha256=sha,hold_seconds=self.s.clock()-captured,
                committed_frontier=s.state.audio_frontier_window,current_parent=s.state.checkpoint_id,
                birth_parent=j['parent'],job_generation=j.get('branch_generation'),
                active_generation=s.branch_generation,order=self.order)
            out.append((worker,r))
        return out

    def drain(self):
        if self.completed:return []
        if self.started is not None and self.s.clock()-self.started>float(self.config.get('timeout_seconds',45)):
            raise TimeoutError('completed-result order targets not jointly available; retain negative run')
        if self.phase=='collect' and len(self.rows)==2*len(self.sids):
            if self.order=='proposal_first':
                self.completed=True;self.phase='done'
                return self._take('proposal')+self._take('authority')
            self.phase='wait-for-commit'
            return self._take('authority')
        if self.phase=='wait-for-commit':
            ready=all(self.s.sessions[sid].state.audio_frontier_window >=
                self.s.jobs[json.loads(self.rows['authority',sid][1])['job_id']]['audio_end_sample'] for sid in self.sids)
            if ready:
                self.completed=True;self.phase='done'
                return self._take('proposal')
        return []


class LateDeliveryScheduler(LiveQwenScheduler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        config=self.contract.get('post_compute_order')
        self._order=PostComputeOrder(self,config) if config else None

    def _receive(self):
        # Physical transport validation/lease release is identical to base.
        if self._order:
            for worker,result in self._order.drain():self._accept_result(worker,result)
        for name,(worker,ids) in list(self.inflight.items()):
            results=worker.poll()
            if hasattr(worker,'drain_telemetry'):
                for item in worker.drain_telemetry():
                    self._event('worker-status',worker=name,status=item['kind'],
                        **{k:v for k,v in item.items() if k!='kind'})
            if results is None:continue
            if getattr(worker,'row_delivery',False):
                if not {r['job_id'] for r in results}.issubset(set(ids)):
                    raise AssertionError('partial row is outside leased batch')
                if worker.batch_drained:del self.inflight[name]
            else:
                if sorted(r['job_id'] for r in results)!=sorted(ids):raise AssertionError('executor result set mismatch')
                del self.inflight[name]
            for result in results:
                for origin,row in self._order.offer(name,result) if self._order else [(name,result)]:
                    self._accept_result(origin,row)
        if self._order:
            for worker,result in self._order.drain():self._accept_result(worker,result)

    def run(self):
        result=super().run()
        if self._order and not self._order.completed:raise AssertionError('frozen ordering not exercised')
        result['post_compute_order_completed']=bool(self._order and self._order.completed)
        return result
