"""Actual certified Consumer timing, supplementary to frozen install clock."""
from pathlib import Path
import collections,csv,json,sys
from analysis_core import quantile,good_audio
B=Path(sys.argv[1]);O=B/'results/revtrace/ces_20261023';A=O/'formal_v1_independent_audit_final';D=O/'consumer_commit_addendum_v1';D.mkdir(exist_ok=False)
def read(p):return list(csv.DictReader(p.open()))
cells=read(A/'SERVICE_CELLS.csv');fs=read(A/'COMMON_FRONTIERS.csv');groups=collections.defaultdict(list)
for f in fs:groups[f['cell']].append(f)
rows=[]
for c in cells:
 local=[];lags=[]
 for f in groups[c['cell']]:
  co=float(f['certified_consumer']) if f['certified_consumer'] else None
  installed=float(f['commit']) if f['commit'] else None
  if co is not None and installed is not None:assert co+1e-7>=installed;lags.append(co-installed)
  local.append({'audio_seconds':float(f['audio_seconds']),'display':float(f['display']) if f['display'] else None,'commit':co})
 row={'cell':c['cell'],'method':c['method'],'certified_consumer_Goodput_2_8':good_audio(local)/float(c['wall_seconds']),
  'install_clock_Goodput_2_8':float(c['Audio_Goodput_2_8']),'max_install_to_consumer_s':max(lags)}
 for q,label in [(.5,'P50'),(.95,'P95'),(.99,'P99')]:row['certified_consumer_'+label]=quantile([f['commit'] for f in local],q)
 rows.append(row)
with (D/'CONSUMER_COMMIT_CELLS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(D/'SUMMARY.json').write_text(json.dumps({'status':'PASS_ACTUAL_CERTIFIED_CONSUMER_CLOCK_ADDENDUM','cells':len(rows),
 'new_GPU_calls':0,'primary_install_clock_not_silently_changed':True,
 'changed_Goodput_cells':sum(abs(r['certified_consumer_Goodput_2_8']-r['install_clock_Goodput_2_8'])>1e-12 for r in rows)},indent=2)+'\n')
