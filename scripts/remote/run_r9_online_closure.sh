#!/usr/bin/env bash
set -u
ROOT=${REVTRACE_DATA_ROOT:-/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9}
PROJ="$ROOT/projects/revtrace_r7_0849660"
PY="$ROOT/envs/streamtxn-cu128/bin/python"
OUT="$ROOT/results/revtrace/r9_dgft/service/online_closure_matrix"
CONTRACTS="$ROOT/results/revtrace/r9_dgft/online_closure/contracts"
MANIFEST="$ROOT/datasets/revtrace/librispeech/whisper-w-quality-r8-pristine-confirm.json"
POLICY="$PROJ/results/r9_dgft/r9-frozen-final3-policy.json"
mkdir -p "$OUT" "$CONTRACTS"
export PYTHONPATH="$PROJ/src:$PROJ/scripts/remote"

for model in tiny base small; do
  "$PY" "$PROJ/scripts/build_r9_online_contract.py" \
    --model "$ROOT/models/whisper-$model.en" \
    --model-name "whisper-$model.en" --manifest "$MANIFEST" \
    --policy "$POLICY" --repo "$PROJ" \
    --output "$CONTRACTS/whisper-$model.en-contract.json" \
    >"$CONTRACTS/whisper-$model.en-contract.log" 2>&1 || exit 20
done

run_one() {
  local model=$1 arrival=$2 seed=$3
  local name="$model-$arrival-$seed"
  "$PY" "$PROJ/scripts/remote/run_r9_dgft_service.py" \
    --model "$ROOT/models/whisper-$model.en" --model-name "whisper-$model.en" \
    --manifest "$MANIFEST" \
    --contract "$CONTRACTS/whisper-$model.en-contract.json" \
    --output "$OUT/$name.json" \
    --sessions 16 --duration-seconds 90 --window-seconds 10 \
    --concurrency 16 --arrival "$arrival" --arrival-scale-seconds 0.02 \
    --coalesce-seconds 0.5 --seed "$seed" \
    --proposer-device cuda:0 --authority-device cuda:1 \
    --coverage-threshold 0.20 --coverage-asymmetry-margin 0.15 \
    --structural-coverage-threshold 0.20 \
    --coverage-repair-mode singleton-replay \
    --post-rebase-forward-threshold 0.20 \
    --post-rebase-reverse-ceiling 0.20 \
    >"$OUT/$name.log" 2>&1
  local rc=$?
  echo "$name rc=$rc"
  return $rc
}

failures=0
for arrival in sync poisson; do
  for seed in 2026103001 2026103002 2026103003 2026103004 2026103005; do
    run_one base "$arrival" "$seed" || failures=$((failures + 1))
  done
done
for model in tiny small; do
  for seed in 2026104001 2026104002 2026104003; do
    run_one "$model" sync "$seed" || failures=$((failures + 1))
  done
done
echo "R9.E cells complete failures=$failures"
exit 0
