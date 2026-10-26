set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test -f "$O/CHAIN_V1_CANCELLED_BEFORE_GPU.json"
test ! -e "$O/CHAIN_OWNER_v2.json"
nohup "$B/envs/revbatch-cu128/bin/python" "$P/after_m_chain_v2.py" > "$O/chain_v2_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"identity":"after_m_chain_v2.py","scope":"own M complete then CPU audit old16truth X16service with full power"}\n' "$pid" > "$O/CHAIN_OWNER_v2.json"
cat "$O/CHAIN_OWNER_v2.json"
