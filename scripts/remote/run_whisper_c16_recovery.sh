#!/usr/bin/env bash
# Fail-closed renewal after a holdback-distribution c16 audit catches a root.
# The failed audit remains evidence; renewed performance and certificates use
# new seeds and separate output directories.
set -euo pipefail
ROOT="${1:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}"
PROJ="$ROOT/projects/revtrace"; PY="$ROOT/envs/streamtxn-cu128/bin/python"
MODEL="$ROOT/models/whisper-base.en"
MANIFEST="$ROOT/datasets/revtrace/librispeech/phase4b-test-clean-full.json"
OLDROOT="$ROOT/results/revtrace/whisper_w0_w7"
OUT="$ROOT/results/revtrace/whisper_p0_p3"
RUNNER="$PROJ/scripts/remote/run_whisper_w_system.py"
OLD="$OUT/p0/c16-policy-original.json"
NEW="$OUT/p0/c16-policy.json"
mkdir -p "$OUT/p0" "$OUT/logs" "$OUT/oracle" \
 "$OUT/p3/c16_w1_renewed" "$OUT/p3/c16_w2_renewed" \
 "$OUT/p3/risk_c16_renewed"
cd "$PROJ"; export PYTHONPATH="$PROJ/src"

[[ -f "$OLD" ]] || cp "$OLDROOT/w4-state-age-policy-base-c16-recovery-r4.json" "$OLD"
mapfile -t FAILED < <(
 find "$OUT/p3/risk" -maxdepth 1 -type f -name 'c16-*.json' \
  ! -name '*.checkpoint.json' | sort
)
[[ "${#FAILED[@]}" -ge 1 ]] || { echo "Expected at least one fail-fast c16 audit" >&2; exit 2; }
CAUGHT=$($PY - "${FAILED[@]}" <<'PY'
import json,sys
print(sum(json.load(open(p))['counts']['caught_state_errors'] for p in sys.argv[1:]))
PY
)
if [[ "$CAUGHT" == 0 ]]; then
  echo "Initial c16 audit did not catch a root; renewal is unnecessary" >&2
  exit 3
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
for SOURCE in "${FAILED[@]}"; do
  SEED=$(basename "$SOURCE" | sed -E 's/.*seed([0-9]+)\.json/\1/')
  mapfile -t ROOTS < <("$PY" - "$SOURCE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); roots={}
for r in d['audit_rows']:
 if not r['state_error']: continue
 key=(r['session_id'],r['window_index'])
 prior=roots.get(key)
 if prior is None or (r['minimum_margin'],-r['episode']) > (prior['minimum_margin'],-prior['episode']):
  roots[key]=r
for r in sorted(roots.values(),key=lambda x:x['episode']):
 print(f"{r['episode']}:{r['session_id']}:{r['window_index']}")
PY
  )
  [[ "${#ROOTS[@]}" == 0 ]] && continue
  if "$PY" - "$SOURCE" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); roots=[r for r in d['audit_rows'] if r['state_error']]
assert roots and all(r.get('canonical_repeat_stable') is True for r in roots)
PY
  then
    # The fail-fast audit already performed two same-input singleton repeats
    # before writing the caught row. Reuse it as adaptation-only evidence.
    REPEATS+=("$SOURCE")
    continue
  fi
  REPEAT="$OUT/p0/c16-adaptation-repeat-seed${SEED}.json"
  FORCED=(); for root in "${ROOTS[@]}"; do FORCED+=(--forced-audit-root "$root"); done
  set +e
  "$PY" "$RUNNER" audit --model "$MODEL" --model-name whisper-base.en \
   --manifest "$MANIFEST" --output "$REPEAT" --sessions 32 \
   --duration-seconds 90 --window-seconds 10 --concurrency 16 \
   --seed "$SEED" --max-new-tokens 96 --authority-max-new-tokens 96 \
   --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0 \
   --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
   --stop-on-caught-error "${FORCED[@]}" "${ARGS[@]}" \
   >"$OUT/logs/c16-adaptation-repeat-seed${SEED}.log" 2>&1
  REPEAT_STATUS=$?
  set -e
  [[ "$REPEAT_STATUS" == 2 ]] || { echo "Expected adaptation exit 2, got $REPEAT_STATUS" >&2; exit 4; }
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
[[ "${#REPEATS[@]}" -gt 0 ]] || { echo "No repeat-stable c16 root" >&2; exit 5; }

BUILD_ARGS=(
 --policy "$OLD"
 --calibration "$OLDROOT/w4-calibration-long-base-c16-seed20260730.json"
 --calibration "$OLDROOT/w4-calibration-long-base-c16-seed20260731.json"
 --adaptation-audit "$OLDROOT/w4-risk-base-c16-attempt1-seed20272033.json"
 --adaptation-audit "$OLDROOT/w4-external-root-base-c16-state-contract-seed20272591.json"
 --adaptation-audit "$OLDROOT/w4-external-root-base-c16-stateonly-formal202726-v1.json"
 --adaptation-audit "$OLDROOT/w4-external-root-base-c16-w5-seed20272202.json"
)
for repeat in "${REPEATS[@]}"; do BUILD_ARGS+=(--adaptation-audit "$repeat"); done
"$PY" "$PROJ/scripts/build_whisper_w_state_age_policy.py" \
 "${BUILD_ARGS[@]}" --output "$NEW" >"$OUT/logs/c16-policy-renewal.log" 2>&1
"$PY" - "$NEW" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); p=d['selected_policy']
assert d['decision']=='STATE_AGE_POLICY_SELECTED'
assert p['fast_path_state_errors']==0
assert p['calibration_upper_risk']<=0.005
assert p['verification_fraction']<=0.20
print(json.dumps(p,sort_keys=True))
PY

"$PY" - "$RUNNER" "$PROJ/src/revtrace/whisper_state.py" \
 >"$OUT/p0/final_runtime_code_identity.json" <<'PY'
import hashlib,json,pathlib,sys
rows=[]
for raw in sys.argv[1:]:
 p=pathlib.Path(raw); rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'schema_version':1,'files':rows},indent=2,sort_keys=True))
PY

mapfile -t N < <("$PY" - "$NEW" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))['selected_policy']
for k in ('threshold','age_window_index','age_margin_threshold','late_window_index','late_margin_threshold','high_load_prompt_tokens','high_load_margin_threshold'):
 v=p.get(k); print('NONE' if v is None else v)
PY
)
NARGS=(--margin-threshold "${N[0]}" --policy-source "$NEW")
[[ "${N[1]}" == NONE ]] || NARGS+=(--age-window-index "${N[1]}")
[[ "${N[2]}" == NONE ]] || NARGS+=(--age-margin-threshold "${N[2]}")
[[ "${N[3]}" == NONE ]] || NARGS+=(--late-window-index "${N[3]}")
[[ "${N[4]}" == NONE ]] || NARGS+=(--late-margin-threshold "${N[4]}")
[[ "${N[5]}" == NONE ]] || NARGS+=(--high-load-prompt-tokens "${N[5]}")
[[ "${N[6]}" == NONE ]] || NARGS+=(--high-load-margin-threshold "${N[6]}")

run_perf() {
 local arrival="$1" seed="$2" output="$3" oracle="$4" log="$5"
 local extra=(); [[ "$arrival" == poisson ]] && extra=(--arrival-scale-seconds 0.02)
 "$PY" "$RUNNER" workload --model "$MODEL" --model-name whisper-base.en \
  --manifest "$MANIFEST" --output "$output" --oracle-cache "$oracle" \
  --sessions 16 --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --arrival "$arrival" "${extra[@]}" --seed "$seed" --max-new-tokens 96 \
  --authority-max-new-tokens 96 --terminal-contract state-only \
  --verifier-lanes 1 --slo-seconds 1.9 --system revtrace \
  --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:1 \
  "${NARGS[@]}" >"$OUT/logs/$log.log" 2>&1
}
for seed in 20275201 20275202 20275203 20275204 20275205; do
 run_perf sync "$seed" "$OUT/p3/c16_w1_renewed/seed${seed}.json" \
  "$OUT/oracle/base-c16-w1-renewed-seed${seed}.json" "p3-c16-W1-renewed-seed${seed}"
done
for seed in 20275301 20275302 20275303 20275304 20275305; do
 run_perf poisson "$seed" "$OUT/p3/c16_w2_renewed/seed${seed}.json" \
  "$OUT/oracle/base-c16-w2-renewed-seed${seed}.json" "p3-c16-W2-renewed-seed${seed}"
done

pids=()
for spec in "0:20275400" "1:20275450"; do
 gpu=${spec%%:*}; seed=${spec##*:}
 CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$RUNNER" audit \
  --model "$MODEL" --model-name whisper-base.en --manifest "$MANIFEST" \
  --output "$OUT/p3/risk_c16_renewed/c16-seed${seed}.json" --sessions 32 \
  --duration-seconds 90 --window-seconds 10 --concurrency 16 \
  --seed "$seed" --max-new-tokens 96 --authority-max-new-tokens 96 \
  --target-risk-entries 30000 --minimum-audits 500 --audit-probability 0.021 \
  --low-margin-policy holdback --proposer-device cuda:0 --verifier-device cuda:0 \
  "${NARGS[@]}" >"$OUT/logs/risk-c16-renewed-seed${seed}.log" 2>&1 &
 pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
touch "$OUT/.c16-renewal-complete"
