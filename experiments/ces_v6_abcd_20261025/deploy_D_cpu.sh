set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_ces_v6_abcd_20261025"
O="$B/results/revtrace/ces_v6_abcd_20261025"
cd "$P"
test ! -e runtime_D
echo '1c19e4aba623c3b294e6a743196a511f1a329087905812661a39c7870937bfd1  SOURCE_D.tar.gz' | sha256sum -c -
tar -xzf SOURCE_D.tar.gz
export PYTHONDONTWRITEBYTECODE=1
cd runtime_D
"$B/envs/revbatch-cu128/bin/python" -m pytest tests/test_dgft.py tests/test_online_admission.py tests/test_live_qwen.py tests/test_lazy_reconciliation.py tests/test_certified_display.py tests/test_consumer_bound_identity.py tests/test_continuity_proof.py tests/test_contract_manifest.py tests/test_terminal_recovery_contract.py tests/test_ces.py tests/test_ces_v5_policy.py tests/test_ces_v5_integration.py tests/test_row_executor_protocol.py tests/test_row_lifecycle_transport.py tests/test_row_progress_integration.py tests/test_durable_journal.py tests/test_ces_closed_loop.py tests/test_closed_loop_independent.py tests/test_v6_planner_cache.py tests/test_v6_anchor.py tests/test_v6_credit_wiring.py -q --basetemp "$O/linux_cpu_tmp_D" --junitxml "$O/LINUX_CPU_D_FOCUSED.xml" > "$O/LINUX_CPU_D_FOCUSED.log" 2>&1
tail -n 3 "$O/LINUX_CPU_D_FOCUSED.log"
