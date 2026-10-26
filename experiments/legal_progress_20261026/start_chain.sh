set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$O/CHAIN_OWNER.json"
nohup "$B/envs/revbatch-cu128/bin/python" "$P/after_m_chain_v1.py" > "$O/chain_owner.log" 2>&1 < /dev/null &
pid=$!
printf '{"pid":%s,"identity":"after_m_chain_v1.py","scope":"wait exact own M owner; CPU audit; old16 truthful controls; X16 service; no other queues"}\n' "$pid" > "$O/CHAIN_OWNER.json"
cat "$O/CHAIN_OWNER.json"
