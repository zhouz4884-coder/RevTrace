"""Validate the frozen TC host-side transaction-overhead artifacts."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "run_tc_transaction_overhead.py"
RESULT_PATH = ROOT / "results" / "tc_transaction_overhead" / "result.json"
RAW_CSV_PATH = RESULT_PATH.with_name("raw_samples.csv")
SUMMARY_CSV_PATH = RESULT_PATH.with_name("summary.csv")
REPORT_PATH = ROOT / "Paper_TC" / "reports" / "TRANSACTION_OVERHEAD.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("tc_overhead_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load transaction-overhead runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    runner = load_runner()
    payload = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    # The result JSON is serialized with ``sort_keys=True`` for stable diffs,
    # so restore the contract order before calling the runner's in-memory
    # schema check.
    ordered_payload = dict(payload)
    ordered_payload["summary"] = {
        variant: payload["summary"][variant] for variant in runner.VARIANTS
    }
    runner.validate_result_schema(ordered_payload)

    with RAW_CSV_PATH.open(encoding="utf-8", newline="") as stream:
        raw_rows = list(csv.DictReader(stream))
    with SUMMARY_CSV_PATH.open(encoding="utf-8", newline="") as stream:
        summary_rows = list(csv.DictReader(stream))

    if len(raw_rows) != len(payload["raw_samples"]):
        raise AssertionError("raw CSV and JSON sample counts differ")
    if [row["variant"] for row in summary_rows] != list(runner.VARIANTS):
        raise AssertionError("summary CSV variant order differs from contract")
    recomputed = runner.summarize(payload["raw_samples"])
    for variant in runner.VARIANTS:
        for metric, expected in payload["summary"][variant].items():
            actual = recomputed[variant][metric]
            if not math.isclose(float(actual), float(expected), rel_tol=1e-12):
                raise AssertionError(
                    f"summary mismatch for {variant}.{metric}: "
                    f"{actual} != {expected}"
                )

    source = ROOT / payload["environment"]["production_source"]
    if runner.sha256_file(source) != payload["environment"]["production_source_sha256"]:
        raise AssertionError("production dgft.py changed after the benchmark")
    report = REPORT_PATH.read_text(encoding="utf-8")
    if payload["conclusion"]["decision"] not in report:
        raise AssertionError("report omits the frozen decision")

    print(json.dumps({
        "status": "PASS",
        "schema_version": payload["schema_version"],
        "raw_sample_rows": len(raw_rows),
        "variants": list(runner.VARIANTS),
        "production_source_sha256": payload["environment"][
            "production_source_sha256"
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
