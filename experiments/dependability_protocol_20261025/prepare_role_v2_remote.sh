set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');old=B/'results/revtrace/dependability_20261025/role_probe_v1'
d=json.loads((old/'PILOT_LAUNCH.json').read_text());p=Path('/proc')/str(d['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==d['start_ticks'])
assert json.loads((old/'pilot/SUMMARY.json').read_text())['cells']==8
assert json.loads((old/'PILOT_ASSET_REPLAY_v1.json').read_text())['status']=='PASS8_ACTUAL_BASE_INPUT_AND_NATIVE_CORRUPT_PHI_ASSET_REPLAY'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
for kind in ['projects','results']:(B/(kind+'/revtrace'+('_dependability_20261025' if kind=='projects' else '/dependability_20261025')+'/role_probe_v2')).mkdir(exist_ok=False)
print('PREPARED_ROLE_V2_SOURCE_AND_RESULTS_ONLY')
PY
