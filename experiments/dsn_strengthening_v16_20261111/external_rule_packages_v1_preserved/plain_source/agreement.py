"""LA2's consecutive-new-input common-prefix rule, explicit Unicode adapter.

No timestamps, models, token/audio alignment, retrospective stability or search.
Published word/timestamp implementation: ufal/whisper_streaming 6da90b44.
"""
from dataclasses import dataclass


def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return a[:n]


@dataclass
class LocalAgreement2:
    confirmed: str = ''
    previous: str | None = None
    max_audio_frontier: int = 0
    updates: int = 0
    ignored_same_or_older_frontier: int = 0
    committed_prefix_conflicts_ignored: int = 0
    canonical_resets: int = 0
    ordinary_extensions: int = 0
    terminal_releases: int = 0

    def canonical(self, text, incompatible_proof=False):
        """Authoritative C/U is common to every policy, never inferred from text."""
        conflict = not (text.startswith(self.confirmed) or self.confirmed.startswith(text))
        if incompatible_proof or conflict:
            self.confirmed, self.previous = text, None
            self.canonical_resets += 1
        elif text.startswith(self.confirmed):
            self.confirmed = text
        return incompatible_proof or conflict

    def update(self, text, audio_frontier):
        if audio_frontier <= self.max_audio_frontier:
            self.ignored_same_or_older_frontier += 1
            return False
        self.max_audio_frontier = audio_frontier
        self.updates += 1
        extended = False
        if self.previous is not None:
            # Keep confirmed output. Without word timestamps, do not realign or
            # concatenate a changed prefix to fabricate a new full hypothesis.
            if not text.startswith(self.confirmed) or not self.previous.startswith(self.confirmed):
                self.committed_prefix_conflicts_ignored += 1
            else:
                agreed = self.confirmed + lcp(self.previous[len(self.confirmed):], text[len(self.confirmed):])
                if len(agreed) > len(self.confirmed):
                    self.confirmed = agreed
                    self.ordinary_extensions += 1
                    extended = True
        self.previous = text
        return extended

    def terminal(self, actual_final_text):
        self.confirmed = actual_final_text
        self.previous = None
        self.terminal_releases += 1


RULES = ('actual_SUP', 'canonical_only', 'fixed_lag_0p5', 'LA2_CP')
