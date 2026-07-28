#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
SOURCE_ROOT="${DATA_ROOT}/sources/revtrace-phase7"

cd "${SOURCE_ROOT}"
for archive in ./*.zip; do
  directory="${archive%.zip}"
  mkdir -p "${directory}"
  unzip -q -o "${archive}" -d "${directory}"
done

find "${SOURCE_ROOT}" -maxdepth 3 -type f \
  \( -name README.md -o -name pyproject.toml \) -print | sort
