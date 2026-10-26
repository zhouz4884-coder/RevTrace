set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
O="$B/results/revtrace/dependability_20261025/lp1_20261026"
"$B/envs/revbatch-cu128/bin/python" - "$O" <<'PY'
import pathlib,json,sys
o=pathlib.Path(sys.argv[1])
for name in ['SCAN_V2_PROGRESS.json','SCAN_V2_COMPLETE.json','SCAN_V2_STOP.json']:
 if (o/name).exists():print(name,(o/name).read_text())
for s in ['ck5','n5']:
 p=o/('scan_'+s+'_v2')
 if (p/'SUMMARY.json').exists():
  x=json.loads((p/'SUMMARY.json').read_text());print(s,x['counts'])
  print('quarantine_unique_jobs',len({(r['attempt'],q['job']) for r in x['attempts'] for q in r.get('quarantine_opportunities',[])}))
 if (p/'STOP.json').exists():print(s,json.loads((p/'STOP.json').read_text())['error'])
PY
