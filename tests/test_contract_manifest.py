from pathlib import Path

import pytest

from revtrace.contract_manifest import (
    digest_value,
    execution_binding,
    mechanism_manifest,
    sha256_file,
    validate_binding,
)


def test_mechanism_digest_is_order_independent() -> None:
    assert digest_value({"b": 2, "a": 1}) == digest_value({"a": 1, "b": 2})


def test_binding_fails_closed_after_raw_mutation(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    raw.write_text('{"value":1}\n', encoding="utf-8")
    binding = execution_binding(
        mechanism_digest="a" * 64,
        role="test",
        runner_sha256="b" * 64,
        raw_result_sha256=sha256_file(raw),
        execution_profile={"shape": 12},
    )
    validate_binding(binding, raw_path=raw)
    raw.write_text('{"value":2}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="raw result digest mismatch"):
        validate_binding(binding, raw_path=raw)


def test_mechanism_requires_content_identity() -> None:
    with pytest.raises(ValueError, match="model content fingerprint"):
        mechanism_manifest(
            model_name="model",
            model_fingerprint={},
            data_manifest_sha256="a" * 64,
            authority_runtime_sha256="b" * 64,
            duration_seconds=120,
            checkpoint_seconds=20,
            margin_threshold=0.031251,
        )
