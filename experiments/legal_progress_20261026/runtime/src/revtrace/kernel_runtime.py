"""Full N5 integration; receipts are issued at actual trusted boundaries."""
from copy import deepcopy
from .certified_envelope import CertifiedEnvelopeScheduler
from .envelope_display import EnvelopeView
from .composed_kernel import Kernel,sha,Denied
from .dgft import digest_tokens
from .certified_display import text_sha

def fact(state,text):
    return dict(v=state.checkpoint_id,F=state.audio_frontier_window,P=digest_tokens(state.prompt_tokens),
        Z=digest_tokens(state.stable_token_segments[-1]) if state.stable_token_segments else '',
        textsha=text_sha(text),txn=state.committed_segment_ids[-1] if state.committed_segment_ids else '')

def input_items(snapshot):
    return {int(sid):dict(accepted=s['accepted'],offered=s['offered'],reserved=s['reserved'],
        prefix=s['accepted_prefix_sha256'],origin=snapshot['origin_perf'])
        for sid,s in snapshot['sessions'].items()}

class KernelView(EnvelopeView):
    """Native adapter-independent two-lane decision followed by kernel gate.

    Evaluate on a private copy first. The actual view is replaced only after
    the kernel authorizes the application, then a distinct applied receipt is
    emitted. The kernel validates actual causal nodes, not a caller boolean.
    """
    def __init__(self,kernel,fine_samples=32000):
        super().__init__(policy='two_lane',strict_bound=True,fine_samples=fine_samples)
        self.kernel=kernel
    def consume(self,e,observed=None):
        if e['kind'] not in ['display','canonical-display','view-mode']:
            return super().consume(e,observed)
        with self.kernel.lock:
            preview=getattr(self,'preview_factory',EnvelopeView)(policy=self.policy,strict_bound=self.strict_bound,fine_samples=self.fine)
            for name in ['states','commits','epoch','contract','modes']:
                setattr(preview,name,deepcopy(getattr(self,name)))
            row=preview.consume(e,observed)
            if row is None:return None
            sid=row['session_id'];s=preview.states[sid]
            # view-mode is a withdrawal-only effect, never a new selection.
            key=(sid,e['display_revision'])
            if e['kind']=='view-mode':
                c=self.kernel.state.C[sid]
                self.kernel.event('owner-mode','publish',str(key),dict(sid=sid,key=key,
                    publication=dict(mode=True,canonical=False)))
            view=dict(v=s['version'],F=s['F'],P=s.get('Psha',digest_tokens(())),
                visible=s['visible'],text=s['visible_text'],revision=s['revision'],
                private=s['tentative']['job_id'] if s.get('tentative') else None)
            op='apply:'+str(key)
            self.kernel.event('consumer','apply-request',op,dict(sid=sid,key=key,view=view,operation=op,
                epoch=e['contract_epoch'],contract=e['contract_digest'],owner=self.epoch))
            for name in ['states','commits','epoch','contract','modes']:
                setattr(self,name,getattr(preview,name))
            self.records.append(row)
            self.kernel.event('consumer','view-applied',op,dict(operation=op))
            return row

class KernelEnvelopeScheduler(CertifiedEnvelopeScheduler):
    def __init__(self,**kwargs):
        self.kernel=None
        original_emit=kwargs['emit'];buffer=[]
        kwargs['emit']=buffer.append
        super().__init__(**kwargs)
        # Genesis sessions may not have published during base WAL replay.
        for s in self.sessions.values():self._recover_session(s)
        snap=self.book.snapshot(self.origin)
        self.kernel.event('input-replay','input-synced','recover-input',
            dict(items=input_items(snap),recovery=True))
        self.consumer.view=getattr(self,'consumer_view_factory',KernelView)(self.kernel,round(self.fine*self.sample_rate))
        self.emit=original_emit
        for row in buffer:original_emit(row)
        self._wrap_journals()

    def _recover_session(self,s):
        if self.kernel is None:self.kernel=Kernel(self.contract_digest,s.state.contract_epoch,self.t0,
            incremental=self.contract.get('kernel_copy_mode','deep')=='event-cow')
        if s.sid not in self.kernel.state.C:
            history={}
            for e in self._journal.events():
                if e.get('event')=='canonical-segment-committed' and e['session_id']==s.sid:
                    c=e['certificate']
                    history[e['checkpoint_id']]=dict(v=e['checkpoint_id'],F=e['audio_end_sample'],
                        P=c['feedback_state_sha256'],Z=c['display_sha256'],
                        textsha=e['text_binding']['text_sha256'],txn=e['segment_id'])
            self.kernel.event('validated-WAL-replay','recover-fact','recover:'+str(s.sid),
                dict(sid=s.sid,fact=fact(s.state,s.text),history=history))
    def _publish_display(self,s,**kw):
        self._recover_session(s)
        key=(s.sid,s.display_revision+1)
        pub=dict(canonical=kw['canonical'])
        if kw['canonical']:pub['fact']=fact(s.state,kw['text'])
        else:pub.update(job=kw['job_id'],end=kw['frontier'],textsha=text_sha(kw['text']))
        self.kernel.event('owner-publication','publish',str(key),dict(sid=s.sid,key=key,publication=pub))
        return super()._publish_display(s,**kw)
    def execution_ready(self,worker):
        if worker.ready is None:raise Denied('missing actual worker ready receipt')
        self.kernel.event('worker-ready-queue','worker-ready',worker.name,dict(worker=worker.name))
    def protocol_dispatch(self,worker,jobs):
        normalized=[]
        for j in jobs:
            normalized.append(dict(id=j['job_id'],sid=j['session_id'],role=j['role'],
                parent=j['parent'],start=j['audio_start_sample'],end=j['audio_end_sample'],
                rootF=round(j['chunk_id']*self.fine*self.sample_rate),inputP=digest_tokens(j['prompt_tokens']),
                identity=sha({k:v for k,v in j.items() if k!='_delivery'})))
        self.kernel.event('frozen-dispatch','dispatch',worker.name,dict(worker=worker.name,jobs=normalized))
    def protocol_row(self,name,job,result):
        binding=result.get('_row_receipt',{}).get('binding',{})
        self.kernel.event('row-inbox-and-trusted-render','row-complete',job['job_id'],dict(
            id=job['job_id'],worker=name,identity=sha({k:v for k,v in job.items() if k!='_delivery'}),
            epoch=binding.get('contract_epoch',job['contract_epoch']),
            contract=binding.get('contract_digest',job['contract_digest']),
            P=digest_tokens(result['state_tokens']),Z=digest_tokens(result['token_ids']),
            textsha=result['text_binding']['text_sha256']))
    def protocol_drain(self,worker):
        self.kernel.event('batch-drained-inbox','batch-drained',worker.name,dict(worker=worker.name))
    def protocol_install(self,s,result,job,txn,next_state):
        self.kernel.event('owner-install','install',txn,dict(sid=s.sid,fact=fact(next_state,result['text'])))
    def _wrap_journals(self):
        original_checkpoint=self.input_journal.checkpoint
        def checkpoint(snapshot):
            items=input_items(snapshot);op='input:'+sha(items)
            self.kernel.event('input-journal','input-sync-request',op,dict(items=items))
            receipt=original_checkpoint(snapshot)  # actual fsync then swap
            self.kernel.event('input-journal','input-synced',op,dict(items=items))
            return receipt
        self.input_journal.checkpoint=checkpoint
        original=self._journal.commit_transitions
        def commit_transitions(transitions):
            operations=[]
            for t in transitions:
                e=t['event'];sid=t['session_id'];job=self.sessions[sid].auth_result['job_id']
                op='wal:'+t['transaction_id'];operations.append(op)
                self.kernel.event('canonical-journal','admission-request',op,dict(sid=sid,job=job,
                    operation=op,fact=fact(t['next_state'],e['committed_text'])))
            receipts=original(transitions)  # real framed writes/fsync/replay
            for op in operations:self.kernel.event('canonical-journal','canonical-synced',op,dict(operation=op))
            return receipts
        self._journal.commit_transitions=commit_transitions
        self._journal.commit_transition=lambda **t:commit_transitions([t])[0]
    def _tick(self):
        super()._tick()
        for sid,s in self.sessions.items():
            if self.book.session(sid).accepted!=self.kernel.state.I[sid]['accepted']:
                raise Denied('input dispatch book/kernel diverged')
