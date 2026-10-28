"""Frozen controlled interleaving, never a normal-serving performance method.

Complete actual FP32 A6 is held until P8 has really completed under the old
private chain. A6 is then installed before the same unmodified P8 delivery.
The optional coherent P6 corruption is separately tagged synthetic content;
subsequent P8 is genuine GPU consumption. No new Canonical permission.
"""
from .kernel_runtime import KernelEnvelopeScheduler
from .certified_display import validate_bound_text
from .dgft import digest_tokens

class ProbeKernelScheduler(KernelEnvelopeScheduler):
    def __init__(self,**kw):
        self.held={};self.registered=set();self.released=False;self.probe_witnesses=[];self.channel=None
        super().__init__(**kw)
        if self.contract['controlled_boundary_probe']=='coherent':
            from kernel_role_channel import OwnProposerChannel
            tok=self.trusted_render.tokenizer;eos=sorted(self.trusted_render.eos)
            payload=tok.encode(' Violet Saturn Alder crossed the quiet bridge before the afternoon bell.',add_special_tokens=False)+[eos[0]]
            # Each source has its own one-shot role capability, implemented
            # by one channel per session only in the bounded probe executor.
            p=self.executors['proposal'][0]
            self.channel=OwnProposerChannel(p.results,worker_name=p.name,job_lookup=lambda jid:self.jobs[jid],
                target_window=3,build_tokens=lambda j:payload,render=self.trusted_render,eos=eos,budget=256)
            p.results=self.channel
    def protocol_row(self,name,job,result):
        if job['job_id'] in self.registered:return
        super().protocol_row(name,job,result);self.registered.add(job['job_id'])
    def _accept_result(self,name,result):
        j=self.jobs[result['job_id']]
        if j['role']=='proposal' and j['end_window']==4 and not self.released:
            # Retain native result identity; no newly executed/rewritten P8.
            result['text_binding']=validate_bound_text(self.trusted_render,j,result)
            self.protocol_row(name,j,result)
            self.held[j['session_id']]=(name,result)
            self._event('controlled-P8-delivery-held',session_id=j['session_id'],job_id=j['job_id'])
            return
        return super()._accept_result(name,result)
    def _commit_ready(self):
        if not self.released:
            # First establish real nonempty canonical parents through 4s.
            # The controlled A6/P8 interleaving is then on the feedback path,
            # not an empty-history demonstration.
            if any(s.state.audio_frontier_window<64000 for s in self.sessions.values()):
                return super()._commit_ready()
            if len(self.held)!=len(self.sessions) or not all(s.auth_result for s in self.sessions.values()):return
            comparisons=[]
            for sid,s in self.sessions.items():
                p6=self._proposal_results[sid,3]
                comparisons.append(dict(session_id=sid,P6_equals_A6=p6['state_tokens']==s.auth_result['state_tokens'],
                    P6_sha256=digest_tokens(p6['state_tokens']),A6_sha256=digest_tokens(s.auth_result['state_tokens'])))
            super()._commit_ready();self.released=True
            for sid,(name,r) in self.held.items():
                super()._accept_result(name,r)
            self.probe_witnesses.extend(comparisons)
        else:super()._commit_ready()
    def probe_report(self):
        return dict(scope='controlled actual GPU A6/P8 completion interleaving; not natural rate or normal SLO',
            released=self.released,witnesses=self.probe_witnesses,
            coherent_injection=self.channel.transforms if self.channel else [],
            original_physical_accounting=self.channel.original_physical_accounting if self.channel else [],
            no_private_canonical_authority=True)
