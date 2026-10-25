set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_ces_v6_abcd_20261025"
O="$B/results/revtrace/ces_v6_abcd_20261025"
PY="$B/envs/revbatch-cu128/bin/python"
cd "$P"
test ! -e runtime
echo '41df5043b45e16bca1829dd864c7ba0703b8d5c18d03291048700a8815d1a2d9  SOURCE_v1.tar.gz' | sha256sum -c -
tar -xzf SOURCE_v1.tar.gz
export PYTHONDONTWRITEBYTECODE=1
cd runtime
"$PY" -m pytest tests/test_dgft.py tests/test_online_admission.py tests/test_live_qwen.py tests/test_lazy_reconciliation.py tests/test_certified_display.py tests/test_consumer_bound_identity.py tests/test_continuity_proof.py tests/test_contract_manifest.py tests/test_terminal_recovery_contract.py tests/test_ces.py tests/test_ces_v5_policy.py tests/test_ces_v5_integration.py tests/test_row_executor_protocol.py tests/test_row_lifecycle_transport.py tests/test_row_progress_integration.py tests/test_durable_journal.py tests/test_ces_closed_loop.py tests/test_closed_loop_independent.py tests/test_v6_planner_cache.py tests/test_v6_anchor.py -q --basetemp "$O/linux_cpu_tmp_v1" --junitxml "$O/LINUX_CPU_REGRESSION.xml" > "$O/LINUX_CPU_REGRESSION.log" 2>&1
cd "$P"
"$PY" fit_v6_profiles.py --base "$B" > "$O/TRAINING.log" 2>&1
"$PY" - <<'PY'
from pathlib import Path
import json,hashlib
P=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_ces_v6_abcd_20261025')
m=json.loads((P/'runtime/SOURCE_MANIFEST.json').read_text())
for r in m['files']:assert hashlib.sha256((P/'runtime'/r['path']).read_bytes()).hexdigest()==r['sha256']
print(json.dumps({'source_commit':m['code_commit'],'source_files':len(m['files']),'Linux_CPU':'PASS','training':'COMPLETE_NO_GPU'}))
PY
