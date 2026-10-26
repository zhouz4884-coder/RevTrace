set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/lp1_20261026"
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$P" "$O" <<'PY'
import json,pathlib,hashlib,sys
p,o=map(pathlib.Path,sys.argv[1:]);s=json.loads((p/'SCAN_SOURCE_v1.json').read_text())
for f in s['files']:assert hashlib.sha256((p/f['path']).read_bytes()).hexdigest()==f['sha256']
assert not (o/'SCAN_OWNER_v1.json').exists();(o/'SCAN_CODE_v1.json').write_text(json.dumps(s,indent=2)+'\n')
PY
test ! -e "$O/scan_ck5_v1"
nohup setsid "$B/envs/revbatch-cu128/bin/python" "$P/scan_historical_views.py" --output "$O/scan_ck5_v1" > "$O/scan_ck5_v1.log" 2>&1 < /dev/null &
SCAN_OWNER=$!
"$B/envs/revbatch-cu128/bin/python" - "$SCAN_OWNER" "$O" <<'PY'
import pathlib,json,sys
pid=int(sys.argv[1]);s=(pathlib.Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
x=dict(pid=pid,start_ticks=s[19],CPU_only=True,source='a87bb21ae3de8ddf1621ad7cf0b41207e67a5ce8')
(pathlib.Path(sys.argv[2])/'SCAN_OWNER_v1.json').write_text(json.dumps(x)+'\n');print(json.dumps(x))
PY
