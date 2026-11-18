"""Full native feedback cut and branch reconciliation for a controlled adaptation.

No ASR/corrector selection lives here. Snapshots contain the complete mutable
inference state at a cleaned-cache boundary, not only the displayed text.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,json

def canonical_bytes(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def digest(value):return hashlib.sha256(canonical_bytes(value)).hexdigest()

STATE_FIELDS=('audio_segments','tokens','context','last_attend_frame','detected_language',
    'initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript')

@dataclass(frozen=True,init=False)
class FeedbackCut:
    _encoded:bytes
    def __init__(self,state):
        if set(state)!=set(STATE_FIELDS):raise ValueError('incomplete or unknown native cut field')
        if not isinstance(state['frontier'],int) or state['frontier']<0:raise ValueError('invalid frontier')
        object.__setattr__(self,'_encoded',canonical_bytes(state))
    @property
    def state(self):return json.loads(self._encoded)
    @property
    def sha256(self):return hashlib.sha256(self._encoded).hexdigest()
    @property
    def frontier(self):return self.state['frontier']
    @property
    def transcript(self):return self.state['transcript']
    def same(self,other):return self._encoded==other._encoded

@dataclass(frozen=True)
class BranchStep:
    job_id:str
    parent_sha:str
    start:FeedbackCut
    end:FeedbackCut
    def __post_init__(self):
        if self.start.sha256!=self.parent_sha:raise ValueError('wrong branch parent')
        if self.end.frontier<=self.start.frontier:raise ValueError('nonadvancing private step')
        if self.start.state['contract']!=self.end.state['contract']:raise ValueError('changed frozen native contract')

class Reconciler:
    """Single-owner strict cut equality; no state projection or text tolerance."""
    def __init__(self,initial:FeedbackCut,retain:bool):
        self.canonical=initial;self.steps=[];self.retain=bool(retain);self.generation=0
    @property
    def tail(self):return self.steps[-1].end if self.steps else self.canonical
    def append(self,step:BranchStep):
        if not step.start.same(self.tail):raise ValueError('private gap, stale root or branch overwrite')
        self.steps.append(step)
    def install(self,next_cut:FeedbackCut):
        if next_cut.frontier<=self.canonical.frontier:raise ValueError('canonical order')
        if next_cut.state['contract']!=self.canonical.state['contract']:raise ValueError('changed trusted contract')
        boundary=next((i for i,s in enumerate(self.steps) if s.end.frontier==next_cut.frontier),None)
        compatible=boundary is not None and self.steps[boundary].end.same(next_cut)
        before=len(self.steps);ahead=bool(self.steps and self.steps[-1].end.frontier>next_cut.frontier)
        if compatible and self.retain:self.steps=self.steps[boundary+1:]
        else:self.steps=[];self.generation+=1
        self.canonical=next_cut
        consumed=(boundary+1) if compatible and self.retain else 0
        return dict(compatible=compatible,ahead=ahead,retained_steps=len(self.steps),
            covered_steps_removed=consumed,discarded_steps=before-len(self.steps)-consumed,generation=self.generation)
    def visible(self):
        cut=self.tail
        return dict(certified_frontier=self.canonical.frontier,visible_frontier=cut.frontier,
            text=cut.transcript,canonical_sha=self.canonical.sha256,private_job=self.steps[-1].job_id if self.steps else None)
