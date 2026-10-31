"""Pure retrospective analysis; no filesystem, neural model, or serving mutation.

Raw-log adapters must establish logical_session_id, authenticated selected cuts,
and clock provenance before invoking these functions. A CONFIRMED result states
complete input equality; it never grants namespace validity or installation.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter


STATE_FIELDS = frozenset((
    "audio_segments", "tokens", "context", "last_attend_frame",
    "detected_language", "initial_tokens", "initial_token_length", "sot_index",
    "decoder_type", "contract", "frontier", "transcript",
))
STATUSES = ("CONFIRMED", "REFUTED", "UNRESOLVED")


def _encoded_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def encoded_cut(cut):
    """Match the original FeedbackCut's complete canonical-byte equality."""
    if not isinstance(cut, dict) or set(cut) != STATE_FIELDS:
        raise ValueError("complete STATE_FIELDS are required")
    if type(cut["frontier"]) is not int or cut["frontier"] < 0:
        raise ValueError("invalid complete-cut frontier")
    return _encoded_json(cut)


def cut_sha(cut):
    return hashlib.sha256(encoded_cut(cut)).hexdigest()


def request_key(row):
    fields = ("cell_id", "logical_session_id", "source_id")
    if any(not isinstance(row.get(f), str) or not row[f] for f in fields):
        raise ValueError("explicit cell/logical-session/source identity required")
    return tuple(row[f] for f in fields)


def dispatch_key(row):
    if type(row.get("owner_epoch")) is not int or row["owner_epoch"] < 0:
        raise ValueError("explicit dispatch Owner epoch required")
    if not isinstance(row.get("job_id"), str) or not row["job_id"]:
        raise ValueError("explicit immutable job ID required")
    return row["cell_id"], row["owner_epoch"], row["job_id"]


def _finite_nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid " + name)
    return float(value)


def pair_dispatches(dispatches, selected_witnesses):
    """Return one status per distinct actual dispatch and audit counts.

    Dispatch row: cell_id, logical_session_id, source_id, owner_epoch, job_id,
      start (full state), started_on_canonical (bool), dispatched_perf.
    Witness row: same request identity, state (full selected state), provenance;
      optional observed_perf is an actually known Canonical witness clock.
    The adapter, not this function, verifies WAL, cadence, contract, source hash,
    exact physical receipts, session mapping, and input manifest provenance.
    """
    selected = {}
    for witness in selected_witnesses:
        state = witness["state"]
        raw = encoded_cut(state)
        key = request_key(witness) + (state["frontier"],)
        if not witness.get("provenance"):
            raise ValueError("selected witness lacks source provenance")
        if "observed_perf" in witness:
            _finite_nonnegative(witness["observed_perf"], "witness clock")
        if key in selected:
            if selected[key][0] != raw:
                raise ValueError("contradictory selected states at one frontier")
            selected[key][1].append(witness)
        else:
            selected[key] = (raw, [witness])

    unique, duplicate_rows = {}, 0
    for dispatch in dispatches:
        request_key(dispatch)
        key = dispatch_key(dispatch)
        encoded_cut(dispatch["start"])
        _finite_nonnegative(dispatch["dispatched_perf"], "dispatch clock")
        if type(dispatch.get("started_on_canonical")) is not bool:
            raise ValueError("actual dispatch birth classification required")
        if key in unique:
            if dispatch != unique[key]:
                raise ValueError("conflicting immutable dispatch records")
            duplicate_rows += 1
            continue
        unique[key] = dispatch

    rows = []
    for key, dispatch in unique.items():
        state = dispatch["start"]
        match = selected.get(request_key(dispatch) + (state["frontier"],))
        row = dict(dispatch)
        row.update(start_sha256=cut_sha(state), start_frontier=state["frontier"],
                   input_status="UNRESOLVED", input_status_reason="no_same_frontier_selected_witness",
                   actual_parent_sha256=None, different_top_level_fields=[],
                   witness_provenances=[], first_known_witness_perf=None)
        if match is not None:
            raw, witnesses = match
            actual = witnesses[0]["state"]
            same = encoded_cut(state) == raw
            row.update(input_status="CONFIRMED" if same else "REFUTED",
                       input_status_reason="complete_bytes_equal" if same else "same_frontier_complete_bytes_differ",
                       actual_parent_sha256=hashlib.sha256(raw).hexdigest(),
                       different_top_level_fields=[f for f in sorted(STATE_FIELDS)
                                                   if _encoded_json(state[f]) != _encoded_json(actual[f])],
                       witness_provenances=[w["provenance"] for w in witnesses],
                       first_known_witness_perf=min((w["observed_perf"] for w in witnesses if "observed_perf" in w), default=None))
        rows.append(row)
    return rows, dict(unique_actual_dispatches=len(rows), duplicate_identical_dispatch_rows=duplicate_rows,
                      all_dispatches=status_summary(rows),
                      conditional_dispatches=status_summary([r for r in rows if not r["started_on_canonical"]]))


def status_summary(rows):
    counts = Counter(r["input_status"] for r in rows)
    if set(counts) - set(STATUSES):
        raise ValueError("unknown tri-state status")
    n = len(rows)
    c, r, u = (counts[s] for s in STATUSES)
    return dict(N=n, CONFIRMED=c, REFUTED=r, UNRESOLVED=u,
                resolved_confirmation_rate=None if c+r == 0 else c/(c+r),
                all_dispatch_confirmation_lower=None if n == 0 else c/n,
                all_dispatch_confirmation_upper=None if n == 0 else (c+u)/n)


def dispatch_timebins(rows, *, origin_perf, duration_seconds, bin_seconds=10.,
                      clock="wall", sample_rate=16000):
    """Fixed cohort bins include empty intervals; statuses are retrospective."""
    _finite_nonnegative(origin_perf, "origin clock")
    duration_seconds = _finite_nonnegative(duration_seconds, "bin coverage")
    if type(bin_seconds) not in (int, float) or not math.isfinite(bin_seconds) or bin_seconds <= 0:
        raise ValueError("positive finite bin width required")
    if clock not in ("wall", "audio"):
        raise ValueError("wall or audio clock required")
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("positive sample rate required")
    n = max(1, math.ceil(duration_seconds/bin_seconds))
    assigned = []
    for row in rows:
        t = (row["dispatched_perf"]-origin_perf if clock == "wall"
             else row["start_frontier"]/sample_rate)
        if not math.isfinite(t) or t < 0 or t > duration_seconds:
            raise ValueError("dispatch falls outside frozen bin coverage")
        # Half-open bins, with the final frozen endpoint included in the last.
        # An exact endpoint must not produce an extra zero-width interval.
        i = min(n-1, int(t//bin_seconds))
        assigned.append((i, row))
    bins = [[] for _ in range(n)]
    for i, row in assigned:
        bins[i].append(row)
    return [dict(bin_index=i, clock=clock, begin_seconds=i*bin_seconds,
                 end_seconds=min((i+1)*bin_seconds, duration_seconds),
                 status_scope="dispatch_time_cohort_retrospective_status",
                 **status_summary(group)) for i, group in enumerate(bins)]


def rolling_confirmation_marker(rows, *, window=20, minimum_resolved=10, below=.5):
    """Descriptive marker only; unknowns stay in each dispatch-count window."""
    conditional = sorted((r for r in rows if not r["started_on_canonical"]),
                         key=lambda r: (r["dispatched_perf"], dispatch_key(r)))
    first_refuted = next((dispatch_key(r) for r in conditional if r["input_status"] == "REFUTED"), None)
    marker = None
    for i in range(window-1, len(conditional)):
        group = conditional[i-window+1:i+1]
        summary = status_summary(group)
        if summary["CONFIRMED"] + summary["REFUTED"] >= minimum_resolved and summary["resolved_confirmation_rate"] < below:
            marker = dict(first_job=dispatch_key(group[0]), last_job=dispatch_key(group[-1]), **summary)
            break
    return dict(first_refuted_conditional_dispatch=first_refuted, first_low_window=marker,
                window_dispatches=window, minimum_resolved=minimum_resolved,
                threshold_strictly_below=below, scope="retrospective_descriptive_marker_not_a_change_point_test")


def exactly_aligned_reference(parts, frontier):
    """Human reference only at genuine cumulative utterance/sample boundaries.

    Rejects missing/noncontiguous parts, and never rounds a sample frontier or
    truncates text according to audio fraction. Returns None inside a part.
    This is an offline annotation checkpoint, not an online endpoint signal.
    """
    if type(frontier) is not int or frontier < 0:
        raise ValueError("invalid requested frontier")
    cursor, chunks, found = 0, [], "" if frontier == 0 else None
    for part in parts:
        start, end = part["start_sample"], part["end_sample"]
        if type(start) is not int or type(end) is not int or start != cursor or end <= start:
            raise ValueError("noncontiguous source parts")
        if not isinstance(part.get("reference"), str):
            raise ValueError("complete part reference required")
        chunks.append(part["reference"])
        cursor = end
        if frontier == end:
            found = " ".join(chunks)
    if frontier > cursor:
        raise ValueError("reference frontier beyond source")
    return found
