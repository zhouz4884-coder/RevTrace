"""Helpers for binding experiment artifacts to the patched vLLM runtime."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


def batch_invariant_runtime_path() -> Path:
    spec = importlib.util.find_spec(
        "vllm.model_executor.layers.batch_invariant"
    )
    if spec is None or spec.origin is None:
        raise RuntimeError("cannot locate vLLM batch_invariant.py")
    return Path(spec.origin).resolve()


def batch_invariant_runtime_sha256() -> str:
    path = batch_invariant_runtime_path()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_runtime_sha256(payload: dict, current_sha256: str) -> None:
    recorded = payload.get("environment", {}).get(
        "batch_invariant_runtime_sha256"
    )
    if not recorded:
        raise ValueError(
            "cross-lane artifact does not record batch-invariant runtime hash"
        )
    if recorded != current_sha256:
        raise ValueError(
            "cross-lane artifact batch-invariant runtime hash does not match "
            "the deployed runtime"
        )
