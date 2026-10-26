"""Controlled own-Proposer IPC corruption; never edits Authority or job bindings.

This helper performs no neural inference and supplies no Canonical permission.
Caller must retain original worker facts and report corruption as an injection.
"""
import copy,hashlib,json
from dataclasses import asdict,replace
from revtrace.dgft import digest_tokens
from revtrace.row_lifecycle import RowComplete

class OwnProposerChannel:
    def __init__(self,underlying,*,worker_name,job_lookup,target_window,build_tokens,render,eos,budget=256):
        self.underlying=underlying;self.worker=worker_name;self.job_lookup=job_lookup
        self.target_window=target_window;self.build_tokens=build_tokens;self.render=render;self.eos=set(eos);self.budget=budget
        self.applied=False;self.replacements={};self.corrupted_messages={};self.original_digests={};self.transforms=[];self.original_physical_accounting=[]
    def get(self,*a,**kw):return self.transform(self.underlying.get(*a,**kw))
    def get_nowait(self):return self.transform(self.underlying.get_nowait())
    def transform(self,item):
        if item['kind']=='row-complete':
            m=item['message'];b=m.binding
            if b.worker!=self.worker or b.role!='proposal':raise ValueError('capability excludes other workers/Authority')
            j=self.job_lookup(b.job_id)
            if (j['job_id'],j['role'],j['session_id'],j['parent'],j['audio_end_sample'])!=(b.job_id,'proposal',b.session_id,b.parent,b.audio_end_sample):
                raise ValueError('frozen own-job identity mismatch')
            if b.job_id in self.corrupted_messages:
                if m.payload_digest!=self.original_digests[b.job_id]:raise ValueError('conflicting duplicate source result')
                return dict(item,message=self.corrupted_messages[b.job_id])
            if self.applied or j['end_window']!=self.target_window or j['session_id']!=0:return item
            if j['chunk_id']<2:raise ValueError('target does not exercise actual feedback rollback path')
            original=m.decode();Z=list(self.build_tokens(j))
            if not Z or len(Z)>self.budget:raise ValueError('payload outside complete token budget')
            stops=[i for i,t in enumerate(Z) if t in self.eos]
            if stops!=[len(Z)-1]:raise ValueError('fixed payload must terminate with one declared EOS')
            P,Y=self.render(j,Z);modified=copy.deepcopy(original)
            modified.update(token_ids=Z,state_tokens=list(P),text=Y,generated_tokens=len(Z),hit_token_limit=False,terminated_by_eos=True)
            allowed={'token_ids','state_tokens','text','generated_tokens','hit_token_limit','terminated_by_eos'}
            assert all(modified.get(k)==v for k,v in original.items() if k not in allowed)
            # Original clocks denote genuine worker emission before in-transit
            # corruption. We do not claim the transformedZ was GPU-generated.
            changed=RowComplete.seal(b,modified,terminal=m.terminal_perf,rendered=m.rendered_perf,emitted=m.emitted_perf)
            self.replacements[b.job_id]=changed.payload_digest;self.applied=True
            self.corrupted_messages[b.job_id]=changed;self.original_digests[b.job_id]=m.payload_digest
            self.transforms.append(dict(job=copy.deepcopy(j),original_message=asdict(m),corrupted_message=asdict(changed),
                interpretation='controlled own-Proposer channel corruption, not new neuralZ or a trusted Authority selection'))
            return dict(item,message=changed)
        if item['kind']=='batch-drained':
            m=item['message']
            if m.worker!=self.worker:raise ValueError('capability excludes foreign batch')
            out=copy.deepcopy(item);self.original_physical_accounting.append(copy.deepcopy(item['physical_accounting']))
            out['message']=replace(m,row_digests=tuple((j,self.replacements.get(j,d)) for j,d in m.row_digests))
            a=out['physical_accounting']
            for jid in a['row_receipt_digests']:
                if jid in self.replacements:a['row_receipt_digests'][jid]=self.replacements[jid]
            for selected in a['selected_output_digests']:
                matching=[t for t in self.transforms if t['job']['job_id']==selected['job_id']]
                if matching:
                    body=json.loads(matching[0]['corrupted_message']['payload_json'])
                    selected.update(Z_sha256=digest_tokens(body['token_ids']),P_sha256=digest_tokens(body['state_tokens']),
                        text_sha256=hashlib.sha256(body['text'].encode()).hexdigest(),generated_tokens=len(body['token_ids']),
                        hit_token_limit=False,terminated_by_eos=True)
            # Preserve actual physical clocks/phases/row set; retain original
            # model-selected digests separately for true work accounting.
            return out
        return item
