"""Exact-state support for already delivered complete views, no text proof."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class WholeView:
    identity: str
    source_id: str
    received: float
    canonical: object
    steps: tuple
    end: object
    text: str

    @property
    def visible_frontier(self):
        return self.end.frontier if self.text else 0

    def rebase(self, new_cut):
        if self.end.frontier <= new_cut.frontier:
            return 'covered', None
        if self.canonical.same(new_cut):
            return 'supported', self
        for i, step in enumerate(self.steps):
            if step.end.frontier == new_cut.frontier:
                if not step.end.same(new_cut):
                    return 'refuted', None
                return 'supported', replace(self, canonical=new_cut, steps=self.steps[i+1:])
        return 'refuted', None


def pick(candidates, canonical, now, confirmed=None, lag=0.):
    eligible = [canonical]
    for c in candidates:
        if c.received > now:
            raise ValueError('future candidate accessed')
        if c.received + lag > now:
            continue
        if confirmed is not None and not confirmed.startswith(c.text):
            continue
        eligible.append(c)
    # A real, complete, received text-bearing view supplies its own frontier.
    return min(eligible, key=lambda c: (-c.visible_frontier, c.received, c.identity))


def rebase_all(candidates, new_cut):
    kept, counts = [], dict(supported=0, covered=0, refuted=0)
    for c in candidates:
        status, updated = c.rebase(new_cut)
        counts[status] += 1
        if updated is not None:
            kept.append(updated)
    return kept, counts
