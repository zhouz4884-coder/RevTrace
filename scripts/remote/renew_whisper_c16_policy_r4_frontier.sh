#!/usr/bin/env bash
# Fail-closed renewal after the first live R3 replay exposed a new, repeat-
# stable window-4 root.  The root is adaptation-only and is excluded from the
# later independent risk audit.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
BASE="$OUT/p0/c16-policy-r3-frontier.json"
CURRENT="$OUT/p0/c16-policy.json"
FRESH="$OUT/p0/c16-adaptation-roots-r4.json"
NEW="$OUT/p0/c16-policy-r4-frontier.json"
WORKLOAD="$OUT/pilot/c16_r3_replay/w2-root-replay.json"
cd "$PROJ"
"$PY" scripts/extract_whisper_adaptation_roots.py \
 --workload "$WORKLOAD" --output "$FRESH" \
 >"$OUT/logs/c16-adaptation-roots-r4.log" 2>&1
mapfile -t CALIBRATIONS < <("$PY" - "$BASE" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['source_files']:
 if row['role']=='calibration': print(row['path'])
PY
)
mapfile -t ROOTS < <("$PY" - "$BASE" <<'PY'
import json,sys
for row in json.load(open(sys.argv[1]))['source_files']:
 if row['role']=='adaptation-only-root': print(row['path'])
PY
)
ARGS=(--policy "$BASE" --output "$NEW" --maximum-verification-fraction 0.20)
for path in "${CALIBRATIONS[@]}"; do ARGS+=(--calibration "$path"); done
for path in "${ROOTS[@]}"; do ARGS+=(--adaptation-audit "$path"); done
ARGS+=(--adaptation-audit "$FRESH")
"$PY" scripts/build_whisper_w_state_age_policy.py "${ARGS[@]}" \
 >"$OUT/logs/c16-policy-r4-frontier.log" 2>&1
"$PY" - "$NEW" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); p=d['selected_policy']
assert d['decision']=='STATE_AGE_POLICY_SELECTED'
assert p['fast_path_state_errors']==0
assert p['calibration_upper_risk']<=0.005
assert p['verification_fraction']<=0.20
assert p['caught_roots_covered']>=8
assert p['window_margin_rules']
print(json.dumps(p,sort_keys=True))
PY
cp "$NEW" "$CURRENT"
