#!/usr/bin/env bash
# Fail-closed renewal from repeat-stable fresh workload roots. The roots adapt
# the policy but are excluded from the later independent risk certificate.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
CURRENT="$OUT/p0/c16-policy.json"
BACKUP="$OUT/p0/c16-policy-r1.json"
NEW="$OUT/p0/c16-policy-r2.json"
FRESH="$OUT/p0/c16-adaptation-roots-r2.json"
cd "$PROJ"

[[ -f "$BACKUP" ]] || cp "$CURRENT" "$BACKUP"
mapfile -t CALIBRATIONS < <("$PY" - "$BACKUP" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['source_files']:
 if row['role']=='calibration': print(row['path'])
PY
)
mapfile -t ROOTS < <("$PY" - "$BACKUP" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['source_files']:
 if row['role']=='adaptation-only-root': print(row['path'])
PY
)
ARGS=(--policy "$BACKUP" --output "$NEW" --maximum-verification-fraction 0.20)
for path in "${CALIBRATIONS[@]}"; do ARGS+=(--calibration "$path"); done
for path in "${ROOTS[@]}"; do ARGS+=(--adaptation-audit "$path"); done
ARGS+=(--adaptation-audit "$FRESH")
"$PY" scripts/build_whisper_w_state_age_policy.py "${ARGS[@]}" \
 >"$OUT/logs/c16-policy-r2.log" 2>&1
"$PY" - "$NEW" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); p=d['selected_policy']
assert d['decision']=='STATE_AGE_POLICY_SELECTED'
assert p['fast_path_state_errors']==0
assert p['calibration_upper_risk']<=0.005
assert p['verification_fraction']<=0.20
assert p['caught_roots_covered']>=7
print(json.dumps(p,sort_keys=True))
PY
cp "$NEW" "$CURRENT"
