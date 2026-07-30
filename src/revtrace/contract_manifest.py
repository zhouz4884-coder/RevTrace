"""Content-addressed experiment contracts for the checkpoint-20 mechanism."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1


def canonical_json(value: Any) -> bytes:
    """Return the unique UTF-8 representation used by all contract digests."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprint_files(root: Path, relative_paths: Iterable[str]) -> dict[str, Any]:
    """Hash an explicit, ordered model/runtime file set.

    The caller chooses the files.  Missing inputs fail closed so a contract
    cannot silently degrade from content identity to a path-only label.
    """

    root = root.resolve()
    entries: dict[str, dict[str, Any]] = {}
    for relative in sorted(set(relative_paths)):
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"fingerprint path escapes root: {relative}") from exc
        if not path.is_file():
            raise FileNotFoundError(path)
        entries[relative.replace("\\", "/")] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    if not entries:
        raise ValueError("at least one fingerprint file is required")
    return {
        "files": entries,
        "content_digest": digest_value(entries),
    }


def mechanism_manifest(
    *,
    model_name: str,
    model_fingerprint: dict[str, Any],
    data_manifest_sha256: str,
    authority_runtime_sha256: str,
    duration_seconds: int,
    checkpoint_seconds: int,
    margin_threshold: float,
    proposer_dtype: str = "float16",
    proposer_batch_size: int = 12,
    authority_dtype: str = "float16",
    authority_batch_size: int = 12,
    audio_construction: str = "distinct_utterance_sequence_v1",
    checkpoint_payload: str = "terminal_state_projection_v1",
    low_margin_policy: str = "provisional_holdback_v1",
    maximum_model_length: int = 4096,
) -> dict[str, Any]:
    """Build the immutable mechanism identity shared by all evidence roles."""

    if duration_seconds <= 0 or checkpoint_seconds <= 0:
        raise ValueError("duration and checkpoint must be positive")
    if duration_seconds % checkpoint_seconds:
        raise ValueError("checkpoint must divide duration")
    if proposer_batch_size <= 0 or authority_batch_size <= 0:
        raise ValueError("batch sizes must be positive")
    for name, value in (
        ("data_manifest_sha256", data_manifest_sha256),
        ("authority_runtime_sha256", authority_runtime_sha256),
    ):
        if len(value) != 64:
            raise ValueError(f"{name} must be a SHA-256 digest")
    if not model_fingerprint.get("content_digest"):
        raise ValueError("model content fingerprint is required")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "model": {
            "name": model_name,
            "fingerprint": model_fingerprint,
        },
        "data": {
            "manifest_sha256": data_manifest_sha256,
            "audio_construction": audio_construction,
        },
        "revision_contract": {
            "duration_seconds": duration_seconds,
            "checkpoint_seconds": checkpoint_seconds,
            "checkpoint_payload": checkpoint_payload,
            "maximum_model_length": maximum_model_length,
        },
        "proposer": {
            "dtype": proposer_dtype,
            "ordinary_batch_size": proposer_batch_size,
        },
        "risk_policy": {
            "minimum_margin_threshold": float(margin_threshold),
            "low_margin_policy": low_margin_policy,
            "margin_is_deterministic_certificate": False,
        },
        "authority": {
            "dtype": authority_dtype,
            "fixed_batch_size": authority_batch_size,
            "runtime_sha256": authority_runtime_sha256,
            "checkpoint_and_terminal_only": True,
        },
    }
    return {
        "mechanism": manifest,
        "mechanism_digest": digest_value(manifest),
    }


def execution_binding(
    *,
    mechanism_digest: str,
    role: str,
    runner_sha256: str,
    raw_result_sha256: str,
    execution_profile: dict[str, Any],
) -> dict[str, Any]:
    """Bind one immutable result to the shared mechanism and runner role."""

    for name, value in (
        ("mechanism_digest", mechanism_digest),
        ("runner_sha256", runner_sha256),
        ("raw_result_sha256", raw_result_sha256),
    ):
        if len(value) != 64:
            raise ValueError(f"{name} must be a SHA-256 digest")
    body = {
        "schema_version": SCHEMA_VERSION,
        "mechanism_digest": mechanism_digest,
        "role": role,
        "runner_sha256": runner_sha256,
        "raw_result_sha256": raw_result_sha256,
        "execution_profile": execution_profile,
    }
    return {**body, "execution_digest": digest_value(body)}


def validate_binding(binding: dict[str, Any], *, raw_path: Path) -> None:
    """Fail closed when a binding or its raw result has changed."""

    supplied = dict(binding)
    execution_digest = supplied.pop("execution_digest", None)
    if execution_digest != digest_value(supplied):
        raise ValueError(f"execution digest mismatch for {raw_path}")
    actual = sha256_file(raw_path)
    if actual != binding.get("raw_result_sha256"):
        raise ValueError(f"raw result digest mismatch for {raw_path}")

