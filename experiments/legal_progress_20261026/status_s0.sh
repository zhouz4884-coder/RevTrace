set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
import json,pathlib,sys
o=pathlib.Path(sys.argv[1]);d=o/'scan_ck5_v1'
if (d/'SUMMARY.json').exists():
 x=json.loads((d/'SUMMARY.json').read_text());print(x['status'],x['counts'])
 print([(r['stage'],r.get('opportunities'),r.get('host_only_upper_bound_opportunities')) for r in x['attempts'] if r.get('opportunities') or r.get('host_only_upper_bound_opportunities')])
if (d/'STOP.json').exists():
 x=json.loads((d/'STOP.json').read_text());print(x['error']);print('completed',len(x['completed']))
h=json.loads((o/'SCAN_OWNER_v1.json').read_text());p=pathlib.Path('/proc')/str(h['pid']);live=False
if (p/'stat').exists():
 s=(p/'stat').read_text().rsplit(')',1)[1].split();live=s[0]!='Z' and s[19]==h['start_ticks']
print('same_CPU_scan_alive',live)
PY
tail -c 3000 "$O/scan_ck5_v1.log"
