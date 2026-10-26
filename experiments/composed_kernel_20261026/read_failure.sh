set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/ck5_v1/pilot/002-whisper-standard_fair-legacy-r0"
tail -n 55 "$O/attempt0.log"
if test -f "$O/attempt0/failure.json"; then cat "$O/attempt0/failure.json"; fi
