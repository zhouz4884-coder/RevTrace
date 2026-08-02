#!/usr/bin/env bash
# Convert an independently caught holdback-distribution root into an
# adaptation-only policy epoch, then leave all validation to fresh seeds.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OLDROOT="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
OLD="$OLDROOT/w4-state-age-policy-base-c8-m80-recovery-r5.json"
NEW="$OUT/p0/c8-policy.json"
ORIGINAL="$OUT/p0/c8-policy-original.json"
mkdir -p "$OUT/p0" "$OUT/logs"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"
[[ -f "$ORIGINAL" ]] || cp "$OLD" "$ORIGINAL"

CAUGHT=$($PY - "$OUT/p3/risk/c8-seed20274300.json" \
 "$OUT/p3/risk/c8-seed20274350.json" <<'PY'
import json,sys
print(sum(json.load(open(p))['counts']['caught_state_errors'] for p in sys.argv[1:]))
PY
)
if [[ "$CAUGHT" == 0 ]]; then
  cp "$ORIGINAL" "$NEW"
  echo "No c8 renewal required"
  exit 0
fi

mapfile -t P < <("$PY" - "$OLD" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))['selected_policy']
for k in ('threshold','age_window_index','age_margin_threshold','late_window_index','late_margin_threshold','high_load_prompt_tokens','high_load_margin_threshold'):
 v=p.get(k); print('NONE' if v is None else v)
PY
)
ARGS=(--margin-threshold "${P[0]}" --policy-source "$OLD")
[[ "${P[1]}" == NONE ]] || ARGS+=(--age-window-index "${P[1]}")
[[ "${P[2]}" == NONE ]] || ARGS+=(--age-margin-threshold "${P[2]}")
[[ "${P[3]}" == NONE ]] || ARGS+=(--late-window-index "${P[3]}")
[[ "${P[4]}" == NONE ]] || ARGS+=(--late-margin-threshold "${P[4]}")
[[ "${P[5]}" == NONE ]] || ARGS+=(--high-load-prompt-tokens "${P[5]}")
[[ "${P[6]}" == NONE ]] || ARGS+=(--high-load-margin-threshold "${P[6]}")

REPEATS=()
for SEED in 20274300 20274350; do
  SOURCE="$OUT/p3/risk/c8-seed${SEED}.json"
  mapfile -t ROOTS < <("$PY" - "$SOURCE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
roots={}
for r in d['audit_rows']:
 if not r['state_error']:
  continue
 key=(r['session_id'],r['window_index'])
 prior=roots.get(key)
 if prior is None or (r['minimum_margin'],-r['episode']) > (prior['minimum_margin'],-prior['episode']):
  roots[key]=r
for r in sorted(roots.values(),key=lambda x:x['episode']):
 print(f"{r['episode']}:{r['session_id']}:{r['window_index']}")
PY
  )
  [[ "${#ROOTS[@]}" == 0 ]] && continue
  REPEAT="$OUT/p0/c8-adaptation-repeat-seed${SEED}.json"
  FORCED=()
  for root in "${ROOTS[@]}"; do FORCED+=(--forced-audit-root "$root"); done
  set +e
  "$PY" "$RUNNER" audit --model "$MODEL" --model-name whisper-base.en \
   --manifest "$MANIFEST" --output "$REPEAT" --sessions 32 \
   --duration-seconds 180 --window-seconds 10 --concurrency 8 \
   --seed "$SEED" --max-new-tokens 80 --authority-max-new-tokens 96 \
   --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0 \
   --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
   --stop-on-caught-error "${FORCED[@]}" "${ARGS[@]}" \
   >"$OUT/logs/c8-adaptation-repeat-seed${SEED}.log" 2>&1
  REPEAT_STATUS=$?
  set -e
  if [[ "$REPEAT_STATUS" != 2 ]]; then
    echo "Expected adaptation-only audit exit 2, got $REPEAT_STATUS" >&2
    exit 3
  fi
  "$PY" - "$REPEAT" "${#ROOTS[@]}" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); expected=int(sys.argv[2])
roots=[r for r in d['audit_rows'] if r['state_error']]
assert len(roots)==expected, (len(roots),expected)
assert all(r.get('canonical_repeat_stable') is True for r in roots), 'canonical oracle is not repeat-stable'
assert len(d['forced_audit_roots_seen'])==expected
PY
  REPEATS+=("$REPEAT")
done
[[ "${#REPEATS[@]}" -gt 0 ]] || { echo "No repeat-stable root" >&2; exit 4; }

BUILD_ARGS=(
 --policy "$ORIGINAL"
 --calibration "$OLDROOT/w4-calibration-long-base-c8-m80-seed20260730.json"
 --calibration "$OLDROOT/w4-calibration-long-base-c8-m80-seed20260731.json"
 --adaptation-audit "$OLDROOT/w4-external-root-base-c8-m80-stateonly-formal202728-v1.json"
 --adaptation-audit "$OLDROOT/w4-risk-base-c8-m80-workv1-attempt1-seed20272900.json"
 --adaptation-audit "$OLDROOT/w4-risk-base-c8-m80-workv1-attempt2-seed20272960.json"
 --adaptation-audit "$OLDROOT/w4-risk-base-c8-m80-workv1-attempt3-seed20273150.json"
 --adaptation-audit "$OLDROOT/w4-risk-base-c8-m80-workv1-attempt4-seed20273300.json"
)
for repeat in "${REPEATS[@]}"; do BUILD_ARGS+=(--adaptation-audit "$repeat"); done
"$PY" "$PROJ/scripts/build_whisper_w_state_age_policy.py" \
 "${BUILD_ARGS[@]}" --output "$NEW" \
 >"$OUT/logs/c8-policy-renewal.log" 2>&1

"$PY" - "$NEW" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['decision']=='STATE_AGE_POLICY_SELECTED'
assert d['selected_policy']['fast_path_state_errors']==0
assert d['selected_policy']['calibration_upper_risk']<=0.005
assert d['selected_policy']['verification_fraction']<=0.20
print(json.dumps(d['selected_policy'],sort_keys=True))
PY
