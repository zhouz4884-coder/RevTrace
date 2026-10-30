"""Shared final-record guards; no writes, compilation, publication or QA claims."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_output_path(path: Path, root: Path, suffix: str) -> Path:
    target = path.resolve()
    if not target.is_relative_to(root.resolve()) or target.suffix != suffix:
        raise ValueError(f"Output must be a {suffix} file inside {root}")
    if target.exists():
        raise ValueError(f"Refusing to overwrite existing output: {target}")
    if not target.parent.is_dir():
        raise ValueError(f"Output parent must already exist: {target.parent}")
    return target


def validate_final_record(record_path: Path, release: Path, archive: Path, project_root: Path) -> dict:
    """Bind the exact selected release AND archive before delivery mutates files."""
    record = json.loads(record_path.read_bytes())
    release, archive, project_root = release.resolve(), archive.resolve(), project_root.resolve()
    if record.get("gate") != "PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA":
        raise ValueError("Final release record has not passed both QA gates")
    expected = {
        "release": release.relative_to(project_root).as_posix(),
        "archive": archive.relative_to(project_root).as_posix(),
        "pdf_sha256": sha((release / "main.pdf").read_bytes()),
        "archive_sha256": sha(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise ValueError(f"Final release record mismatch: {key}")
    return record
