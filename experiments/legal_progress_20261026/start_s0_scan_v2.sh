set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
test ! -e "$O/SCAN_V2_OWNER.json"
nohup setsid "$B/envs/revbatch-cu128/bin/python" "$P/run_scan_v2.py" > "$O/scan_driver_v2.log" 2>&1 < /dev/null &
SCAN_OWNER=$!
"$B/envs/revbatch-cu128/bin/python" - "$SCAN_OWNER" "$O" <<'PY'
import pathlib,json,sys
pid=int(sys.argv[1]);s=(pathlib.Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
x=dict(pid=pid,start_ticks=s[19],CPU_only=True,source='9ca1f4ee6a565adda66919d303842a4dd8746160')
(pathlib.Path(sys.argv[2])/'SCAN_V2_OWNER.json').write_text(json.dumps(x)+'\n');print(json.dumps(x))
PY
