"""Recompute summaries from independently audited per-cell CSV, never GPU proxies."""
from pathlib import Path
import csv,json,statistics as st
from collections import defaultdict
W=Path(__file__).resolve().parent;T=W/'tables';T.mkdir(exist_ok=True)
p=W/'collected_early/ALL_162_INDEPENDENT_SERVICE_CELLS.csv'
rs=list(csv.DictReader(p.open()));groups=defaultdict(list)
for r in rs:
 if r['stage'] in ['R4_strict','R2_transfer','R2_strong_async','R2_cost']:
  name=r['cell'].rsplit('-r',1)[0]
  groups[r['stage'],name].append(r)
out=[]
for (stage,name),a in groups.items():
 row={'stage':stage,'policy_load':name,'repeats':len(a),'arrival':a[0]['arrival'],'sessions':int(a[0]['sessions']),
      'dual_2_8_pass_repeats':sum(r['dual_2_8_pass']=='True' for r in a),
      'consumer_rollback_events':[int(r['consumer_rollback_events']) for r in a],
      'authority_cap_events':[int(r['authority_cap_events']) for r in a]}
 for k in ['display_P99_consumer','commit_P99','xRT_to_final_consumer','GPU_J_per_audio_s','WER','CER','consumer_erased_characters','render_wall_seconds_sum','consumer_CPU_seconds','WAL_bytes','max_RSS_kbytes_including_init']:
  vals=[float(r[k]) for r in a if r[k]]
  row[k+'_median']=st.median(vals) if len(vals)==len(a) else None
 out.append(row)
(T/'CAPACITY_AND_STRONG_CONTROLS.json').write_text(json.dumps(out,indent=2)+'\n')
with (T/'CAPACITY_AND_STRONG_CONTROLS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
for r in out:
 print(json.dumps({k:v for k,v in r.items() if k not in ['WAL_bytes_median','max_RSS_kbytes_including_init_median','render_wall_seconds_sum_median','consumer_CPU_seconds_median','consumer_erased_characters_median','CER_median']},ensure_ascii=False))
