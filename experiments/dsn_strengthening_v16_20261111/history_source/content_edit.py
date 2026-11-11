"""Offline actual-Consumer Unicode edit/lifetime ledger. No model/runtime hook.

An edit identity is an alignment convention, not semantic character identity.
Deterministic priority is MATCH, SUBSTITUTE, DELETE, INSERT. A second priority
DELETE, INSERT, MATCH, SUBSTITUTE is propagated independently through the whole
history. Per-event bounds range over every optimal alignment conditional on the
current primary identities; these are not global lifetime-confidence bounds.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

PRIMARY = ("M", "S", "D", "I")
ALTERNATE = ("D", "I", "M", "S")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def suffix_distance(a, b):
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n:
                d[i][j] = m - j
            elif j == m:
                d[i][j] = n - i
            else:
                d[i][j] = min(d[i + 1][j] + 1, d[i][j + 1] + 1,
                              d[i + 1][j + 1] + (a[i] != b[j]))
    return d


def transitions(a, b, d, i, j):
    out = []
    if i < len(a) and j < len(b):
        op = "M" if a[i] == b[j] else "S"
        cost = op != "M"
        if d[i][j] == d[i + 1][j + 1] + cost:
            out.append((op, i + 1, j + 1))
    if i < len(a) and d[i][j] == d[i + 1][j] + 1:
        out.append(("D", i + 1, j))
    if j < len(b) and d[i][j] == d[i][j + 1] + 1:
        out.append(("I", i, j + 1))
    return out


def alignment(a, b, priority=PRIMARY, old_births=None, observed=None, age=2.0):
    """Return one minimum-cost path plus all-optimal additive metric ranges."""
    if old_births is None:
        old_births = [observed or 0.0] * len(a)
    if len(old_births) != len(a):
        raise ValueError("birth count does not match previous text")
    observed = 0.0 if observed is None else observed
    # Exact fast path: if a is a subsequence of b, the length lower bound is
    # attained by insertions only. Every optimal path therefore has D=S=0.
    # Count ALL embeddings in an O(len(a) * length_delta) band; do not silently
    # discard ambiguity by trimming a common prefix.
    cursor = iter(b)
    if len(b) >= len(a) and all(any(c == x for x in cursor) for c in a):
        n, delta = len(a), len(b) - len(a)
        ways = [[0] * (delta + 1) for _ in range(n + 1)]
        for i in range(n, -1, -1):
            for extra in range(delta, -1, -1):
                j = i + extra
                if i == n:
                    ways[i][extra] = 1
                else:
                    ways[i][extra] = (ways[i + 1][extra] if a[i] == b[j] else 0)
                    if extra < delta: ways[i][extra] += ways[i][extra + 1]
        path, i, extra = [], 0, 0
        rank = {v: k for k, v in enumerate(priority)}
        while i < n or extra < delta:
            j = i + extra
            choices = []
            if i < n and a[i] == b[j] and ways[i + 1][extra]: choices.append("M")
            if extra < delta and ways[i][extra + 1]: choices.append("I")
            op = min(choices, key=rank.__getitem__)
            path.append((op, i if op == "M" else None, j))
            if op == "M": i += 1
            else: extra += 1
        return dict(distance=delta, path=path,
                    operation_counts=dict(I=delta, D=0, S=0, M=n),
                    optimal_alignment_count=str(ways[0][0]),
                    all_optimal_bounds_conditional_on_current_identity_history={
                        "I": (delta, delta), "D": (0, 0), "S": (0, 0),
                        "retracted": (0, 0), "retracted_age_ge_threshold": (0, 0)})
    d = suffix_distance(a, b)
    i = j = 0
    path = []
    rank = {v: k for k, v in enumerate(priority)}
    while i < len(a) or j < len(b):
        op, ni, nj = min(transitions(a, b, d, i, j), key=lambda t: rank[t[0]])
        path.append((op, i if op != "I" else None, j if op != "D" else None))
        i, j = ni, nj
    counts = Counter(op for op, _, _ in path)
    assert counts["I"] - counts["D"] == len(b) - len(a)
    assert counts["I"] + counts["D"] + counts["S"] == d[0][0]
    # Optimal-path DAG, exact integer path count; long identical runs may make
    # that count large, so output only its decimal representation.
    metrics = ("I", "D", "S", "retracted", "retracted_age_ge_threshold")
    bounds = {}
    ways = {}
    n, m = len(a), len(b)
    for ii in range(n, -1, -1):
        for jj in range(m, -1, -1):
            key = ii, jj
            if ii == n and jj == m:
                bounds[key] = {k: (0, 0) for k in metrics}
                ways[key] = 1
                continue
            candidates = []
            ways[key] = 0
            for op, ni, nj in transitions(a, b, d, ii, jj):
                removed = op in ("D", "S")
                inc = {k: int(k == op) for k in ("I", "D", "S")}
                inc["retracted"] = int(removed)
                inc["retracted_age_ge_threshold"] = int(
                    removed and observed - old_births[ii] >= age)
                candidates.append({k: (bounds[ni, nj][k][0] + inc[k],
                                        bounds[ni, nj][k][1] + inc[k])
                                   for k in metrics})
                ways[key] += ways[ni, nj]
            bounds[key] = {k: (min(c[k][0] for c in candidates),
                               max(c[k][1] for c in candidates)) for k in metrics}
    return {"distance": d[0][0], "path": path,
            "operation_counts": {k: counts[k] for k in ("I", "D", "S", "M")},
            "optimal_alignment_count": str(ways[0, 0]),
            "all_optimal_bounds_conditional_on_current_identity_history": bounds[0, 0]}


class Ledger:
    def __init__(self, priority=PRIMARY, age=2.0):
        self.priority, self.age = priority, age
        self.text = ""
        self.active = []
        self.closed = []
        self.events = []
        self.totals = Counter()
        self.last_time = None

    def observe(self, text, observed, row_index, kind):
        if not isinstance(text, str) or not isinstance(observed, (int, float)):
            raise ValueError("text/time type mismatch")
        if self.last_time is not None and observed < self.last_time:
            raise ValueError("same-source Consumer time decreases")
        result = alignment(self.text, text, self.priority,
                           [x["first_observed"] for x in self.active], observed, self.age)
        active = []
        operations = []
        for op, old_index, new_index in result.pop("path"):
            old = self.active[old_index] if old_index is not None else None
            if op in ("D", "S"):
                closed = dict(old, closing_row=row_index, closing_kind=kind,
                              closing_observed=observed, retraction_operation=op,
                              lifetime_seconds=observed - old["first_observed"])
                self.closed.append(closed)
                operations.append(dict(op=op, old_index=old_index, new_index=new_index,
                                       old_code_point=old["char"],
                                       new_code_point=text[new_index] if op == "S" else None,
                                       occurrence_id=old["occurrence_id"],
                                       lifetime_seconds=closed["lifetime_seconds"]))
            if op == "M":
                active.append(old)
            elif op in ("S", "I"):
                unit = dict(char=text[new_index], first_observed=observed,
                            birth_row=row_index, birth_offset=new_index,
                            occurrence_id=f"{row_index}:{new_index}")
                active.append(unit)
                if op == "I":
                    operations.append(dict(op=op, old_index=None, new_index=new_index,
                                           new_code_point=text[new_index],
                                           occurrence_id=unit["occurrence_id"]))
        prefix = 0
        for x, y in zip(self.text, text):
            if x != y:
                break
            prefix += 1
        lcp_closed, lcp_new = len(self.text) - prefix, len(text) - prefix
        self.totals.update(result["operation_counts"])
        self.totals["distance"] += result["distance"]
        self.totals["lcp_suffix_closed"] += lcp_closed
        self.totals["lcp_suffix_introduced"] += lcp_new
        self.events.append(dict(row_index=row_index, kind=kind, observed=observed,
                                before=self.text, after=text,
                                lcp_suffix_closed=lcp_closed, lcp_suffix_introduced=lcp_new,
                                edit_operations=operations, **result))
        self.text, self.active, self.last_time = text, active, observed
        assert "".join(x["char"] for x in active) == text
        assert self.totals["I"] - self.totals["D"] == len(text)
        assert self.totals["I"] + self.totals["D"] + self.totals["S"] == self.totals["distance"]

    def summary(self):
        return dict(metric_family="minimum_edit", tie_break=list(self.priority), age_threshold_seconds=self.age,
                    **dict(self.totals), retracted_edit_occurrences=len(self.closed),
                    edit_retractions_age_ge_threshold=sum(
                        x["lifetime_seconds"] >= self.age for x in self.closed),
                    longest_edit_retraction_lifetime_seconds=max(
                        (x["lifetime_seconds"] for x in self.closed), default=0.0),
                    final_visible_code_points=len(self.text),
                    right_censored_survivors=len(self.active),
                    right_censor_time_last_actual_source_observation=self.last_time,
                    ambiguous_events=sum(int(e["optimal_alignment_count"]) > 1 for e in self.events))

    def spans(self):
        return [dict(x, retracted=True, right_censored=False) for x in self.closed] + [
            dict(x, retracted=False, right_censored=True,
                 censor_observed=self.last_time,
                 observed_lifetime_seconds=self.last_time - x["first_observed"])
            for x in self.active]


class LcpLedger:
    """A separate LCP suffix-identity ledger; never called true edit identity."""
    def __init__(self, age=2.0):
        self.age = age
        self.text, self.active, self.closed, self.events = "", [], [], []
        self.last_time = None
        self.introduced = 0

    def observe(self, text, observed, row_index, kind):
        if self.last_time is not None and observed < self.last_time:
            raise ValueError("same-source Consumer time decreases")
        prefix = 0
        for x, y in zip(self.text, text):
            if x != y: break
            prefix += 1
        for old in self.active[prefix:]:
            self.closed.append(dict(old, closing_row=row_index, closing_kind=kind,
                closing_observed=observed, retraction_operation="LCP_SUFFIX_CLOSE",
                lifetime_seconds=observed - old["first_observed"]))
        self.events.append(dict(row_index=row_index, observed=observed, kind=kind,
            before=self.text, after=text, lcp_suffix_closed=len(self.text) - prefix,
            lcp_suffix_introduced=len(text) - prefix))
        self.introduced += len(text) - prefix
        self.active = self.active[:prefix] + [dict(char=c, first_observed=observed,
            birth_row=row_index, birth_offset=k, occurrence_id=f"{row_index}:{k}")
            for k, c in enumerate(text) if k >= prefix]
        self.text, self.last_time = text, observed
        assert self.introduced - len(self.closed) == len(text)

    def summary(self):
        return dict(metric_family="lcp_suffix_identity", age_threshold_seconds=self.age,
            lcp_suffix_closed=len(self.closed), lcp_suffix_introduced=self.introduced,
            lcp_retractions_age_ge_threshold=sum(x["lifetime_seconds"] >= self.age for x in self.closed),
            longest_lcp_retraction_lifetime_seconds=max((x["lifetime_seconds"] for x in self.closed), default=0.0),
            final_visible_code_points=len(self.text), right_censored_survivors=len(self.active),
            right_censor_time_last_actual_source_observation=self.last_time)

    def spans(self):
        return [dict(x, retracted=True, right_censored=False) for x in self.closed] + [
            dict(x, retracted=False, right_censored=True, censor_observed=self.last_time,
                 observed_lifetime_seconds=self.last_time - x["first_observed"])
            for x in self.active]


def analyze_rows(rows, age=2.0):
    ledgers = {}
    # Do not sort: source-local order is the actual Consumer observation order.
    for index, row in enumerate(rows):
        sid = row["source_id"]
        for mode in ("raw", "whitespace_stripped"):
            text = row["text"]
            if mode == "whitespace_stripped":
                text = "".join(c for c in text if not c.isspace())
            for name, priority in (("primary", PRIMARY), ("alternate", ALTERNATE)):
                key = sid, mode, name
                if key not in ledgers:
                    ledgers[key] = Ledger(priority, age)
                ledgers[key].observe(text, row["observed"], index, row.get("kind", "unspecified"))
            key = sid, mode, "LCP_suffix_identity"
            if key not in ledgers:
                ledgers[key] = LcpLedger(age)
            ledgers[key].observe(text, row["observed"], index, row.get("kind", "unspecified"))
    if not ledgers:
        raise ValueError("empty actual Consumer log")
    return ledgers


def checked_json(path, expected):
    blob = Path(path).read_bytes()
    if sha256(blob) != expected:
        raise ValueError(f"input SHA256 mismatch: {path}")
    return json.loads(blob.decode("utf-8"))


def checked_rows(path, expected):
    blob = Path(path).read_bytes()
    if sha256(blob) != expected:
        raise ValueError(f"input SHA256 mismatch: {path}")
    return [json.loads(line) for line in blob.decode("utf-8").splitlines() if line.strip()]
