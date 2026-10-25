set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');N=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
assert json.loads((N/'postfault_cpu_v2/SUMMARY.json').read_text())['status']=='PASS21_FORMAL_RECOVERY_WAL_PRIMARY_AND_ACTUAL_ASSETS'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
O=B/'results/revtrace/dependability_20261025/role_probe_v1';O.mkdir(exist_ok=False)
print('PREPARED_RESULTS_ONLY',O)
PY
