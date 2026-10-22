"""Independent cross-table and raw-clock checks; no model execution."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,statistics

W=Path(__file__).resolve().parent
def rows(p):return list(csv.DictReader(p.open(newline='')))
A=W/'collected_evidence_v1/collected/formal_v1_audit_v3'
original={(r['cell'],r['source_id'],r['frontier_sample']):r for r in rows(A/'COMMON_FRONTIERS.csv')}
actual=rows(W/'C2_RAW_DIAGNOSTIC_v1/FIRST_LEGAL_VIEW.csv')
assert len(actual)==5868
maximum_error=0
for r in actual:
 old=original[r['cell'],r['source_id'],r['frontier_sample']]
 error=abs(float(old['display'])-float(r['display_s']))
 maximum_error=max(maximum_error,error);assert error<1e-8
vis=rows(W/'C2_RAW_DIAGNOSTIC_v1/CELL_VISIBILITY.csv')
for v in vis:
 c=v['cell'];a=[r for r in actual if r['cell']==c]
 assert len(a)==int(v['frontiers'])
 misses=[r for r in a if float(r['display_s'])>2]
 assert len(misses)==int(v['miss_frontiers'])
 assert abs(sum(float(r['audio_seconds']) for r in misses)-float(v['miss_audio_s']))<1e-8
ex=rows(W/'C2_RESIDUAL_OPPORTUNITY_v1/PENDING_CONFLICT_AND_SLACK.csv')
dg=[r for r in ex if r['method']=='dgft']
fr=rows(W/'C2_RAW_DIAGNOSTIC_v1/FAULT_RESPONSE.csv')
delay={}
for method in ['fine','dgft']:
 rs=[r for r in fr if r['cell'].startswith(method+'-sync16-F2-')]
 assert len(rs)==48
 delay[method]={'events':len(rs),'source_count':len({r['source_id'] for r in rs}),
  'first_new_parent_proposal_enqueue_after_fault_done_median_s':statistics.median(float(r['first_new_parent_proposal_enqueue_after_fault_done_s']) for r in rs),
  'injected_new_token_total':sum(int(r['fault_new_tokens']) for r in rs),
  'not_independent_subjects_or_isolated_causal_effect':True}
out={'status':'PASS_C2_DERIVED_AND_RAW_AGREEMENT','raw_cells':36,'first_views':len(actual),
 'maximum_original_vs_raw_reconstructed_display_difference_s':maximum_error,
 'dgft_pending_known_mismatch_exposures':len(dg),
 'dgft_exposures_with_positive_deadline_slack':sum(float(r['display_deadline_slack_s'])>0 for r in dg),
 'dgft_exposures_with_positive_slack_and_observed_authority_gap_ge1s':sum(float(r['display_deadline_slack_s'])>0 and float(r['next_actual_authority_worker_start_gap_s'])>=1 for r in dg),
 'same_case_raw_witnesses_and_not_a_causal_algorithm_evaluation':True,
 'observed_reanchoring_delay':delay,'new_GPU_calls':0,
 'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(W/'C2_BOTTLENECK_v1/INDEPENDENT_VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
