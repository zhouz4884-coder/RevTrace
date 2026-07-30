#!/usr/bin/env python3
"""Auditable compatibility patch for vLLM batch-invariant log-softmax.

The installed vLLM runtime rejects ``aten::_log_softmax(...,
half_to_float=True)``.  vLLM's sampler intentionally requests that operation
when it computes FP32 log probabilities from FP16 logits.  This patch preserves
those semantics by casting the input to FP32 before invoking vLLM's
batch-invariant Triton log-softmax implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import py_compile
from pathlib import Path


ORIGINAL = """def _log_softmax_batch_invariant(input, dim, _half_to_float):
    assert not _half_to_float, "not implemented"
    return log_softmax(input, dim=dim)
"""

PATCHED = """def _log_softmax_batch_invariant(input, dim, _half_to_float):
    # Match aten::_log_softmax half_to_float semantics used by vLLM's sampler:
    # promote FP16/BF16 logits before the deterministic Triton reduction.
    if _half_to_float:
        input = input.to(torch.float32)
    return log_softmax(input, dim=dim)
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_runtime() -> Path:
    spec = importlib.util.find_spec(
        "vllm.model_executor.layers.batch_invariant"
    )
    if spec is None or spec.origin is None:
        raise RuntimeError("cannot locate vLLM batch_invariant.py")
    return Path(spec.origin).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    target = locate_runtime()
    before_sha = sha256(target)
    text = target.read_text(encoding="utf-8")
    status: str
    if PATCHED in text:
        status = "already_patched"
    elif ORIGINAL in text:
        backup = target.with_suffix(target.suffix + ".revtrace.orig")
        if not backup.exists():
            backup.write_bytes(target.read_bytes())
        target.write_text(text.replace(ORIGINAL, PATCHED, 1), encoding="utf-8")
        status = "patched"
    else:
        raise RuntimeError(
            "installed vLLM source is neither the audited original nor the "
            "RevTrace-patched implementation; refusing to edit"
        )

    py_compile.compile(str(target), doraise=True)
    after_sha = sha256(target)
    payload = {
        "schema_version": 1,
        "status": status,
        "target": str(target),
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "original_snippet_sha256": hashlib.sha256(
            ORIGINAL.encode("utf-8")
        ).hexdigest(),
        "patched_snippet_sha256": hashlib.sha256(
            PATCHED.encode("utf-8")
        ).hexdigest(),
        "semantic_contract": (
            "For half_to_float=True, cast the input logits to float32 before "
            "the batch-invariant log-softmax reduction."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
