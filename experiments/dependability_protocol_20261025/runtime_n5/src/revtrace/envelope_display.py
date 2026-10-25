"""Typed degradation controls only withdraw provisional visibility, never P."""
from .certified_display import ContinuityView

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
