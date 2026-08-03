#!/usr/bin/env python3
"""Freeze a machine-auditable R9.E model/runtime/policy contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def tree_digest(root: Path) -> tuple[str, list[dict[str, Any]]]:
    rows = []
    aggregate = hashlib.sha256()
    for path in sorted(value for value in root.rglob("*") if value.is_file()):
        relative = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size
        rows.append({"path": relative, "bytes": size, "sha256": digest})
        aggregate.update(f"{relative}\0{size}\0{digest}\n".encode("utf-8"))
    return aggregate.hexdigest(), rows


def canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    import torch
    import transformers

    model_digest, model_files = tree_digest(args.model)
    sources = [
        "src/revtrace/dgft.py",
        "src/revtrace/causal_scheduler.py",
        "src/revtrace/online_coordinator.py",
        "scripts/remote/run_r9_dgft_service.py",
        "scripts/remote/run_r9_segment_oracle.py",
        "scripts/remote/run_r9_coverage_fallback.py",
        "scripts/remote/whisper_batched_executor.py",
    ]
    source_digests = {
        relative: sha256_file(args.repo / relative) for relative in sources
    }
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    runtime = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "gpu_names": [
            torch.cuda.get_device_name(index)
            for index in range(torch.cuda.device_count())
        ],
    }
    body = {
        "schema_version": 1,
        "study": "R9.E online evidence closure contract",
        "model_name": args.model_name,
        "model_tree_sha256": model_digest,
        "model_files": model_files,
        "manifest_sha256": sha256_file(args.manifest),
        "policy_sha256": sha256_file(args.policy),
        "policy_version": policy["policy_version"],
        "policy": policy["policy"],
        "source_sha256": source_digests,
        "runtime": runtime,
        "frozen_service_budget": {
            "sessions": 16,
            "duration_seconds": 90,
            "window_seconds": 10,
            "concurrency": 16,
            "proposer_max_steps": 32,
            "display_slo_seconds": 1.9,
            "commit_slo_seconds": 36.0,
            "authority_audio_amplification_ceiling": 1.2,
        },
    }
    body["contract_digest"] = canonical_digest(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "model": args.model_name,
        "contract_digest": body["contract_digest"],
        "model_files": len(model_files),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
