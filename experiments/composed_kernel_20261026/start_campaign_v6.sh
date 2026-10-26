set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v6"
O="$B/results/revtrace/dependability_20261025/ck5_v6"
test ! -e "$O/CAMPAIGN_STARTED.json"
tar -xzf "$P/SOURCE_v6.tar.gz" -C "$P"
cd "$P/runtime"
"$B/envs/revbatch-cu128/bin/python" -m pytest tests/test_composed_kernel.py tests/test_certified_envelope.py tests/test_live_qwen.py -q --basetemp="$O/cpu_v6" > "$O/CPU_GATE.log" 2>&1
cd "$P"
nohup "$B/envs/revbatch-cu128/bin/python" -u run_campaign.py > "$O/CAMPAIGN.log" 2>&1 < /dev/null &
CPID=$!
"$B/envs/revbatch-cu128/bin/python" -c 'import json,pathlib,sys; p=int(sys.argv[1]); s=pathlib.Path("/proc")/str(p)/"stat"; pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(pid=p,start_ticks=s.read_text().rsplit(")",1)[1].split()[19])))' "$CPID" "$O/CAMPAIGN_OWNER.json"
cat "$O/CAMPAIGN_OWNER.json"
