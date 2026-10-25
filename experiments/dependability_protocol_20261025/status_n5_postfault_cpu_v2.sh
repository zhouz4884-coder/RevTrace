set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dependability_20261025/n5_v3_supervisor_v2')
d=json.loads((O/'POSTFAULT_CPU_V2_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
d['verified_live']=p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'];print(json.dumps(d))
for name in ['PROGRESS.json','SUMMARY.json','STOP.json']:
 p=O/'postfault_cpu_v2'/name
 if p.exists():print(name,p.read_text()[:2500])
for p in (O/'postfault_cpu_v2').glob('*.log'):
 print('LOG',p.name,p.read_text(errors='replace')[-1200:])
PY
