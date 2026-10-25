set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025"
O="$B/results/revtrace/dependability_20261025"
"$B/envs/revbatch-cu128/bin/python" "$P/audit_assets_n1_v2.py" --stage "$O/pilot" --manifest "$P/MANIFEST.json" --model "$B/models/Qwen3-ASR-1.7B" --output "$O/PILOT_ASSET_AUDIT_v2.json"
