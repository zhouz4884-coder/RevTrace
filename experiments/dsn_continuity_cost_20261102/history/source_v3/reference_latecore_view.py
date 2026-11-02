"""Verbatim latecore CPU reference definitions; see LATECORE_PROVENANCE.json."""
from __future__ import annotations
import hashlib, json, time, queue, threading, re, heapq
from hashlib import sha256
from typing import Sequence
def digest_tokens(values: Sequence[int]) -> str:
    payload = ",".join(str(int(value)) for value in values).encode("ascii")
    return sha256(payload).hexdigest()

def text_sha(text):return hashlib.sha256(text.encode('utf8')).hexdigest()

class ContinuityView:
    """Trusted single-owner FIFO stream, independently versioned certified lane.

    A compatible whole provisional hypothesis is NEVER a certified suffix.
    Exact text-state equality at the same audio boundary and a complete causal
    chain permit only a provisional view. No token/audio alignment is inferred.
    """
    def __init__(self,policy='snapshot',fine_samples=32000,strict_bound=False):
        self.policy=policy;self.fine=fine_samples;self.states={};self.commits={};self.epoch=None;self.records=[];self.strict_bound=strict_bound;self.contract=None
    def consume(self,e,observed=None):
        kind=e['kind']
        if kind=='run-start':
            self.epoch=e.get('t0_perf');self.contract=e.get('contract_digest');self.states={};self.commits={};return
        sid=e.get('session_id')
        if kind=='commit':
            if self.strict_bound and e['certificate']['contract_digest']!=self.contract:raise ValueError('commit belongs to another declared contract')
            self.commits[sid,e['version']]=e;return
        if kind not in ['display','canonical-display']:return
        s=self.states.setdefault(sid,{'version':0,'F':0,'text':'','visible':0,'visible_text':'','nodes':{},'tentative':None,'buffer':[],'revision':0})
        if self.strict_bound and (e.get('contract_digest')!=self.contract or 'contract_epoch' not in e):raise ValueError('missing/wrong publication contract or epoch')
        incoming_epoch=e.get('contract_epoch',s.get('epoch'))
        if s.get('epoch') is not None and incoming_epoch!=s['epoch']:
            if incoming_epoch<s['epoch']:return
            raise ValueError('new epoch requires a fresh declared FIFO stream')
        if kind=='display' and e.get('canonical_version',e.get('version',0))<s['version']:return
        s['epoch']=incoming_epoch
        if e.get('display_revision',0)<=s['revision']:return
        before=s['visible'];oldtext=s['visible_text'];s['revision']=e.get('display_revision',s['revision']+1);retained=False;invalid=False
        if kind=='canonical-display':
            version=e['version']
            if version<s['version']:return
            if not e.get('recovered'):
                commit=self.commits.get((sid,version))
                if commit is None or commit['segment_id']!=e['transaction_id'] or commit['audio_end_sample']!=e['audio_end_sample']:raise ValueError('uninstalled canonical display')
                if e.get('canonical_projection_sha256') not in (None,digest_tokens(commit['next_prompt_tokens'])):raise ValueError('canonical P mismatch')
                if self.strict_bound and e.get('canonical_Z_sha256')!=commit['certificate']['display_sha256']:raise ValueError('canonical selected Z mismatch')
            if e.get('text_sha256') not in (None,text_sha(e['text'])):raise ValueError('canonical text binding mismatch')
            s.update(version=version,F=e['audio_end_sample'],text=e['text'],Psha=e.get('canonical_projection_sha256'),Zsha=e.get('canonical_Z_sha256'),transaction=e.get('transaction_id'),textsha=e.get('text_sha256'),buffer=[],stable_text=e['text'])
            tent=s['tentative']
            retained=bool(self.policy=='two_lane' and tent and tent['audio_end_sample']>s['F'] and self._compatible(s,tent,e.get('canonical_projection_sha256')))
            invalid=bool(tent and not retained)
            if retained:s.update(visible=tent['audio_end_sample'],visible_text=tent['text'])
            else:s.update(visible=s['F'],visible_text=s['text'],tentative=None)
        else:
            if e.get('canonical_version',e.get('version',0))<s['version'] or e['audio_end_sample']<=s['F']:return
            s['nodes'][e['job_id']]=e
            check_private=(self.policy=='checked_snapshot' or self.policy=='two_lane' and s['version'])
            root=s.get('Psha') or (digest_tokens(()) if s['version']==0 else None)
            if check_private and not self._compatible(s,e,root):
                invalid=True;s.update(visible=s['F'],visible_text=s['text'],tentative=None)
            elif self.policy.startswith('localagreement'):
                n=int(self.policy[-1]);s['buffer'].append(e['text']);s['buffer']=s['buffer'][-n:]
                text=s.get('stable_text',s['text'])
                if len(s['buffer'])==n:
                    # Credited LocalAgreement-n display adaptation: complete
                    # words for English, codepoints for no-whitespace CJK.
                    cjk=any('\u4e00'<=ch<='\u9fff' for ch in e['text'])
                    units=[list(t) if cjk else re.findall(r'\S+',t) for t in s['buffer']]
                    common=0
                    for group in zip(*units):
                        if len(set(group))!=1:break
                        common+=1
                    if cjk:candidate=e['text'][:common]
                    else:
                        spans=list(re.finditer(r'\S+',e['text']));candidate=e['text'][:spans[common-1].end()] if common else ''
                    # Never blank/withdraw the current confirmed view merely
                    # because a fresh buffer is not yet in agreement. Only an
                    # actual canonical correction can override that view.
                    if candidate.startswith(text):text=candidate
                s['stable_text']=text
                # Without word/audio alignment a partial stable prefix cannot
                # claim the entire source interval as legally displayed.
                s.update(visible=s['F'],visible_text=text,tentative=e)
            elif self.policy=='canonical_only':return
            else:s.update(visible=e['audio_end_sample'],visible_text=e['text'],tentative=e)
        common=0
        for a,b in zip(oldtext,s['visible_text']):
            if a!=b:break
            common+=1
        row={'kind':'consumer-view','source_kind':kind,'session_id':sid,'server_time':e.get('displayed',e['time']),'observed_perf':observed,'owner_incarnation':self.epoch,'contract_digest':self.contract,'canonical_epoch':s.get('epoch'),'canonical_version':s['version'],'certified_transaction':s.get('transaction'),'certified_Z_sha256':s.get('Zsha'),'certified_P_sha256':s.get('Psha'),'certified_text_sha256':s.get('textsha'),'certified_frontier':s['F'],'certified_text':s['text'],'valid_visible_frontier':s['visible'],'visible_text':s['visible_text'],'audio_rollback_samples':max(0,before-s['visible']),'erased_characters':len(oldtext)-common,'compatible_provisional_retained':retained,'tentative_invalidated':invalid,'joined_suffix':False,'policy':self.policy}
        self.records.append(row);return row
    def _compatible(self,s,node,Psha):
        if not Psha:return False
        seen=set()
        while node['job_id'] not in seen:
            seen.add(node['job_id']);chunk=node.get('chunk_id');inp=node.get('input_projection_sha256')
            if chunk is None or inp is None:return False
            if chunk==round(s['F']/self.fine) and inp==Psha:return True
            candidates=[p for p in s['nodes'].values() if p.get('end_window')==chunk and p.get('output_projection_sha256')==inp and p['audio_end_sample']>=s['F'] and p['audio_end_sample']<node['audio_end_sample'] and p.get('branch_generation')==node.get('branch_generation')]
            if len(candidates)!=1:return False
            node=candidates[0]
            if node['audio_end_sample']==s['F']:return node.get('output_projection_sha256')==Psha
        return False

class EnvelopeView(ContinuityView):
    MODES={'NORMAL','DEGRADED','CERTIFIED-ONLY','BACKPRESSURE/REJECT','RECOVERY'}
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self.modes={}
    def consume(self,e,observed=None):
        sid=e.get('session_id');kind=e['kind']
        if kind=='run-start':self.modes={}
        if kind=='view-mode':
            if e['mode'] not in self.MODES or e.get('contract_digest')!=self.contract:
                raise ValueError('undeclared or unauthenticated view mode')
            s=self.states.setdefault(sid,dict(version=0,F=0,text='',visible=0,visible_text='',
                nodes={},tentative=None,buffer=[],revision=0))
            if s.get('epoch') is not None and e['contract_epoch']!=s['epoch']:
                if e['contract_epoch']<s['epoch']:return None
                raise ValueError('view mode cannot switch epoch without new stream')
            if e['display_revision']<=s['revision']:return None
            s['epoch']=e['contract_epoch'];s['revision']=e['display_revision']
            before=s['visible'];old=s['visible_text'];self.modes[sid]=e['mode']
            if e['mode'] in ['CERTIFIED-ONLY','RECOVERY']:
                s.update(visible=s['F'],visible_text=s['text'],tentative=None,buffer=[])
            common=0
            for a,b in zip(old,s['visible_text']):
                if a!=b:break
                common+=1
            r=dict(kind='consumer-view',source_kind=kind,session_id=sid,
                server_time=e['displayed'],observed_perf=observed,owner_incarnation=self.epoch,
                contract_digest=self.contract,canonical_epoch=s['epoch'],canonical_version=s['version'],
                certified_transaction=s.get('transaction'),certified_Z_sha256=s.get('Zsha'),
                certified_P_sha256=s.get('Psha'),certified_text_sha256=s.get('textsha'),
                certified_frontier=s['F'],certified_text=s['text'],valid_visible_frontier=s['visible'],
                visible_text=s['visible_text'],audio_rollback_samples=max(0,before-s['visible']),
                erased_characters=len(old)-common,compatible_provisional_retained=False,
                tentative_invalidated=before>s['F'] and s['visible']==s['F'],joined_suffix=False,
                policy=self.policy,envelope_mode=e['mode'],no_certified_snapshot_yet=s['version']==0)
            self.records.append(r);return r
        mode=self.modes.get(sid,'NORMAL')
        if kind=='display' and mode in ['CERTIFIED-ONLY','RECOVERY']:return None
        if kind=='canonical-display' and mode in ['CERTIFIED-ONLY','RECOVERY'] and sid in self.states:
            self.states[sid]['tentative']=None
        row=super().consume(e,observed)
        if row:
            row['envelope_mode']=mode
            if mode in ['CERTIFIED-ONLY','RECOVERY']:
                assert row['valid_visible_frontier']==row['certified_frontier']
        return row
