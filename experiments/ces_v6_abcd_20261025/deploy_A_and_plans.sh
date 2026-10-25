set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_ces_v6_abcd_20261025"
cd "$P"
test ! -e runtime_A
echo '2e1f0e4fdd7600c2f45dae96c056b0c2c949c1e23145e3c73da6160f5066d75c  SOURCE_A.tar.gz' | sha256sum -c -
tar -xzf SOURCE_A.tar.gz
"$B/envs/revbatch-cu128/bin/python" prepare_plans.py --base "$B"
