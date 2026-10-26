"""Whole-run grouped costs; never sum overlapping clocks or reclassify CPU as GPU."""
from pathlib import Path
import csv,hashlib,json,statistics
W=Path(__file__).resolve().parent;O=W/'synthesis_data_v2';O.mkdir(exist_ok=False)
p=W/'N5_NORMAL_PRIMARY_v1.json';d=json.loads(p.read_text());assert d['cells']==105
metrics=['all_offered_audio_goodput_2_8','display_P50','display_P95','display_P99','commit_view_P50','commit_view_P95','commit_view_P99',
 'GPU_J_per_offered_audio_second','all_offered_WER_percent','all_offered_character_error_percent','valid_provisional_ahead_coverage_per_offered_audio',
 'accepted_debt_peak_audio_seconds','reserved_debt_peak_audio_seconds','exact_pending_unaccepted_peak_audio_seconds',
 'exact_unadmitted_offered_peak_audio_seconds','physical_batches','recorded_complete_rows','controller_CPU_seconds',
 'input_data_fsync_calls_including_genesis','input_fsync_seconds','canonical_commit_group_fsync_calls','canonical_commit_group_fsync_seconds',
 'canonical_owner_WAL_call_seconds','trusted_render_host_wall_seconds','consumer_CPU_seconds','actual_row_emission_to_owner_receive_P99',
 'actual_publication_to_Consumer_applied_P99','consumer_audio_rollback_events','consumer_total_retracted_audio_seconds','consumer_erased_characters',
 'input_journal_bytes','canonical_journal_bytes']
rows=[];raw=[]
for load,method in sorted({(r['episode'].rsplit('-r',1)[0].split('-',1)[1],r['method']) for r in d['episodes']}):
 rs=[r for r in d['episodes'] if r['method']==method and r['episode'].startswith(method+'-'+load+'-r')];assert len(rs)==3
 row=dict(workload=load,method=method,runs=3,whole_dual_P99_passes=sum(r['whole_run_dual_P99_pass'] for r in rs),
  recorded_unauthorized_admissions=sum(r['unauthorized_admissions'] for r in rs),
  recorded_stale_or_root_invalid_views=sum(r['stale_publications']+r['root_incompatible_actual_views'] for r in rs),
  explicit_rejected_sessions=sum(r['rejected_sessions'] for r in rs),unfinished_sources=sum(r['unfinished_sources'] for r in rs))
 for key in metrics:
  v=[r[key] for r in rs]
  # Missing/infinite latency cannot be silently dropped by aggregation.
  row[key+'_median']=None if any(x is None for x in v) else statistics.median(v)
  raw.append(dict(workload=load,method=method,metric=key,each=v))
 rows.append(row)
assert len(rows)==35
with (O/'NORMAL_FULL_COSTS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(O/'NORMAL_FULL_COSTS.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
  groups=rows,repeats=raw,no_new_neural_calls=True,
  scope='actual repeated-run medians, no pooled cross-workload ratio or equal-quality claim; component CPU/host clocks may overlap and are not totalCPUenergy'),indent=2)+'\n')
print(json.dumps(dict(groups=len(rows),rows=105,readouts=len(metrics))))
