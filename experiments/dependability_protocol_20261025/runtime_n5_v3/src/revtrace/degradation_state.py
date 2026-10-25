"""CPU accounting/policy core. Does not install P or certify a model output.

Live wiring MUST durably append input acceptance decisions before ACK and obtain
canonical/Consumer notices from the existing audited runtime. Neither is faked
by this module; until wired, tests are CPU fixtures, not a serving mechanism.
"""
from dataclasses import asdict,dataclass
from enum import Enum


class Mode(str,Enum):
    NORMAL='NORMAL'
    DEGRADED='DEGRADED'
    CERTIFIED_ONLY='CERTIFIED-ONLY'
    BACKPRESSURE='BACKPRESSURE/REJECT'
    RECOVERY='RECOVERY'


@dataclass
class AudioObligation:
    offered:int=0
    accepted:int=0
    certified:int=0
    reserved:int=0
    version:int=0
    visible:int=0
    visible_version:int=0
    rejected:bool=False
    eof:bool=False
    rejection_reason:str=''
    accepted_prefix_sha256:str=''


class CreditBook:
    def __init__(self,budget_samples,*,epoch=1):
        if type(budget_samples) is not int or budget_samples<=0:raise ValueError('positive integer audio budget')
        self.budget=budget_samples;self.epoch=epoch;self.sessions={};self.events=[]
    def session(self,sid):return self.sessions.setdefault(sid,AudioObligation())
    @property
    def debt(self):return sum(s.accepted-s.certified for s in self.sessions.values())
    @property
    def committed_credit(self):return sum(max(s.accepted,s.reserved)-s.certified for s in self.sessions.values())
    def _record(self,kind,sid,**fields):
        self.events.append(dict(kind=kind,session_id=sid,epoch=self.epoch,**fields));self.check()
    def check(self):
        assert self.debt<=self.committed_credit<=self.budget
        for s in self.sessions.values():
            assert 0<=s.certified<=s.accepted<=s.offered
            assert s.reserved>=s.accepted
            if s.rejected:assert s.accepted==s.certified==0
    def snapshot(self,origin_perf):
        return dict(budget=self.budget,epoch=self.epoch,origin_perf=origin_perf,
            sessions={str(sid):asdict(s) for sid,s in sorted(self.sessions.items())})
    @classmethod
    def restore(cls,snapshot,canonical,*,epoch,origin_perf):
        if snapshot['origin_perf']!=origin_perf:raise ValueError('original offered clock changed')
        b=cls(snapshot['budget'],epoch=epoch)
        if set(map(int,snapshot['sessions']))!=set(canonical):raise ValueError('restore session manifest mismatch')
        for key,v in snapshot['sessions'].items():
            sid=int(key);s=AudioObligation(**v);state=canonical[sid]
            if not s.certified<=state.audio_frontier_window<=s.accepted:raise ValueError('canonical/input ledgers disagree')
            s.certified=state.audio_frontier_window;s.version=state.checkpoint_id
            s.reserved=max(s.reserved,s.accepted,s.certified)
            s.visible=0;s.visible_version=-1
            b.sessions[sid]=s
        b.check();return b
    def offer(self,sid,frontier,*,eof=False):
        s=self.session(sid)
        if type(frontier) is not int or frontier<s.offered:raise ValueError('offered audio cannot move backward')
        if s.eof and frontier!=s.offered:raise ValueError('audio after EOF')
        s.offered=frontier;s.eof=s.eof or eof
        if s.eof and s.reserved>s.offered:s.reserved=max(s.accepted,s.offered)
        self._record('audio-offered',sid,frontier=frontier,eof=s.eof)
    def reserve(self,sid,authority_quantum):
        s=self.session(sid)
        if type(authority_quantum) is not int or not 0<authority_quantum<=self.budget:
            raise ValueError('whole authority quantum must fit budget')
        if s.rejected:return False
        if s.reserved>s.accepted:return True
        start=max(s.reserved,s.certified)
        if s.offered<=start:return False
        end=start+authority_quantum
        if s.eof:end=min(end,s.offered)
        cost=end-start
        if self.committed_credit+cost>self.budget:
            self._record('credit-backpressure',sid,requested_end=end);return False
        s.reserved=end;self._record('whole-interval-reserved',sid,frontier=end)
        return True
    def acceptance_intent(self,sid,frontier):
        s=self.session(sid)
        if s.rejected or type(frontier) is not int or not s.accepted<=frontier<=min(s.offered,s.reserved):
            raise ValueError('no accepted hole, future audio or unreserved debt')
        return dict(session_id=sid,from_sample=s.accepted,to_sample=frontier)
    def accept_released(self,sid,frontier,*,durable_receipt):
        intent=self.acceptance_intent(sid,frontier);s=self.session(sid)
        r=durable_receipt
        if (r.get('kind')!='accepted-input' or r.get('session_id')!=sid or
            r.get('from_sample')!=intent['from_sample'] or r.get('to_sample')!=frontier or
            type(r.get('sequence')) is not int or r['sequence']<1 or
            len(r.get('decision_id',''))!=64 or len(r.get('prefix_sha256',''))!=64):
            raise ValueError('actual synchronized input receipt required before acceptance')
        # Trusted in-process input journal supplies the receipt; this field
        # validation is not a MAC or protection from a malicious owner.
        s.accepted=frontier;s.accepted_prefix_sha256=r['prefix_sha256'];self._record('observed-durable-input-acceptance',sid,
            frontier=frontier,input_sequence=r['sequence'],input_decision_id=r['decision_id'])
    def observe_admission(self,sid,*,epoch,version,parent_frontier,frontier,receipt):
        s=self.session(sid)
        if epoch!=self.epoch or not receipt or version!=s.version+1 or parent_frontier!=s.certified or not s.certified<frontier<=s.accepted:
            raise ValueError('notice must name actual next durable canonical admission')
        s.certified=frontier;s.version=version
        if s.reserved<s.certified:s.reserved=s.certified
        self._record('observed-durable-admission',sid,frontier=frontier,version=version,receipt=receipt)
    def observe_consumer(self,sid,*,epoch,canonical_version,legal_frontier):
        s=self.session(sid)
        if epoch!=self.epoch or type(legal_frontier) is not int or not 0<=legal_frontier<=s.accepted:
            raise ValueError('invalid observed consumer progress')
        if canonical_version>s.version:raise ValueError('consumer cannot invent a canonical version')
        # An old ACK is retained as observation, never relabelled current.
        s.visible=legal_frontier;s.visible_version=canonical_version
        self._record('observed-consumer',sid,frontier=legal_frontier,version=canonical_version)
    def valid_private_frontier(self,sid):
        s=self.session(sid)
        return s.visible if s.visible_version==s.version else 0
    def reject_unaccepted(self,sid,reason):
        s=self.session(sid)
        if s.accepted or s.certified:raise ValueError('accepted audio cannot be erased by rejection')
        if not reason:raise ValueError('explicit rejection reason required')
        s.rejected=True;s.reserved=0;s.rejection_reason=reason
        self._record('new-session-rejected',sid,reason=reason,offered=s.offered)


@dataclass(frozen=True)
class ObservedPressure:
    # Deliberately no output text, fault labels, future service time or WER.
    pending_ingress:bool
    oldest_uncertified_age:float
    actual_private_queue:int
    actual_authority_queue:int
    private_lease_active:bool
    authority_lease_active:bool
    consumer_caught_up:bool
    owner_and_input_recovered:bool


@dataclass(frozen=True)
class EnvelopeAction:
    mode:Mode
    accept_new_credit:bool
    issue_private:bool
    issue_authority:bool
    publish_provisional:bool
    cancel_running_GPU:bool=False
    bypass_admission:bool=False


class EnvelopePolicy:
    def __init__(self,*,warning_age=4.,critical_age=8.,clear_age=2.):
        if not 0<=clear_age<warning_age<critical_age:raise ValueError('ordered hysteresis ages')
        self.warning=warning_age;self.critical=critical_age;self.clear=clear_age
        self.mode=Mode.NORMAL;self.recovering=False
    def begin_recovery(self):self.recovering=True;self.mode=Mode.RECOVERY
    def decide(self,book,pressure):
        p=pressure
        if p.oldest_uncertified_age<0 or min(p.actual_private_queue,p.actual_authority_queue)<0:
            raise ValueError('only real nonnegative observations')
        if self.recovering:
            if not (p.owner_and_input_recovered and p.consumer_caught_up):
                return EnvelopeAction(Mode.RECOVERY,False,False,False,False)
            self.recovering=False
        age=p.oldest_uncertified_age
        if age>=self.critical or (self.mode==Mode.CERTIFIED_ONLY and age>self.clear):
            mode=Mode.CERTIFIED_ONLY
        elif p.pending_ingress and book.committed_credit>=book.budget:
            mode=Mode.BACKPRESSURE
        elif age>=self.warning or (self.mode==Mode.DEGRADED and age>self.clear):
            mode=Mode.DEGRADED
        else:mode=Mode.NORMAL
        self.mode=mode
        private=mode not in [Mode.CERTIFIED_ONLY,Mode.RECOVERY]
        # The live adapter additionally enforces released/accepted target and
        # existing exact-chain/receive checks. This action is not a certificate.
        return EnvelopeAction(mode,mode not in [Mode.CERTIFIED_ONLY,Mode.BACKPRESSURE],
            private,True,private)


def accept_durably(book,journal,sid,frontier,prefix_sha256):
    """Validate first, actual sync second, dispatch eligibility/ACK only last."""
    intent=book.acceptance_intent(sid,frontier)
    if frontier==intent['from_sample']:return None
    receipt=journal.accept(sid,from_sample=intent['from_sample'],to_sample=frontier,
        prefix_sha256=prefix_sha256)
    book.accept_released(sid,frontier,durable_receipt=receipt)
    return receipt
