set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,datetime,xml.etree.ElementTree as X
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025')
p=O/'LINUX_CPU_D_FOCUSED.xml';suite=X.fromstring(p.read_text()).find('testsuite')
# JUnit uses server-local time; datetime.timestamp applies this host's same TZ.
start=datetime.datetime.fromisoformat(suite.get('timestamp')).timestamp();end=start+float(suite.get('time'));overlap=[]
for C in sorted((O/'A').iterdir()):
 if not C.is_dir() or not (C/'result.json').exists():continue
 es=[json.loads(x) for x in (C/'events.jsonl').read_text().splitlines()];r=json.loads((C/'result.json').read_text());t=next(e for e in es if e['kind']=='run-start')
 # Convert monotonic clocks using the source provenance wall anchor if available.
 prov=json.loads((C/'provenance.json').read_text())
 overlap.append({'cell':C.name,'result_mtime_unix':(C/'result.json').stat().st_mtime,'wall_seconds':r['wall_seconds_including_arrival_and_drain'],'provenance_clock_keys':list(prov) if len(overlap)==0 else []})
print(json.dumps({'CPU_start_unix':start,'CPU_end_unix':end,'CPU_seconds':float(suite.get('time')),'approx_serving_interval_by_result_mtime':[r for r in overlap if r['result_mtime_unix']>=start and r['result_mtime_unix']-r['wall_seconds']<=end],'precision_note':'Result mtime can follow final write; inspect bounded intervals, do not silently delete a cell.'}))
PY
