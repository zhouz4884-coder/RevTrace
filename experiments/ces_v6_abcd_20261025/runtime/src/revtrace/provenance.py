"""Git-backed source provenance for immutable experiment runners."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo,
        stderr=subprocess.DEVNULL,
    )


def git_blob_sha256(repo: Path, commit: str, relative_path: str) -> str:
    data = _git(repo, "show", f"{commit}:{relative_path}")
    return hashlib.sha256(data).hexdigest()


def commits_with_blob_sha256(
    repo: Path,
    relative_path: str,
    expected_sha256: str,
) -> list[str]:
    revisions = _git(
        repo,
        "rev-list",
        "--all",
        "--",
        relative_path,
    ).decode("utf-8").splitlines()
    return [
        revision
        for revision in revisions
        if git_blob_sha256(repo, revision, relative_path) == expected_sha256
    ]


def resolve_runner_provenance(
    *,
    repo: Path,
    runner_path: Path,
    raw_payload: dict[str, Any],
) -> dict[str, Any]:
    """Resolve the exact Git blob while preserving at-run evidence limits."""

    repo = repo.resolve()
    runner_path = runner_path.resolve()
    relative = runner_path.relative_to(repo).as_posix()
    environment = raw_payload.get("environment", {})
    recorded_sha = environment.get("runner_sha256")
    recorded_commit = str(environment.get("code_commit", ""))
    if recorded_sha and len(str(recorded_sha)) != 64:
        raise ValueError(f"invalid recorded runner SHA for {relative}")

    if (
        recorded_sha
        and len(recorded_commit) == 40
        and git_blob_sha256(repo, recorded_commit, relative) == recorded_sha
    ):
        return {
            "runner_sha256": recorded_sha,
            "git_commit": recorded_commit,
            "runner_path": relative,
            "provenance_kind": "AT_RUN_SHA_AND_COMMIT_ATTESTED",
            "at_run_source_attested": True,
        }

    if recorded_sha:
        matches = commits_with_blob_sha256(repo, relative, recorded_sha)
        if len(matches) != 1:
            raise ValueError(
                f"recorded runner SHA for {relative} maps to {matches}"
            )
        return {
            "runner_sha256": recorded_sha,
            "git_commit": matches[0],
            "runner_path": relative,
            "provenance_kind": "AT_RUN_SHA_COMMIT_RECOVERED_FROM_GIT",
            "at_run_source_attested": True,
            "recorded_commit_label": recorded_commit or None,
        }

    current_sha = hashlib.sha256(runner_path.read_bytes()).hexdigest()
    matches = commits_with_blob_sha256(repo, relative, current_sha)
    if len(matches) != 1:
        raise ValueError(
            f"retrospective runner snapshot for {relative} maps to {matches}"
        )
    return {
        "runner_sha256": current_sha,
        "git_commit": matches[0],
        "runner_path": relative,
        "provenance_kind": "RETROSPECTIVE_REPOSITORY_SNAPSHOT",
        "at_run_source_attested": False,
        "recorded_commit_label": recorded_commit or None,
        "claim_boundary": (
            "The raw artifact did not record a runner SHA. This exact Git "
            "snapshot is the retrospectively frozen analysis source, not an "
            "at-run cryptographic attestation."
        ),
    }
