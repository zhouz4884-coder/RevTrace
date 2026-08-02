#!/usr/bin/env bash
# Re-express the same seven adaptation-only roots with a learned piecewise
# state-age frontier. No new outcome enters selection in this step.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
CURRENT="$OUT/p0/c16-policy.json"; BACKUP="$OUT/p0/c16-policy-r2.json"
NEW="$OUT/p0/c16-policy-r3-frontier.json"
cd "$PROJ"
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
"$PY" scripts/build_whisper_w_state_age_policy.py "${ARGS[@]}" \
 >"$OUT/logs/c16-policy-r3-frontier.log" 2>&1
"$PY" - "$NEW" "$BACKUP" <<'PY'
import json,sys
new=json.load(open(sys.argv[1])); old=json.load(open(sys.argv[2]))
p=new['selected_policy']; q=old['selected_policy']
assert new['decision']=='STATE_AGE_POLICY_SELECTED'
assert p['fast_path_state_errors']==0
assert p['calibration_upper_risk']<=0.005
assert p['caught_roots_covered']>=7
assert p['verification_fraction'] < q['verification_fraction']
assert p['window_margin_rules']
print(json.dumps(p,sort_keys=True))
PY
cp "$NEW" "$CURRENT"
