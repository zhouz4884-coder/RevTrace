from pathlib import Path
from collections import defaultdict
import csv,json,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/elastic_20261022';rows=[]
for stage in ['fixed_scout','stress_scout','formal']:
 for c in sorted((O/stage).iterdir()):
  if not (c/'result.json').exists():continue
  r=json.loads((c/'result.json').read_text());es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];vs=[json.loads(l) for l in (c/'consumer.jsonl').read_text().splitlines()];t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');wall=max(r['wall_seconds_including_arrival_and_drain'],max(v['observed'] for v in vs));a,b=t0,t0+wall;by=defaultdict(list)
  for p in json.loads((c/'power_samples.json').read_text())['samples']:by[p['gpu']].append(p)
  energy=0;cov=[]
  for ps in by.values():
   ps.sort(key=lambda p:p['t']);cov.append(max(0,min(b,ps[-1]['t'])-max(a,ps[0]['t']))/(b-a))
   for x,y in zip(ps,ps[1:]):
    l,u=max(a,x['t']),min(b,y['t'])
    if u<=l:continue
    def watts(t):return x['power_w']+(y['power_w']-x['power_w'])*(t-x['t'])/(y['t']-x['t'])
    energy+=(watts(l)+watts(u))*(u-l)/2
  assert len(by)==2
  rows.append({'stage':stage,'cell':c.name,'strict_common_window_seconds':wall,'audio_seconds':r['audio_seconds'],'sample_supported_common_window_GPU_J':energy,'common_window_J_audio_s':energy/r['audio_seconds'],'min_device_window_coverage':min(cov),'original_sample_span_J_audio_s':r['energy_joules_per_audio_second'],'host_energy_not_measured':True})
with (O/'POWER_WINDOW_AUDIT.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('independent two-device power windows',len(rows))
