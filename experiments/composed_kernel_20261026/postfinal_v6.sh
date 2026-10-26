set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v6"
O="$B/results/revtrace/dependability_20261025/ck5_v6"
test -f "$O/CAMPAIGN_COMPLETE_v3.json"
test ! -e "$O/POSTFINAL_COMPLETE.json"
cd "$P"
"$B/envs/revbatch-cu128/bin/python" regression.py final_v6 > "$O/CPU_SUPPORTED_FINAL.log" 2>&1
cp "$P/CPU_linux_final_v6.xml" "$O/CPU_SUPPORTED_FINAL.xml"
"$B/envs/revbatch-cu128/bin/python" -m pytest test_composed_recovery_external.py -q --basetemp="$O/cpu_external_final" --junitxml="$O/CPU_EXTERNAL_FINAL.xml" > "$O/CPU_EXTERNAL_FINAL.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" formal_explore.py "$O/FORMAL_LINUX_v6_exact.json" > "$O/FORMAL_LINUX.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" formal_two_session.py > "$O/FORMAL_TWO_SESSION_LINUX.log" 2>&1
cp "$P/FORMAL_TWO_SESSION_v6.json" "$O/FORMAL_TWO_SESSION_LINUX_v6.json"
"$B/envs/revbatch-cu128/bin/python" compare_histories_final.py > "$O/HISTORY_COMPARISON.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" supplement_recovery_clocks.py > "$O/RECOVERY_CLOCKS.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" audit_physical_costs_final.py > "$O/PHYSICAL_COSTS.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" audit_boundary_outcomes.py > "$O/BOUNDARY_ACTUAL_OUTCOMES.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" final_resource_audit_final.py > "$O/FINAL_RESOURCE.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" -c 'import pathlib,json; p=pathlib.Path("'"$O"'")/"POSTFINAL_COMPLETE.json"; p.write_text(json.dumps(dict(status="COMPLETE_LINUX_CPU_RECOUNT_HISTORY_COST_AND_RESOURCE_GATES",no_new_GPU=True))+"\n")'
"$B/envs/revbatch-cu128/bin/python" collect_bounded_final.py > "$O/BOUNDED_COLLECTION.log" 2>&1
cat "$O/FINAL_RESOURCE.log"
cat "$O/BOUNDED_COLLECTION.log"
