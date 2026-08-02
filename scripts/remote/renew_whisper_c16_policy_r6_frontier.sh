#!/usr/bin/env bash
# Freeze a full revision-age frontier after R5 exposed a policy-conditioned
# window-7 root.  The source workload is adaptation-only.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
BASE="$OUT/p0/c16-policy-r5-frontier.json"; CURRENT="$OUT/p0/c16-policy.json"
FRESH="$OUT/p0/c16-adaptation-roots-r6.json"; NEW="$OUT/p0/c16-policy-r6-frontier.json"
WORKLOAD="$OUT/pilot/c16_r3_replay/w2-root-replay.json"
cd "$PROJ"
"$PY" scripts/extract_whisper_adaptation_roots.py --workload "$WORKLOAD" \
 --output "$FRESH" >"$OUT/logs/c16-adaptation-roots-r6.log" 2>&1
"$PY" scripts/update_whisper_window_frontier.py --policy "$BASE" \
 --adaptation-audit "$FRESH" --output "$NEW" \
 --maximum-verification-fraction 0.20 >"$OUT/logs/c16-policy-r6-frontier.log" 2>&1
"$PY" - "$NEW" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); p=d['selected_policy']
assert d['decision']=='WINDOW_FRONTIER_UPDATED'
assert p['fast_path_state_errors']==0
assert p['calibration_upper_risk']<=0.005
assert p['verification_fraction']<=0.20
assert p['caught_roots_covered']>=10
print(json.dumps(p,sort_keys=True))
PY
cp "$NEW" "$CURRENT"
