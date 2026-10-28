"""Compact descriptive tables from complete frozen H3 recounts; no inference."""
import collections,hashlib,json,statistics
from pathlib import Path
T=Path(__file__).resolve().parents[1];D=T/'H3_RESULTS_v2'
inputs={}
def read(name):
 p=D/name;inputs[name]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text(encoding='utf8'))
runs=read('aggregate/RUNS.json');use={r['cell_id']:r for r in read('usefulness/RUNS.json')}
opp=read('opportunities/STRATIFIED_RATES.json');effects=read('aggregate/FACTORIAL_EFFECTS.json')
history=read('aggregate/CANONICAL_HISTORY_GROUPS.json');positive=read('aggregate/STANDARD_POSITIVE_CONTROL.json')
strata=collections.defaultdict(list)
for r in runs:strata[tuple(r[k] for k in ['phase','adapter','rho','arrival','arm'])].append(r)
tables=[]
for key,rows in strata.items():
 row=dict(zip(['phase','adapter','rho','arrival','arm'],key));row['cells']=len(rows)
 row['cohorts']=[r['cohort'] for r in rows]
 for k in ['offered_audio_seconds','dual_credited_audio_seconds','audio_rollback_events','audio_rollback_seconds','rollback_area_audio_seconds_x_wall_seconds','erased_visible_characters','WER_errors','WER_reference_words']:
  row[k+'_sum']=sum(r[k] for r in rows)
 for k in ['display_P99','commit_view_P99','GPU_J_per_offered_audio_second','all_offered_audio_goodput_2_8','longest_actual_visible_progress_gap_seconds']:
  row[k+'_median']=statistics.median(r[k] for r in rows);row[k+'_range']=[min(r[k] for r in rows),max(r[k] for r in rows)]
 row['whole_run_dual_P99_pass_count']=sum(r['whole_run_dual_P99_pass'] for r in rows)
 row['pooled_WER_percent']=100*row['WER_errors_sum']/row['WER_reference_words_sum']
 ur=[use[r['cell_id']] for r in rows]
 row['raw_equal_or_certified_dual_timely_audio_seconds']=sum(r['first_certified_dual_timely_audio_seconds']+r['first_ahead_raw_equal_dual_timely_audio_seconds'] for r in ur)
 row['normalized_equal_or_certified_dual_timely_audio_seconds']=sum(r['first_certified_dual_timely_audio_seconds']+r['first_ahead_normalized_equal_dual_timely_audio_seconds'] for r in ur)
 row['ahead_raw_different_session_wall_seconds']=sum(r['ahead_view_raw_different_session_wall_seconds'] for r in ur)
 row['ahead_unmatched_same_F_views']=sum(r['ahead_view_unmatched_no_selected_same_f_count'] for r in ur)
 orows=[r for r in opp if r['clock_scope']=='consumer_apply' and tuple(r[k] for k in ['phase','adapter','rho','arrival','arm'])==key]
 for k in ['canonical_updates','ahead_updates','compatible_opportunities','compatible_retained','compatible_cleared','incompatible_ahead_updates','incompatible_cleared']:row[k]=sum(r[k] for r in orows)
 tables.append(row)
output=dict(scope='descriptive stratified summaries; independent source N=24, not110; paired_jitter reuses8 sources; no pooled population claim',tables=tables,
 all_history_groups_equal=all(r['all_recorded_histories_equal'] for r in history),history_group_count=len(history),
 positive_control_same_history_pairs=sum(r['canonical_histories_equal'] for r in positive),positive_control_pairs=len(positive),
 whole_run_dual_P99_pass_count=sum(r['whole_run_dual_P99_pass'] for r in runs),
 per_block=[{k:r[k] for k in ['paired_block','phase','adapter','rho','arrival','cohort','repeat']}|{'effects':{k:r['effects'][k] for k in ['dual_audio_fraction','display_P99','audio_rollback_events','erased_visible_characters']}} for r in effects])
(D/'COMPACT_TABLES.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
(D/'COMPACT_TABLES_RECORD.json').write_text(json.dumps(dict(evidence_tier='offline derived tables',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inputs=inputs,new_GPU_calls=0),indent=2)+'\n',encoding='utf8')
for r in tables:
 print('|'.join(str(r[k]) for k in ['phase','adapter','rho','arrival','arm']),json.dumps({k:r[k] for k in ['dual_credited_audio_seconds_sum','display_P99_median','audio_rollback_events_sum','erased_visible_characters_sum','pooled_WER_percent','whole_run_dual_P99_pass_count','normalized_equal_or_certified_dual_timely_audio_seconds','compatible_opportunities','compatible_retained','compatible_cleared']}))
print(json.dumps({k:v for k,v in output.items() if k not in ['tables','per_block']}))
