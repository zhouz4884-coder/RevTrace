"""Actual-Consumer character exposure and retrospective horizon-censored curves."""
from collections import defaultdict,Counter
import csv,hashlib,json
from pathlib import Path
from exposure_curves import stable_prefix_curve,exposure_from_spans

def load(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def adapt(cell):
 rows=[json.loads(x) for x in Path(cell['consumer_path']).read_text(encoding='utf8').splitlines() if x.strip()]
 if cell['schema']=='core':rows=[dict(source_id=cell['session_source_map'][str(r['session_id'])],observed=r['observed_perf'],text=r['visible_text']) for r in rows]
 return rows
def put(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def analyze(cfg,out):
 old=load(cfg['original_config']);oldroot=Path(cfg['original_results']);sources=[];all_curves=[];finals=defaultdict(list)
 for cell in old['cells']:
  assert sha(cell['consumer_path'])==cell['consumer_sha256'];rows=adapt(cell)
  spans=load(oldroot/'cells'/cell['cell_id']/'EDIT_AND_LCP_OCCURRENCE_LIFETIMES.json')
  bysource=defaultdict(list)
  for i,r in enumerate(rows):bysource[r['source_id']].append(dict(r,row_index=i))
  cell_curves=[]
  for sid,observations in sorted(bysource.items()):
   for mode in ('raw','whitespace_stripped'):
    sequence=[dict(r,text=r['text'] if mode=='raw' else ''.join(c for c in r['text'] if not c.isspace())) for r in observations]
    curve=stable_prefix_curve(sequence)
    meta=dict(bank=cell['bank'],stage=cell['stage'],arm=cell['arm'],cell_id=cell['cell_id'],source_id=sid,mode=mode,repeat=cell['repeat'],cohort=cell['cohort'])
    for point in curve['curves']:
     value=dict(meta,**point);cell_curves.append(value);all_curves.append(value)
    final=sequence[-1]['text'];finals[cell['bank'],cell['stage'],sid,mode].append(dict(cell_id=cell['cell_id'],arm=cell['arm'],repeat=cell['repeat'],
     final_observed=sequence[-1]['observed'],final_code_points=len(final),final_utf8_sha256=hashlib.sha256(final.encode('utf8')).hexdigest()))
    for convention in ('primary','alternate','LCP_suffix_identity'):
     ss=[s for s in spans if s['source_id']==sid and s['mode']==mode and s['convention']==convention]
     family='lcp_suffix_identity' if convention=='LCP_suffix_identity' else 'minimum_edit'
     exposure=exposure_from_spans(ss,curve,family)
     sources.append(dict(meta,convention=convention,**exposure,
      retrospective_stable_prefix_code_point_seconds=curve['retrospective_stable_prefix_code_point_seconds'],
      volatile_suffix_code_point_seconds=curve['volatile_suffix_code_point_seconds'],observed_horizon_seconds=curve['observed_horizon_seconds']))
  target=out/'cells'/cell['cell_id'];target.mkdir(parents=True)
  put(target/'CURVES.json',cell_curves)
 group=defaultdict(Counter)
 for r in sources:
  key=tuple(r[k] for k in ('bank','stage','arm','mode','convention'))
  for field in ('modified_identity_code_points','exposed_then_modified_code_point_seconds','right_censored_surviving_code_points',
   'right_censored_survivor_observed_code_point_seconds','total_observed_code_point_seconds','retrospective_stable_prefix_code_point_seconds',
   'volatile_suffix_code_point_seconds','observed_horizon_seconds'):group[key][field]+=r[field]
 aggregates=[dict(zip(('bank','stage','arm','mode','convention'),key),**dict(values)) for key,values in sorted(group.items())]
 final_groups=[]
 for key,items in sorted(finals.items()):
  expected=5 if key[0]=='H3_primary24_qwen_staggered' else (3 if key[1]=='formal' else 1)
  assert len({x['arm'] for x in items})==expected
  final_groups.append(dict(bank=key[0],stage=key[1],source_id=key[2],mode=key[3],expected_arms=expected,
   observed_arms=sorted({x['arm'] for x in items}),observations=items,
   all_actual_final_text_bytes_equal=len({x['final_utf8_sha256'] for x in items})==1,
   cross_arm_test=expected>1))
 put(out/'SOURCE_EXPOSURES.json',sources);put(out/'AGGREGATES.json',aggregates);put(out/'FINAL_ACTUAL_TEXT_HASH_GROUPS.json',final_groups)
 with (out/'STABLE_PREFIX_CURVES.csv').open('w',encoding='utf8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(all_curves[0]));w.writeheader();w.writerows(all_curves)
 return dict(status='PASS_ALL29_EXPOSURE_AREA_AND_HORIZON_CURVES',cells=len(old['cells']),curve_rows=len(all_curves),source_mode_conventions=len(sources),
  aggregates=aggregates,final_text_comparisons=dict(groups=len(final_groups),cross_arm_groups=sum(r['cross_arm_test'] for r in final_groups),
   unequal_groups=sum(not r['all_actual_final_text_bytes_equal'] for r in final_groups)),
  interpretation='Observed code-point residence exposure proxy; minimum-edit identity is alignment dependent. Stable prefix known retrospectively only through each actual source horizon; terminal duration0 and future unknown. Not validated human experience or causal serving benefit.',new_model_calls=0)
