#!/usr/bin/env python3
"""Phase 6 semantic gate over frozen Phase 5 records.

This is an offline protocol audit, not a serving benchmark. It exercises the
evidence lifecycle and epoch fences using the real Phase 5 c32 counterexample
and recorded proposer margins.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from revtrace.phase6 import (
    ContractEvidenceMemory,
    EpochFencedCommitLedger,
    ExecutionIdentity,
    ExecutionSignature,
    FailureRecord,
    PopulationContract,
    PositiveCertificate,
    RuntimeContract,
    ServiceContract,
    ShapeEnvelope,
    joint_risk_slo_admission,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase5-c32",
        type=Path,
        default=ROOT
        / "results/phase5/workload_matrix/0p6b-c32-d120-burst-zh.json",
    )
    parser.add_argument(
        "--phase5-c16",
        type=Path,
        default=ROOT
        / "results/phase5/workload_matrix/0p6b-c16-d60-poisson-mixed.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/phase6/semantic_gate.json",
    )
    return parser.parse_args()


def make_contract(
    identity: ExecutionIdentity,
    *,
    batch: int,
    language: str,
    arrival: str,
    duration: str,
) -> RuntimeContract:
    return RuntimeContract(
        identity,
        ShapeEnvelope(
            (batch,),
            (4096,),
            ("observed",),
            (f"c{batch}-{language}-{arrival}",),
            (language,),
            ("all-revisions",),
        ),
        PopulationContract(
            language,
            arrival,
            duration,
            f"observed-c{batch}",
            "observed",
        ),
        ServiceContract(2.0, 0.005, 0.1),
        "2s-k5",
        32,
    )


def main() -> int:
    args = parse_args()
    c32_raw = json.loads(args.phase5_c32.read_text(encoding="utf-8"))
    c16_raw = json.loads(args.phase5_c16.read_text(encoding="utf-8"))
    failures = [
        event
        for event in c32_raw["events"]
        if not event["selected_vs_canonical"][
            "state_projection_token_exact"
        ]
    ]
    if len(failures) != 1:
        raise AssertionError("expected the frozen single c32 state failure")
    observed = failures[0]

    identity = ExecutionIdentity(
        "qwen3-asr-0.6b-frozen",
        "qwen3-asr-processor-frozen",
        "revtrace-phase6-runtime",
        "cuda12.8-vllm0.14-flash-attn",
        "float16",
        "sm86",
        "fp16-singleton-v1",
    )
    c16 = make_contract(
        identity,
        batch=16,
        language="mixed",
        arrival="poisson",
        duration="d60",
    )
    c32 = make_contract(
        identity,
        batch=32,
        language="Chinese",
        arrival="burst",
        duration="d120",
    )
    c64 = make_contract(
        identity,
        batch=64,
        language="mixed",
        arrival="episode-sync",
        duration="d10",
    )
    memory = ContractEvidenceMemory(
        failure_epsilon=1e-6, renewal_canaries=64
    )
    memory.store_certificate(
        c16,
        PositiveCertificate(
            c16.digest,
            0.05,
            0.0045,
            1497,
            identity.digest,
            1,
        ),
    )
    c32_failure = FailureRecord(
        "phase5-c32-s023-8",
        identity.digest,
        ExecutionSignature(
            32,
            4096,
            "observed",
            "c32-Chinese-burst",
            "Chinese",
            "all-revisions",
        ),
        float(observed["proposal_minimum_margin"]),
        "phase5-batched-projection",
        "phase5-canonical-projection",
        c32.digest,
    )
    memory.record_failure(c32_failure)

    sequence = [
        ("c16_initial", c16),
        ("c32_zh_burst", c32),
        ("c16_return", c16),
        ("c64_overload", c64),
    ]
    evidence_trace = []
    for label, item in sequence:
        decision = memory.enter(item)
        evidence_trace.append({"label": label, **asdict(decision)})

    ledger = EpochFencedCommitLedger()
    ledger.register("s0")
    ledger.change_contract()
    stale_contract = ledger.issue("s0", "old-contract")
    ledger.change_contract()
    contract_fence_rejected = not ledger.can_commit(stale_contract)
    stale_policy = ledger.issue("s0", "old-policy")
    ledger.change_policy()
    policy_fence_rejected = not ledger.can_commit(stale_policy)

    c64_admission = joint_risk_slo_admission(
        c64,
        predicted_p99_seconds=2.888937874697149,
        upper_risk=0.004988737202775151,
        reshape_candidates=((16, 1.4055951461195946),),
    )

    c16_margins = [
        float(event["proposal_minimum_margin"])
        for event in c16_raw["events"]
        if event["proposal_minimum_margin"] is not None
        and not event["terminal"]
    ]
    exact_scope_verify = sum(value <= 0.05 for value in c16_margins)
    global_floor_verify = sum(value <= 0.109376 for value in c16_margins)
    raw_queue_depths = tuple(range(1, 65))
    queue_regions = {
        "q1-8" if value <= 8 else
        "q9-16" if value <= 16 else
        "q17-32" if value <= 32 else "q33-64"
        for value in raw_queue_depths
    }

    gates = {
        "c32_enters_quarantine": (
            evidence_trace[1]["status"] == "quarantine_all_verify"
        ),
        "c32_failure_floor_covers_known_error": (
            float(evidence_trace[1]["failure_floor"])
            > float(observed["proposal_minimum_margin"])
        ),
        "c16_exact_return_requires_canary": (
            evidence_trace[2]["status"] == "exact_restore_canary"
            and not evidence_trace[2]["certified"]
        ),
        "cross_contract_positive_reuse_zero": (
            memory.unsafe_positive_reuse_attempts == 0
        ),
        "stale_contract_result_rejected": contract_fence_rejected,
        "stale_policy_result_rejected": policy_fence_rejected,
        "c64_reshaped": (
            c64_admission.level.value == "capacity_reshape"
            and c64_admission.admitted_concurrency == 16
        ),
    }
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 6 offline evidence-lifecycle gate",
        "evidence_tier": (
            "offline semantic replay over real Phase 5 events; not a serving "
            "performance result"
        ),
        "decision": (
            "PHASE6A_SEMANTIC_GATE_PASS"
            if all(gates.values())
            else "PHASE6A_SEMANTIC_GATE_FAIL"
        ),
        "source_failure": {
            "revision_id": observed["revision_id"],
            "margin": observed["proposal_minimum_margin"],
            "verified": observed["verified"],
        },
        "evidence_trace": evidence_trace,
        "gates": gates,
        "global_floor_boundary": {
            "events": len(c16_margins),
            "exact_scope_verifications": exact_scope_verify,
            "global_floor_verifications": global_floor_verify,
            "unnecessary_extra_if_global_floor": (
                global_floor_verify - exact_scope_verify
            ),
        },
        "fingerprint_fragmentation_proxy": {
            "raw_queue_depth_values": len(raw_queue_depths),
            "mechanism_regions": len(queue_regions),
            "note": "protocol-state proxy, not measured serving speedup",
        },
        "c64_admission": asdict(c64_admission),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"decision": payload["decision"], "gates": gates}))
    return 0 if all(gates.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
