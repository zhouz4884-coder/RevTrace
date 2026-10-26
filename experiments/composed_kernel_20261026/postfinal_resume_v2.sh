set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v6"
O="$B/results/revtrace/dependability_20261025/ck5_v6"
test -f "$O/CAMPAIGN_COMPLETE_v3.json"
test -f "$O/HISTORY_COMPARISON_v1.json"
test ! -e "$O/POSTFINAL_COMPLETE.json"
cd "$P"
"$B/envs/revbatch-cu128/bin/python" supplement_recovery_clocks_v2.py > "$O/RECOVERY_CLOCKS_v2.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" audit_physical_costs_final.py > "$O/PHYSICAL_COSTS.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" audit_boundary_outcomes.py > "$O/BOUNDARY_ACTUAL_OUTCOMES.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" final_resource_audit_final.py > "$O/FINAL_RESOURCE.log" 2>&1
"$B/envs/revbatch-cu128/bin/python" -c 'import pathlib,json; p=pathlib.Path("'"$O"'")/"POSTFINAL_COMPLETE.json"; p.write_text(json.dumps(dict(status="COMPLETE_LINUX_CPU_RECOUNT_HISTORY_COST_AND_RESOURCE_GATES",no_new_GPU=True))+"\n")'
"$B/envs/revbatch-cu128/bin/python" collect_bounded_final.py > "$O/BOUNDED_COLLECTION.log" 2>&1
cat "$O/FINAL_RESOURCE.log"
cat "$O/BOUNDED_COLLECTION.log"
