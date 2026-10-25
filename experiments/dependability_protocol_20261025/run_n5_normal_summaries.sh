set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v3';O=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
assert json.loads((O/'postnormal_cpu_v1/primary/SUMMARY.json').read_text())['cells']==105
for path in [O/'normal_aggregation_v1',O/'normal_budgets_v1']:assert not path.exists()
PY
"$B/envs/revbatch-cu128/bin/python" "$B/projects/revtrace_dependability_20261025/n5_v3/aggregate_n5_normal_v1.py" --root "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2" --output "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2/normal_aggregation_v1"
"$B/envs/revbatch-cu128/bin/python" "$B/projects/revtrace_dependability_20261025/n5_v3/audit_n5_budgets_v1.py" --root "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2" --stage formal_normal --output "$B/results/revtrace/dependability_20261025/n5_v3_supervisor_v2/normal_budgets_v1"
