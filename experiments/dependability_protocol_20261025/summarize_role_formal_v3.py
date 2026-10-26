"""Frozen metric, explicit P/Z/Y and paired quality; not a deployment benchmark."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
from audit_role_probe_v2 import marker
from audit_n5 import lines
ap=argparse.ArgumentParser();ap.add_argument('--pilot-control',action='store_true');args=ap.parse_args()
kind='pilot' if args.pilot_control else 'formal';expected=8 if args.pilot_control else 64
W=Path(__file__).resolve().parent;root=W/f'role_{kind}_collected_v2/{kind}'
primary=json.loads((W/f'role_{kind}_primary_v2/SUMMARY.json').read_text())
cost=json.loads((W/f'ROLE_{kind.upper()}_WAL_COST_AUDIT_v3.json').read_text())
assets=json.loads((W/f'ROLE_{kind.upper()}_ASSET_REPLAY_v2.json').read_text())
assert primary['case_count']==len(cost['cases'])==assets['cases']==expected
assert all(p['pre_injection_actual_input_and_native_Z_matched'] for p in primary['pairs'])
C={r['case']:r for r in cost['cases']};A={r['case']:r for r in assets['runs']};out=[];hist={}
for r in primary['cases']:
 name=r['case'];c=C[name];a=A[name];D=root/name
 assert c['full_operator_window_energy_measured']
 cons=lines(D/'consumer.jsonl');events=lines(D/'events.jsonl')
 new=dict(r);new.pop('prelude_native_Z');new.pop('original_candidate_native_Z');new.pop('original_parent_P_before_injection')
 new.update(selected_verify_seconds=c['selected_at6_verification_seconds'],selected_generation_seconds=c['selected_at6_actual_generation_seconds'],
  selected_physical_neural_phases=c['selected_at6_neural_calls'],all_operator_GPU_joules=c['observed_support_GPU_joules_NOT_full_window_if_coverage_below1'],
  operator_seconds=c['operator_window_seconds'],worker_init_seconds_separate=c['worker_init_seconds'],
  canonical_fsync_calls=c['canonical_commit_fsync_calls'],canonical_fsync_seconds=c['canonical_commit_fsync_seconds'],
  actual_provisional_payload_visible=any(marker(x['visible_text'])['frozen_substring'] and x['valid_visible_frontier']>x['certified_frontier'] for x in cons),
  actual_certified_payload_visible=any(marker(x['certified_text'])['frozen_substring'] for x in cons),
  future_authority_processed_marker_calls=sum(x['purpose']=='future-real-authority-continuation' and x['actual_processed_IDs_have_frozen_substring'] for x in a['input_detections']),
  future_private_neural_new_Z_marker=any(x['purpose']=='future-private-at-8s-before-authority-install' and x['original_worker_Z_has_substring'] for x in a['input_detections']))
 out.append(new)
 views={e['version']:e['text'] for e in events if e['kind']=='canonical-display'}
 hist[r['method'],r['source_id'],r['traffic'],r['repeat']]=[
  dict({k:e[k] for k in ['audio_start_sample','audio_end_sample','segment_tokens','next_prompt_tokens']},text=views[e['version']]) for e in events if e['kind']=='commit']
groups=[]
for method in ['renderer_only','strict','revtrace','standard']:
 for traffic in ['clean','coherent-proposer']:
  rs=[r for r in out if r['method']==method and r['traffic']==traffic];assert len(rs)==expected//8
  groups.append(dict(method=method,traffic=traffic,cases=len(rs),unique_sources=len({r['source_id'] for r in rs}),fresh_repeats=len({r['repeat'] for r in rs}),
   private_future_marker_input_cases=sum(r['private_future_processed_prefix_marker']['frozen_substring'] for r in rs),
   future_private_neural_new_Z_marker_cases=sum(r['future_private_neural_new_Z_marker'] for r in rs),
   actual_provisional_payload_visible_cases=sum(r['actual_provisional_payload_visible'] for r in rs),
   actual_certified_payload_visible_cases=sum(r['actual_certified_payload_visible'] for r in rs),
   future_authority_consumed_marker_cases=sum(r['future_authority_processed_marker_calls']>0 for r in rs),
   final_substring_marker_cases=sum(r['final_marker']['frozen_substring'] for r in rs),
   final_whole_word_marker_cases=sum(r['final_marker']['exact_whole_words'] for r in rs),
   word_errors=sum(r['word_errors'] for r in rs),reference_words=sum(r['reference_words'] for r in rs),
   WER_percent=100*sum(r['word_errors'] for r in rs)/sum(r['reference_words'] for r in rs),
   selected_verify_seconds_median=statistics.median(r['selected_verify_seconds'] for r in rs),
   selected_generation_seconds_median=statistics.median(r['selected_generation_seconds'] for r in rs),
   all_operator_GPU_joules_median=statistics.median(r['all_operator_GPU_joules'] for r in rs),
   same_contract_operator_calls_median=statistics.median(r['physical_batches'] for r in rs),
   unchecked_candidate_installs=sum(r['unchecked_candidate_installs'] for r in rs)))
repeated=[]
for method,source_id,traffic,_ in sorted(hist):
 if _!=0 or (method,source_id,traffic,1) not in hist:continue
 repeated.append(dict(method=method,source_id=source_id,traffic=traffic,
  normalized_actual_Canonical_history_equal=hist[method,source_id,traffic,0]==hist[method,source_id,traffic,1]))
O=W/f'role_{kind}_synthesis_v4';O.mkdir(exist_ok=False)
for file,rs in [('CASES.csv',out),('GROUPS.csv',groups),('PAIRS.csv',primary['pairs']),('REPEAT_HISTORIES.csv',repeated)]:
 with (O/file).open('w',newline='') as f:
  fields=list(rs[0]) if rs else ['method','source_id','traffic','normalized_actual_Canonical_history_equal']
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)
summary=dict(status=f'COMPLETE{expected}_SAME_CONTRACT_OPERATOR_SOURCE_SELECTION_CONSUMER_WAL_COST_ASSETS',groups=groups,
 pairs=primary['pairs'],same_input_fresh_process_repeat_histories=repeated,
 stage=kind,cases=expected,pilots_included_in64=False,unique_acoustic_sources=len({r['source_id'] for r in out}),metadata_only_shadow_not_extra_GPU_case=True,
 limits='fixed role-restricted coherentProposer intervention; private provisional contamination permitted; no trustedAuthority compromise, natural incidence, new neural amplification, production security, online SLO/goodput or performance superiority inferred',
 input_sha256={f:hashlib.sha256((W/f).read_bytes()).hexdigest() for f in [f'role_{kind}_primary_v2/SUMMARY.json',f'ROLE_{kind.upper()}_WAL_COST_AUDIT_v3.json',f'ROLE_{kind.upper()}_ASSET_REPLAY_v2.json']})
(O/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(groups=groups,all_repeat_histories_equal=all(r['normalized_actual_Canonical_history_equal'] for r in repeated) if repeated else None)))
