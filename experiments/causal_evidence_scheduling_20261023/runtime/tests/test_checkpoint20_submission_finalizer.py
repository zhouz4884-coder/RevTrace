import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE_RESULTS = REPO / "results" / "checkpoint20_holdback_authority"
FINALIZER = REPO / "scripts" / "finalize_checkpoint20_submission.py"
ARTIFACT = REPO / "artifact" / "checkpoint20-submission-closure-v2"
ARTIFACT_VERIFIER = (
    REPO / "scripts" / "verify_checkpoint20_submission_artifact.py"
)


def isolated_results(tmp_path: Path) -> Path:
    target = tmp_path / "checkpoint20_holdback_authority"
    shutil.copytree(SOURCE_RESULTS, target)
    binding_path = target / "contract_bindings.json"
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    for binding in payload["bindings"].values():
        source_name = Path(binding["path"]).name
        binding["path"] = str((target / source_name).resolve())
    binding_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def run_finalizer(results: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "--results-dir",
            str(results),
            "--report",
            str(results / "report.md"),
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def test_finalizer_accepts_untampered_isolated_evidence(
    tmp_path: Path,
) -> None:
    results = isolated_results(tmp_path)
    completed = run_finalizer(results)
    assert completed.returncode == 0, completed.stderr
    assert "REVTRACE_EXPERIMENTAL_EVIDENCE_COMPLETE" in completed.stdout


def test_finalizer_rejects_raw_result_tampering(tmp_path: Path) -> None:
    results = isolated_results(tmp_path)
    quality = results / "deployed_b12_quality_32x2.json"
    quality.write_bytes(quality.read_bytes() + b" ")
    completed = run_finalizer(results)
    assert completed.returncode != 0
    assert "raw result digest mismatch" in completed.stderr


def test_finalizer_rejects_missing_binding_role(tmp_path: Path) -> None:
    results = isolated_results(tmp_path)
    binding_path = results / "contract_bindings.json"
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    payload["bindings"].pop("resume_lineage")
    binding_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    completed = run_finalizer(results)
    assert completed.returncode != 0
    assert "binding role mismatch" in completed.stderr


def run_artifact_verifier(
    artifact: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ARTIFACT_VERIFIER), str(artifact)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def test_artifact_verifier_accepts_exact_file_set() -> None:
    completed = run_artifact_verifier(ARTIFACT)
    assert completed.returncode == 0, completed.stderr
    assert "CHECKPOINT20_ARTIFACT_VERIFY_PASS" in completed.stdout


def test_artifact_verifier_rejects_extra_file(tmp_path: Path) -> None:
    target = tmp_path / "artifact"
    shutil.copytree(ARTIFACT, target)
    (target / "unexpected.txt").write_text("not declared", encoding="utf-8")
    completed = run_artifact_verifier(target)
    assert completed.returncode != 0
    assert "artifact file-set mismatch" in completed.stderr
