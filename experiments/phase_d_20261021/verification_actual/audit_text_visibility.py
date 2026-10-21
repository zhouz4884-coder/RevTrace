"""Actual view timing, plus explicitly OFFLINE selected-text-prefix evaluation."""
from pathlib import Path
import csv,json,re,sys
from collections import defaultdict
B=Path(sys.argv[1]);O=B/'results/revtrace/phaseD_20261021';rows=[];points=[]
def units(text):return list(text) if any('\u4e00'<=c<='\u9fff' for c in text) else re.findall(r'\S+',text)
def q99(xs):
 if not xs or any(x is None for x in xs):return None
 xs=sorted(xs);n=(len(xs)-1)*.99;i=int(n);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(n-i)
for stage in ['R2_continuity','R2_strong_async','R2_transfer','R4_strict']:
 for c in sorted((O/stage).iterdir()):
  if not (c/'result.json').exists():continue
  cfg=json.loads((c/'config.json').read_text());es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];vs=[json.loads(l) for l in (c/'consumer.jsonl').read_text().splitlines()];pubs={(e['session_id'],e['version']):e for e in es if e['kind']=='canonical-display'};server={(e['session_id'],e['kind'],e['displayed']):e for e in es if e['kind'] in ['display','canonical-display']};cellpoints=[]
  for commit in [e for e in es if e['kind']=='commit']:
   sid=commit['session_id'];F=commit['audio_end_sample'];target=pubs[sid,commit['version']]['text'];target_units=units(target);seen=[]
   for v in vs:
    if v['session_id']!=sid or v['observed']<commit['audio_ready']:continue
    source=server[sid,v['source_kind'],v['server_time']]
    input_frontier=max(source['audio_end_sample'],v['valid_visible_frontier'])
    if input_frontier<F:continue
    visible=[v['visible_text']]+([v['certified_text']] if cfg['consumer_policy']=='two_lane' else [])
    if any(units(text)[:len(target_units)]==target_units for text in visible):seen.append(v['observed'])
   row={'stage':stage,'cell':c.name,'rho':cfg['rho'],'session_id':sid,'version':commit['version'],'frontier_seconds':F/16000,'selected_reference_text_first_seen_latency':min(seen)-commit['audio_ready'] if seen else None,'installed_commit_latency':commit['latency_seconds'],'reference_units':len(target_units),'evidence':'OFFLINE_REFERENCE_PREFIX_EVALUATION_OF_ACTUAL_CLIENT_LOGS_NOT_ONLINE_CERTIFICATION_OR_AUDIO_WORD_ALIGNMENT'}
   points.append(row);cellpoints.append(row)
  rows.append({'stage':stage,'cell':c.name,'consumer':cfg['consumer_policy'],'rho':cfg['rho'],'reference_targets':len(cellpoints),'missing':sum(p['selected_reference_text_first_seen_latency'] is None for p in cellpoints),'selected_text_first_seen_P99':q99([p['selected_reference_text_first_seen_latency'] for p in cellpoints]),'commit_P99_on_same_targets':q99([p['installed_commit_latency'] for p in cellpoints]),'not_a_substitute_for_primary_audio_frontier_SLO':True})
A=O/'independent';A.mkdir(exist_ok=True)
for name,rs in [('SELECTED_TEXT_VISIBILITY.csv',rows),('SELECTED_TEXT_VISIBILITY_POINTS.csv',points)]:
 with (A/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
print('audited selected-text visibility',len(rows),'actual client runs')
