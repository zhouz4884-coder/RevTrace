"""Arithmetic on completed frozen shadow output, never original model/raw logs."""
from pathlib import Path
from collections import defaultdict
import hashlib,json
H=Path(__file__).resolve().parent;O=H/'RESULTS_V2';inputs={}
def load(p):
 b=p.read_bytes();inputs[p.name]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());return json.loads(b)
table=load(O/'ALL24_RULE_TABLE.json');totals=load(O/'ARM_TOTALS.json');activation=[]
for p in sorted(O.glob('*_LA2_PREFIX.json')):
 x=load(p);s=x['summary'];cell=s['cell_id'];la=load(O/(cell+'_LA2_CP_ROWS.json'));canon=load(O/(cell+'_canonical_only_ROWS.json'))
 if len(la)!=len(canon) or [r['observed'] for r in la]!=[r['observed'] for r in canon]:raise ValueError('observer clocks differ')
 ahead=[a for a,b in zip(la,canon) if a['visible_frontier']>b['visible_frontier']]
 actual=[a for a,b in zip(la,canon) if a['kind']=='actual_Consumer_delivery' and a['visible_frontier']>b['visible_frontier']]
 area=sum((la[i+1]['observed']-a['observed'])*(a['visible_frontier']-b['visible_frontier'])/16000 for i,(a,b) in enumerate(zip(la[:-1],canon[:-1])) if a['visible_frontier']>b['visible_frontier'])
 row=dict(cell_id=cell,source_id=s['source_id'],strategy=s['strategy'],repeat=s['repeat'],
  updates=s['counts']['agreement']['updates'],ordinary_extensions=s['counts']['agreement']['ordinary_extensions'],
  canonical_resets=s['counts']['agreement']['canonical_resets'],ignored_same_or_older=s['counts']['agreement']['ignored_same_or_older_frontier'],
  terminal_releases=s['counts']['agreement']['terminal_releases'],
  prefix_rows_with_unmapped=s['rows_with_unmapped_code_points'],maximum_unmapped_code_points=s['maximum_unmapped_code_points'],
  actual_delivery_rows_ahead_of_canonical_only=len(actual),unique_whole_view_identities_ahead_of_canonical_only=len({r['candidate_identity'] for r in ahead}),
  mapped_ahead_audio_seconds_x_wall_seconds=area,
  free_prefix_retired_characters=s['text']['raw']['primary']['retired_characters'],
  free_prefix_retired_character_seconds=s['text']['raw']['primary']['retired_character_seconds'])
 activation.append(row)
byarm=[]
for arm in sorted({r['strategy'] for r in table}):
 data=[r for r in activation if r['strategy']==arm]
 armrows=[r for r in table if r['strategy']==arm]
 for rule in ('actual_SUP','canonical_only','fixed_lag_0p5','LA2_CP'):
  selected=[r for r in armrows if r['rule']==rule]
  known=sum(r['observed_within_D_coverage_audio_seconds_x_wall_seconds'] for r in selected)
  censored=sum(r['right_censored_within_D_audio_seconds_x_wall_seconds'] for r in selected)
  base=next(r for r in totals if r['strategy']==arm and r['rule']==rule)
  byarm.append(dict(base,credit_percent=100*base['offline_shadow_credit_audio_seconds']/base['offered_audio_seconds'],
   observed_within_D_coverage_audio_seconds_x_wall_seconds=known,within_D_coverage_upper_bound=known+censored,
   right_censored_coverage_audio_seconds_x_wall_seconds=censored,
   frontier_retreat_events=sum(r['frontier_retreats']['count'] for r in selected),
   LA2_ordinary_extensions=sum(r['ordinary_extensions'] for r in data) if rule=='LA2_CP' else None,
   LA2_unique_mapped_whole_views_ahead_of_canonical_only=sum(r['unique_whole_view_identities_ahead_of_canonical_only'] for r in data) if rule=='LA2_CP' else None))
contrasts=[]
for cell in sorted({r['cell_id'] for r in table}):
 group={r['rule']:r for r in table if r['cell_id']==cell}
 a=group['LA2_CP'];c=group['canonical_only'];base=group['actual_SUP']
 contrasts.append(dict(cell_id=cell,source_id=a['source_id'],speaker_id=a['speaker_id'],strategy=a['strategy'],repeat=a['repeat'],
  LA2_minus_actual_credit_audio_seconds=a['offline_shadow_dual_credit_audio_seconds']-base['offline_shadow_dual_credit_audio_seconds'],
  LA2_minus_canonical_credit_audio_seconds=a['offline_shadow_dual_credit_audio_seconds']-c['offline_shadow_dual_credit_audio_seconds'],
  LA2_minus_actual_primary_retired_characters=a['text']['raw']['primary']['retired_characters']-base['text']['raw']['primary']['retired_characters']))
sourcefinal=defaultdict(set)
for r in table:sourcefinal[r['source_id']].add(r['text']['raw']['primary']['final_text_sha256'])
out=dict(record_type='DERIVED_FROM_FROZEN_SHADOW_OUTPUT_NOT_NEW_RUN',inputs=inputs,formulae=dict(
 credit_percent='100 * frozen offline credit / frozen all-offered audio seconds',
 mapped_ahead_area='sum recorded output segment dt * (LA2 real whole-view F - canonical-only F)/16000 where positive',
 credit_difference='same cell and recorded schedule only; no alternative model computation or additive arm claim'),
 arm_rule_totals=byarm,per_cell_activation=activation,per_cell_contrasts=contrasts,
 final_raw_text_SHA_sets={k:sorted(v) for k,v in sourcefinal.items()},all_rule_final_SHA_equal_per_source=all(len(v)==1 for v in sourcefinal.values()))
target=H/'BOUNDED_INTERPRETATION_TABLES_V2.json'
with target.open('x',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(file=str(target),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),all_final_SHA_equal=out['all_rule_final_SHA_equal_per_source'])))
