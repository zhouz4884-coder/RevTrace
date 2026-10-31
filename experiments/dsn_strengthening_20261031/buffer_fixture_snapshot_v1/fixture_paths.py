"""Cross-platform frozen POSIX paths plus live Linux symlink containment gate."""
from pathlib import Path, PurePosixPath

DISK = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
RESULTS = DISK + "/results"


def frozen_path(value, *, parent=RESULTS):
    value = str(value)
    if "\\" in value or "\0" in value or any(part in (".", "..") for part in value.split("/")):
        raise ValueError("frozen raw path contains an alias or traversal component")
    path, base = PurePosixPath(value), PurePosixPath(parent)
    if not path.is_absolute() or not path.is_relative_to(base) or path == base or path.as_posix() != value:
        raise ValueError("frozen raw path escapes the exact designated results root")
    return path


def _reject_existing_links(path):
    for part in reversed((path, *path.parents)):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("raw path has a symlink or junction ancestor")


def validate_live_under(config, out, *, disk_root):
    """disk_root is injectable only for CPU tests; production wrapper fixes it."""
    disk = Path(disk_root)
    if not disk.is_absolute() or not disk.is_dir():
        raise ValueError("designated experiment disk is not an existing absolute directory")
    _reject_existing_links(disk)
    verified_disk = disk.resolve(strict=True)
    if verified_disk != disk:
        raise ValueError("designated disk has an unresolved alias")
    results = disk / "results"
    if not results.is_dir():
        raise ValueError("designated results directory must already exist")
    _reject_existing_links(results)
    expected = Path(config["raw_result_location"])
    raw_root = Path(config["frozen_raw_root"])
    actual = Path(out)
    for candidate in (expected, raw_root, actual):
        if not candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("raw output must use a traversal-free absolute path")
        _reject_existing_links(candidate)
    if expected != raw_root / "cells" / config["cell_id"] or actual != expected:
        raise ValueError("--out differs from the frozen exact cell output path")
    resolved_results = results.resolve(strict=True)
    resolved_root, resolved_out = raw_root.resolve(), actual.resolve()
    if (not resolved_root.is_relative_to(resolved_results) or resolved_root == resolved_results or
            not resolved_out.is_relative_to(resolved_root) or resolved_out == resolved_root or
            not resolved_out.is_relative_to(verified_disk)):
        raise ValueError("resolved raw output escapes the verified experiment disk/frozen run root")
    return resolved_out


def validate_live_output(config, out):
    # First use target POSIX semantics even if the caller is accidentally on
    # Windows. A Linux path must not become a Windows drive-relative pathname.
    root = frozen_path(config["frozen_raw_root"])
    expected = frozen_path(config["raw_result_location"], parent=root.as_posix())
    if expected != root / "cells" / config["cell_id"] or str(out) != expected.as_posix():
        raise ValueError("--out is not the exact frozen POSIX cell path")
    return validate_live_under(config, out, disk_root=DISK)
