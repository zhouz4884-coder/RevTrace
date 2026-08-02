#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 EVIDENCE_ROOT OUTPUT_TAR_GZ" >&2
  exit 2
fi

evidence_root=$(realpath "$1")
archive=$(realpath -m "$2")
manifest="$evidence_root/MANIFEST.json"
file_list=$(mktemp)
python_bin=${PYTHON_BIN:-python3}
trap 'rm -f "$file_list"' EXIT

if [[ ! -f "$manifest" ]]; then
  echo "missing manifest: $manifest" >&2
  exit 2
fi

"$python_bin" - "$manifest" "$file_list" <<'PY'
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
output = Path(sys.argv[2])
payload = json.loads(manifest.read_text(encoding="utf-8"))
selected = ["MANIFEST.json"]
selected.extend(row["path"] for row in payload["files"] if not row["remote_only"])
with output.open("wb") as stream:
    for item in selected:
        stream.write(item.encode("utf-8") + b"\0")
print(
    f"packaging {len(selected)} files; "
    f"omitting {payload['remote_only_file_count']} content-addressed remote-only files"
)
PY

mkdir -p "$(dirname "$archive")"
tar --null -czf "$archive" -C "$evidence_root" -T "$file_list"
sha256sum "$archive"
du -h "$archive"
