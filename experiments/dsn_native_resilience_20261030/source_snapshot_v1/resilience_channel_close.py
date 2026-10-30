"""Admit complete old-channel receipts before its physical incarnation is fenced.

The Supervisor has already confirmed OS exit and joined both readers.  No new
old-channel data can arrive after that closure barrier.  This is not a way to
grant authority after replacement: callbacks run through the original strict
coordinator while its old dispatch still owns that incarnation.
"""
from __future__ import annotations

from collections import Counter
import copy
import queue


class ClosedChannelError(RuntimeError):
    def __init__(self, reason, packets=()):
        super().__init__(reason)
        self.packets = packets


class WorkerReportedFailure(ClosedChannelError):
    """A worker's actual failure report cannot be hidden as an EOF."""


def _closed_proof(slot, incarnation, proof):
    if (not isinstance(proof, dict) or
            proof.get("confirmed_exit") is not True or
            proof.get("slot") != slot or proof.get("incarnation") != incarnation or
            type(proof.get("pid")) is not int or proof["pid"] <= 0 or
            type(proof.get("exitcode")) is not int or
            proof.get("result_channel_closed") is not True or
            proof.get("control_channel_closed") is not True or
            proof.get("partial_frame_thread_blocked") is not False):
        raise ClosedChannelError("closed-channel admission requires confirmed exit and joined readers")


def _partition_closed_packets(inbox, slot, incarnation):
    if not isinstance(inbox, queue.Queue):
        raise TypeError("Owner inbox must be the local thread Queue")
    # Other readers can enqueue concurrently.  Keeping their existing entries
    # in place under the Queue lock avoids requeue-at-tail FIFO inversions.
    selected = []
    with inbox.mutex:
        retained = []
        for packet in inbox.queue:
            if (isinstance(packet, dict) and packet.get("slot") == slot and
                    packet.get("incarnation") == incarnation):
                selected.append(packet)
            else:
                retained.append(packet)
        inbox.queue.clear()
        inbox.queue.extend(retained)
        if selected:
            inbox.not_full.notify_all()
    return selected


def drain_closed_worker_channel(inbox, *, slot, incarnation, death_proof,
                                on_message, on_control=None, audit_packet=None):
    """Drain this closed channel only, before worker_lost/replace_worker.

    on_message(packet) must use strict receive_event and normal terminal-busy
    matching; its return may be the coordinator disposition dictionary.
    on_control is observational only (e.g. final state telemetry), never a
    recursive failure trigger or a new physical-authority registration.
    audit_packet can persist all selected raw receipts before classification.
    Errors are fatal to this Owner; they are not converted into local drops.
    Other channels retain their FIFO positions, including concurrent arrivals.
    """
    _closed_proof(slot, incarnation, death_proof)
    if not callable(on_message):
        raise TypeError("strict original message callback is required")
    selected = _partition_closed_packets(inbox, slot, incarnation)
    counts = Counter()
    try:
        if audit_packet is not None:
            for packet in selected:
                audit_packet(copy.deepcopy(packet))
        # Inspect the whole sealed batch before publishing anything.  A worker
        # failure or integrity failure must not disappear behind its later EOF.
        for packet in selected:
            kind = packet.get("type")
            payload = packet.get("payload")
            if kind == "channel_integrity_failure":
                raise ClosedChannelError("closed channel contains an integrity failure", selected)
            if kind == "message" and isinstance(payload, dict) and payload.get("kind") == "failed":
                raise WorkerReportedFailure("closed worker reported an actual execution failure", selected)
            if kind not in ("message", "control", "channel_exit"):
                raise ClosedChannelError("unknown packet on a sealed worker channel", selected)
        for packet in selected:
            kind = packet["type"]
            if kind == "channel_exit":
                counts["channel_exit"] += 1
                counts["partial_logical_frame"] += int(bool(packet.get("partial_frame")))
                continue
            if kind == "control":
                counts["control_records"] += 1
                if on_control is not None:
                    on_control(packet)
                continue
            payload = packet.get("payload")
            if not isinstance(payload, dict):
                raise ClosedChannelError("sealed worker result is not an object", selected)
            phase = payload.get("kind")
            if phase in ("ready", "drained"):
                # Process-control bytes from a now-dead worker cannot re-grant
                # readiness or produce a neural result.
                counts["retired_process_controls"] += 1
                continue
            if phase not in ("asr_early", "completed", "abandoned"):
                raise ClosedChannelError("unknown result phase on a sealed worker channel", selected)
            result = on_message(packet)
            counts["delivered_results"] += 1
            counts["delivered_" + phase] += 1
            if isinstance(result, dict):
                counts["disposition_" + str(result.get("disposition", "unspecified"))] += 1
        return dict(
            slot=slot, incarnation=incarnation,
            sealed_packets=len(selected), counts=dict(counts),
            closure_before_incarnation_fence=True,
            new_authority_granted_by_helper=False,
            other_channels_reordered=False,
        )
    finally:
        # Removal is equivalent to receiving these Queue items.  Preserve the
        # Queue's completion accounting even when the Owner must now recover.
        for _ in selected:
            inbox.task_done()
