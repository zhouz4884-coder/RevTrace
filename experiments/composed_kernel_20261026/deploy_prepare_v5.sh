set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v5"
test ! -d "$P"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
mkdir "$P"
mkdir "$B/results/revtrace/dependability_20261025/ck5_v5"
cp "$B/projects/revtrace_dependability_20261025/n5_v3/INDEPENDENT_MANIFEST_v1.json" "$P/"
cp "$B/projects/revtrace_dependability_20261025/n5_v3/run_n5_validation_v2.py" "$P/"
