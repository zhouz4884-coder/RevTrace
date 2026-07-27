from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "results" / "phase1" / "deployed_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    files = sorted(
        path
        for path in RESULT_ROOT.rglob("*")
        if path.is_file()
        and path.name not in {"MANIFEST.json", "SOURCE_MANIFEST.json"}
    )
    manifest = {
        "schema_version": 1,
        "scope": "standalone RevTrace Phase 1 deployed evidence",
        "source_commit": "dc8887dd538cc3d9916f441b38ebd909e92db97e",
        "files": [
            {
                "path": path.relative_to(RESULT_ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    with (RESULT_ROOT / "MANIFEST.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"files": len(files), "root": str(RESULT_ROOT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
