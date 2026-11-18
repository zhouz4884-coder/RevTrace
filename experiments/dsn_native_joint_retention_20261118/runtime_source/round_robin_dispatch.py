"""Common canonical-first round-robin allocation; no authorization or execution.

Probing reads existing canonical/tail/input-work predicates. It does not register
jobs, refresh/promote jobs, issue proofs, consume receipts, or alter the cursor.
The sole cursor transition follows an actual successful Owner command send.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Proposal:
    source_id: str
    start: object
    end: int
    layer: str
    source_index: int
    cursor_before: int
    generation: int
    eligible_canonical_sources: tuple
    eligible_conditional_sources: tuple
    accepted_frontier_snapshot: tuple
    canonical_frontier_snapshot: tuple


class CanonicalFirstRoundRobin:
    def __init__(self,source_ids):
        self.source_ids=tuple(source_ids)
        if len(set(self.source_ids))!=len(self.source_ids):raise ValueError('duplicate scheduler source')
        self.cursor=0;self.successful_dispatches=0

    def peek(self,policy,accepted,*,allow_speculation,max_ahead_frames):
        """Return one pure proposal; caller must register/revalidate before send."""
        if not self.source_ids:return None
        canonical={};conditional={};canonical_frontiers=[]
        for index,sid in enumerate(self.source_ids):
            canon=policy.canonical(sid);canonical_frontiers.append((sid,canon.frontier));starts=[('canonical',canon)]
            if allow_speculation:
                tail=policy.tail(sid)
                if not tail.same(canon):starts.append(('conditional',tail))
            for layer,start in starts:
                end=min(policy.frames[sid],start.frontier+8000)
                if end<=start.frontier or end>accepted[sid]:continue
                if layer=='conditional' and end>canon.frontier+max_ahead_frames:continue
                if policy._has_work(sid,start,end):continue
                (canonical if layer=='canonical' else conditional)[index]=(start,end)
        canonical_ids=tuple(self.source_ids[i] for i in canonical)
        conditional_ids=tuple(self.source_ids[i] for i in conditional)
        for layer,eligible in (('canonical',canonical),('conditional',conditional)):
            for offset in range(len(self.source_ids)):
                index=(self.cursor+offset)%len(self.source_ids)
                if index in eligible:
                    start,end=eligible[index]
                    return Proposal(self.source_ids[index],start,end,layer,index,self.cursor,
                        self.successful_dispatches,canonical_ids,conditional_ids,
                        tuple((sid,accepted[sid]) for sid in self.source_ids),tuple(canonical_frontiers))
        return None

    def confirm_dispatch(self,proposal,*,slot):
        """Advance after registered command send; never on a peek or failed send."""
        if (not isinstance(proposal,Proposal) or proposal.generation!=self.successful_dispatches
                or proposal.cursor_before!=self.cursor
                or self.source_ids[proposal.source_index]!=proposal.source_id):
            raise ValueError('stale or foreign scheduler dispatch confirmation')
        self.successful_dispatches+=1
        self.cursor=(proposal.source_index+1)%len(self.source_ids)
        return dict(policy='shared_canonical_first_round_robin_v1',slot=slot,source_id=proposal.source_id,
            chosen_layer=proposal.layer,eligible_canonical_source_count=len(proposal.eligible_canonical_sources),
            eligible_canonical_sources=list(proposal.eligible_canonical_sources),
            eligible_conditional_source_count=len(proposal.eligible_conditional_sources),
            eligible_conditional_sources=list(proposal.eligible_conditional_sources),
            accepted_frontier_snapshot=dict(proposal.accepted_frontier_snapshot),
            canonical_frontier_snapshot=dict(proposal.canonical_frontier_snapshot),
            cursor_before=proposal.cursor_before,cursor_after=self.cursor,
            successful_dispatch_sequence=self.successful_dispatches)
