"""Second implementation: direct future-view comparisons and timestamp sums."""
from collections import defaultdict,Counter
import hashlib,json
from pathlib import Path

def naive_prefix_lengths(rows):
 result=[]
 for i,current in enumerate(rows):
  limit=len(current['text'])
  for future in rows[i+1:]:
   j=0
   while j<min(limit,len(future['text'])) and current['text'][j]==future['text'][j]:j+=1
   limit=j
  result.append(limit)
 return result
def areas(rows,lengths):
 visible=stable=0.0
 for i in range(1,len(rows)):
  duration=rows[i]['observed']-rows[i-1]['observed'];assert duration>=0
  visible+=len(rows[i-1]['text'])*duration;stable+=lengths[i-1]*duration
 return visible,stable
def span_totals(spans):
 modified=sum(s['closing_observed']-s['first_observed'] for s in spans if s['retracted'])
 censored=sum(s['censor_observed']-s['first_observed'] for s in spans if not s['retracted'])
 return modified,censored
def load(p):return json.loads(Path(p).read_bytes())

def analyze(cfg,out):
 old=load(cfg['original_config']);oldroot=Path(cfg['original_results']);newroot=Path(cfg['exposure_results'])
 recorded=load(newroot/'SOURCE_EXPOSURES.json');index={(r['cell_id'],r['source_id'],r['mode'],r['convention']):r for r in recorded}
 checked=0;verified=[];finals=defaultdict(list)
 for cell in old['cells']:
  raw=Path(cell['consumer_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==cell['consumer_sha256']
  rows=[json.loads(x) for x in raw.decode('utf8').splitlines() if x.strip()]
  if cell['schema']=='core':rows=[dict(source_id=cell['session_source_map'][str(r['session_id'])],observed=r['observed_perf'],text=r['visible_text']) for r in rows]
  bysource=defaultdict(list)
  for r in rows:bysource[r['source_id']].append(r)
  spans=load(oldroot/'cells'/cell['cell_id']/'EDIT_AND_LCP_OCCURRENCE_LIFETIMES.json');curve_rows=load(newroot/'cells'/cell['cell_id']/'CURVES.json')
  for sid,observations in bysource.items():
   for mode in ('raw','whitespace_stripped'):
    series=[dict(r,text=r['text'] if mode=='raw' else ''.join(c for c in r['text'] if not c.isspace())) for r in observations]
    lengths=naive_prefix_lengths(series);visible,stable=areas(series,lengths)
    actual=[r for r in curve_rows if r['source_id']==sid and r['mode']==mode]
    assert len(actual)==len(series) and [r['retrospective_stable_prefix_code_points'] for r in actual]==lengths
    assert [r['observed'] for r in actual]==[r['observed'] for r in series]
    assert actual[-1]['terminal_zero_duration'] is True and actual[-1]['step_duration_seconds']==0
    checked+=len(series)
    finals[cell['bank'],cell['stage'],sid,mode].append(hashlib.sha256(series[-1]['text'].encode('utf8')).hexdigest())
    for convention in ('primary','alternate','LCP_suffix_identity'):
     relevant=[s for s in spans if s['source_id']==sid and s['mode']==mode and s['convention']==convention]
     modified,censored=span_totals(relevant);assert abs(modified+censored-visible)<1e-5
     r=index[cell['cell_id'],sid,mode,convention]
     assert abs(r['exposed_then_modified_code_point_seconds']-modified)<1e-6
     assert abs(r['right_censored_survivor_observed_code_point_seconds']-censored)<1e-6
     assert abs(r['retrospective_stable_prefix_code_point_seconds']-stable)<1e-6
     assert abs(r['total_observed_code_point_seconds']-visible)<1e-6
     assert r['observation_start']==series[0]['observed'] and r['observation_horizon']==series[-1]['observed']
     verified.append(dict(cell_id=cell['cell_id'],source_id=sid,mode=mode,convention=convention,
      modified_character_seconds=modified,right_censored_character_seconds=censored,visible_character_seconds=visible,stable_prefix_character_seconds=stable))
 groups=load(newroot/'FINAL_ACTUAL_TEXT_HASH_GROUPS.json')
 for r in groups:
  hashes=finals[r['bank'],r['stage'],r['source_id'],r['mode']]
  assert r['all_actual_final_text_bytes_equal']==(len(set(hashes))==1)
  assert sorted(hashes)==sorted(x['final_utf8_sha256'] for x in r['observations'])
 (out/'VERIFIED_SOURCE_METRICS.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf8')
 return dict(status='PASS_INDEPENDENT_ALL29_EXPOSURE_CURVES_HORIZONS_FINAL_TEXT_HASHES',cells=len(old['cells']),checked_curve_rows=checked,
  checked_exposure_identity_groups=len(verified),checked_final_text_groups=len(groups),new_model_calls=0,
  scope='Second implementation: direct comparisons against every future actual view, direct timestamp residence sums, and actual last-text SHA; no primary metric imports, no human-experience claim')
