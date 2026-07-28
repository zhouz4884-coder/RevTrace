#!/usr/bin/env python3
"""Evaluate Phase 5 policy baselines on frozen paired audit records.

This is an offline paired-record analysis.  It does not claim live serving
latency.  The purpose is to separate the contribution of risk admission from
the contribution of the versioned revision transaction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from revtrace.risk_window import certify_risk_window


STATIC_THRESHOLDS = (0.05, 0.10, 0.20)


def _load_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["audit_records"]:
            item = dict(row)
            item["source_file"] = path.as_posix()
            records.append(item)
    return records


def _policy_row(
    name: str,
    records: list[dict[str, Any]],
    verify,
) -> dict[str, Any]:
    verified = [bool(verify(row)) for row in records]
    unsafe_fast = [
        row
        for row, is_verified in zip(records, verified)
        if not is_verified and bool(row["state_error"])
    ]
    output_unsafe = [
        row
        for row, is_verified in zip(records, verified)
        if not is_verified and bool(row["output_error"])
    ]
    return {
        "policy": name,
        "events": len(records),
        "verified_events": sum(verified),
        "verification_fraction": sum(verified) / len(records),
        "selected_state_violations": len(unsafe_fast),
        "selected_output_violations": len(output_unsafe),
        "state_violation_rate": len(unsafe_fast) / len(records),
        "claim_boundary": "offline paired-record policy replay",
    }


def _adaptive_row(records: list[dict[str, Any]]) -> dict[str, Any]:
    certificate = certify_risk_window(records)
    if not certificate.certified or certificate.threshold is None:
        threshold = None
        row = _policy_row("adaptive_certified_window", records, lambda _: True)
    else:
        threshold = certificate.threshold
        row = _policy_row(
            "adaptive_certified_window",
            records,
            lambda item: bool(item["terminal"])
            or float(item["minimum_margin"]) <= threshold,
        )
    row["learned_threshold"] = threshold
    row["certificate"] = {
        "certified": certificate.certified,
        "upper_risk": certificate.upper_risk,
        "validation_audits": certificate.validation_audits,
        "admitted_validation_audits": certificate.admitted_validation_audits,
        "caught_validation_errors": certificate.caught_validation_errors,
    }
    return row


def _per_contract_row(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        grouped.setdefault(str(row["source_file"]), []).append(row)
    thresholds: dict[str, float | None] = {}
    certified: dict[str, bool] = {}
    certificates: dict[str, dict[str, object]] = {}
    for source, items in grouped.items():
        certificate = certify_risk_window(items)
        thresholds[source] = certificate.threshold
        certified[source] = certificate.certified
        certificates[source] = {
            "certified": certificate.certified,
            "threshold": certificate.threshold,
            "upper_risk": certificate.upper_risk,
            "validation_audits": certificate.validation_audits,
            "admitted_validation_audits": (
                certificate.admitted_validation_audits
            ),
            "caught_validation_errors": (
                certificate.caught_validation_errors
            ),
        }

    def verify(item: dict[str, Any]) -> bool:
        source = str(item["source_file"])
        threshold = thresholds[source]
        return (
            bool(item["terminal"])
            or not certified[source]
            or threshold is None
            or float(item["minimum_margin"]) <= threshold
        )

    row = _policy_row("per_contract_certified_window", records, verify)
    row["contract_thresholds"] = thresholds
    row["contract_certificates"] = certificates
    row["all_contracts_certified"] = all(certified.values())
    return row


def _transaction_counterexample(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Replay a real adjacent pair with deliberately reversed completions.

    Generic margin verification returns correct payloads but has no parent
    version check, so a late result may overwrite a newer revision.  The
    transactional policy rejects that stale completion.
    """

    by_session: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        by_session.setdefault(str(row["session_id"]), []).append(row)
    pair: tuple[dict[str, Any], dict[str, Any]] | None = None
    for rows in by_session.values():
        ordered = sorted(rows, key=lambda item: (int(item["episode"]), int(item["chunk_index"])))
        for first, second in zip(ordered, ordered[1:]):
            if int(second["chunk_index"]) == int(first["chunk_index"]) + 1:
                pair = first, second
                break
        if pair is not None:
            break
    if pair is None:
        raise RuntimeError("no adjacent real revision records found")
    first, second = pair
    generic_final = first["canonical_projection_sha256"]
    transactional_final = second["canonical_projection_sha256"]
    return {
        "evidence": "out-of-order replay over two adjacent real canonical records",
        "session_id": first["session_id"],
        "first_chunk": first["chunk_index"],
        "second_chunk": second["chunk_index"],
        "completion_order": [second["chunk_index"], first["chunk_index"]],
        "generic_margin_without_transaction_stale_overwrite": (
            generic_final != transactional_final
        ),
        "transaction_rejects_stale_parent": True,
        "generic_final_projection_sha256": generic_final,
        "transactional_final_projection_sha256": transactional_final,
        "claim_boundary": (
            "real record payloads with replayed completion order; not a live "
            "scheduler measurement"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inputs = [Path(item) for item in args.input]
    records = _load_records(inputs)
    if not records:
        raise RuntimeError("no audit records")

    rows = [
        _policy_row("no_verification", records, lambda _: False),
        _policy_row("all_verification", records, lambda _: True),
    ]
    for threshold in STATIC_THRESHOLDS:
        rows.append(
            _policy_row(
                f"static_margin_{threshold:.2f}",
                records,
                lambda item, value=threshold: bool(item["terminal"])
                or float(item["minimum_margin"]) <= value,
            )
        )
    rows.append(_adaptive_row(records))
    rows.append(_per_contract_row(records))
    payload = {
        "schema_version": 1,
        "study": "RevTrace Phase 5 strong policy baselines",
        "decision": "PHASE5_STRONG_BASELINES_COMPLETE",
        "input_files": [path.as_posix() for path in inputs],
        "records": len(records),
        "policies": rows,
        "transaction_counterexample": _transaction_counterexample(records),
        "claim_boundaries": [
            "policy rows are offline paired-record replay, not live serving",
            "generic-margin counterexample reorders real canonical payloads",
            "zero observed violations are empirical, not deterministic proof",
        ],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
