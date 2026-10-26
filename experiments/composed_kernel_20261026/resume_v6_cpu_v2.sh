set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v6"
O="$B/results/revtrace/dependability_20261025/ck5_v6"
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader)"
test ! -e "$O/RESUME_OWNER_v2.json"
cd "$P"
nohup "$B/envs/revbatch-cu128/bin/python" -u resume_campaign_v2.py > "$O/CAMPAIGN_v2.log" 2>&1 < /dev/null &
CPID=$!
"$B/envs/revbatch-cu128/bin/python" -c 'import json,pathlib,sys; p=int(sys.argv[1]); s=pathlib.Path("/proc")/str(p)/"stat"; pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(pid=p,start_ticks=s.read_text().rsplit(")",1)[1].split()[19])))' "$CPID" "$O/RESUME_OWNER_v2.json"
cat "$O/RESUME_OWNER_v2.json"
