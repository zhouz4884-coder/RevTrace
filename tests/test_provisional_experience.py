import importlib.util
from pathlib import Path


RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "remote"
    / "run_deployed_checkpoint20_quality.py"
)
SPEC = importlib.util.spec_from_file_location("deployed_quality", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_append_only_resolution_has_zero_overwrite() -> None:
    assert (
        MODULE.provisional_overwrite_fraction(
            "the quick fox",
            "the quick fox jumps",
            "English",
        )
        == 0.0
    )


def test_overwrite_is_bounded() -> None:
    value = MODULE.provisional_overwrite_fraction(
        "short",
        "a completely different and longer sentence",
        "English",
    )
    assert value == 1.0


def test_chinese_append_is_not_revision() -> None:
    assert MODULE.provisional_overwrite_fraction("配置", "配置文件", "Chinese") == 0.0
