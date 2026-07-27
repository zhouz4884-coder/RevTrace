from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "results" / "phase1" / "deployed_v1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def final_json_line(path: Path) -> dict[str, Any]:
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise ValueError(f"no JSON summary line in {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    config = load_json(ROOT / "configs" / "revtrace_deployed_gate.json")
    raw = RESULT_ROOT / "raw"
    logs = RESULT_ROOT / "logs"
    worksteal = {
        "Qwen3-ASR-0.6B": load_json(
            raw / "dual-gpu-worksteal-qwen3-asr-0.6b.json"
        ),
        "Qwen3-ASR-1.7B": load_json(
            raw / "dual-gpu-worksteal-qwen3-asr-1.7b.json"
        ),
    }
    stress = {
        "Qwen3-ASR-0.6B": load_json(
            raw / "flip-stress-qwen3-asr-0.6b.json"
        ),
        "Qwen3-ASR-1.7B": load_json(
            raw / "flip-stress-qwen3-asr-1.7b.json"
        ),
    }
    streaming = {
        "Qwen3-ASR-0.6B": final_json_line(
            logs
            / "dual-gpu-streaming-Qwen3-ASR-0.6B-fp16-d30-c16.log"
        ),
        "Qwen3-ASR-1.7B": final_json_line(
            logs
            / "dual-gpu-streaming-Qwen3-ASR-1.7B-fp16-d30-c16.log"
        ),
    }
    gates = config["gates"]
    rows = []
    all_service = True
    all_stress = True
    for model in config["models"]:
        summary = worksteal[model]["summary"]
        baseline = streaming[model]
        stress_summary = stress[model]["summary"]
        service_pass = (
            summary["deployed_two_gpu_wall_speedup"]
            >= gates["minimum_wall_speedup"]
            and summary["slo_goodput_speedup"]
            >= gates["minimum_slo_goodput_speedup"]
            and summary["output_violation_events"]
            <= gates["maximum_output_violations"]
            and summary["state_projection_violation_events"]
            <= gates["maximum_state_projection_violations"]
            and summary["stale_or_replayed_result_events"]
            <= gates["maximum_stale_or_replayed_commits"]
        )
        stress_pass = (
            stress_summary["mismatch_rows"]
            >= gates["minimum_stress_mismatches_per_model"]
            and stress_summary["false_safe_rows"]
            <= gates["maximum_stress_false_safe_rows"]
        )
        all_service = all_service and service_pass
        all_stress = all_stress and stress_pass
        rows.append(
            {
                "model": model,
                "event_count": summary["event_count"],
                "verification_fraction": summary[
                    "verification_fraction"
                ],
                "wall_speedup": summary[
                    "deployed_two_gpu_wall_speedup"
                ],
                "gpu_normalized_speedup": summary[
                    "gpu_normalized_throughput_speedup"
                ],
                "slo_goodput_speedup": summary["slo_goodput_speedup"],
                "state_entry_p99_seconds": summary[
                    "state_entry_latency_seconds_p99"
                ],
                "terminal_verifier_p95_seconds": summary[
                    "terminal_verifier_wait_seconds_p95"
                ],
                "deadline_miss_rate": summary[
                    "state_entry_deadline_miss_rate"
                ],
                "output_violations": summary[
                    "output_violation_events"
                ],
                "state_violations": summary[
                    "state_projection_violation_events"
                ],
                "stale_commits": summary[
                    "stale_or_replayed_result_events"
                ],
                "stress_target_rows": stress_summary[
                    "target_row_evaluations"
                ],
                "stress_mismatches": stress_summary["mismatch_rows"],
                "stress_false_safe": stress_summary["false_safe_rows"],
                "worksteal_wall_improvement": (
                    summary["deployed_two_gpu_wall_speedup"]
                    / baseline["deployed_two_gpu_wall_speedup"]
                    - 1.0
                ),
                "worksteal_p99_reduction": (
                    1.0
                    - summary["state_entry_latency_seconds_p99"]
                    / baseline["state_entry_latency_seconds_p99"]
                ),
                "service_gate": "PASS" if service_pass else "FAIL",
                "stress_gate": "PASS" if stress_pass else "FAIL",
            }
        )

    bi_logs = sorted(logs.glob("bi-fa-*.log"))
    bi_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in bi_logs
    )
    batch_invariant_compat_failure = (
        'assert not _half_to_float, "not implemented"' in bi_text
        and "EngineDeadError" in bi_text
    )
    decision = (
        "DEPLOYED_SYSTEM_GATE_PASS_"
        "DETERMINISTIC_CERTIFICATE_UNRESOLVED"
        if all_service and all_stress and batch_invariant_compat_failure
        else "DEPLOYED_SYSTEM_GATE_FAIL"
    )
    files = sorted(
        path
        for path in RESULT_ROOT.rglob("*")
        if path.is_file() and path.name not in {"summary.json", "MANIFEST.json"}
    )
    manifest = {
        "schema_version": 1,
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    payload = {
        "schema_version": 1,
        "decision": decision,
        "rows": rows,
        "gates": {
            "deployed_service": "PASS" if all_service else "FAIL",
            "flip_rich_stress": "PASS" if all_stress else "FAIL",
            "generic_wsir_novelty": "REJECTED_BY_D0",
            "vllm_batch_invariant_qwen3_asr_compatibility": (
                "FAIL"
                if batch_invariant_compat_failure
                else "NOT_REPRODUCED"
            ),
            "deterministic_margin_certificate": "NOT_ESTABLISHED",
            "cascading_speculation": (
                "NO_GO_NO_CROSS_CHUNK_LAG_IN_BASELINE"
                if all(
                    row["intermediate_verifier_wait_seconds_p95"] < 2.0
                    for row in streaming.values()
                )
                else "REQUIRES_FURTHER_GATE"
            ),
        },
        "boundaries": config["claim_boundaries"],
        "manifest_sha256": hashlib.sha256(
            json.dumps(
                manifest, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest(),
    }
    write_json(RESULT_ROOT / "summary.json", payload)
    write_json(RESULT_ROOT / "MANIFEST.json", manifest)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if decision.startswith("DEPLOYED_SYSTEM_GATE_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
