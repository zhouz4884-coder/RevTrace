"""Document arithmetic from published/frozen outputs; not a new CPU experiment.

No original events, native_jobs, audio, model or raw Consumer are read. Only the
frozen298-row JOBS, bound historical cell summaries and existing content exports.
"""
from collections import Counter,defaultdict
import hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
inputs={}
def metadata(p):
 p=Path(p);inputs[str(p.resolve())]=dict(bytes=p.stat().st_size,sha256=sha(p));return load(p)
ledger_path=H/'results/LEDGER_v2/JOBS.json';jobs=metadata(ledger_path)
cfg=metadata(H/'LEDGER_CONFIG_v2.json');assert len(jobs)==298 and len(cfg['cells'])==16
content_root=R/'experiments/dsn_streamcorrect_independent_20261029/FINAL_CONTENT_RESULTS_v2'
content_runs=metadata(content_root/'RUNS.json');content_summary=metadata(content_root/'SUMMARY.json')
content_gate=metadata(content_root/'GATE.json');content_inputs=metadata(content_root/'INPUT_HASHES.json')
archive=metadata(R/'experiments/dsn_streamcorrect_independent_20261029/SERVICE_RESULTS_v1/COLLECTION_MANIFEST.json')
archive_by={r['path']:r for r in archive['files']};runs={r['cell_id']:r for r in content_runs}
assert len(runs)==16 and set(runs)=={c['cell_id'] for c in cfg['cells']}
bycell=defaultdict(list)
for r in jobs:bycell[r['cell_id']].append(r)
cells=[]
for c in cfg['cells']:
 local=R/'experiments/dsn_streamcorrect_independent_20261029/SERVICE_RESULTS_v1'/c['cell_id']/'SUMMARY.json'
 assert sha(local)==c['files']['summary']['sha256'];summary=metadata(local)
 historical=runs[c['cell_id']];assert summary['source_commit']==cfg['measured_neural_commit']
 assert historical['arm']==c['arm'] and historical['source_id']==c['source_id'] and historical['repeat']==c['repeat']
 assert historical['primary']==summary['primary']
 assert historical['primary']['raw_inputs']['config_sha256']==c['files']['config']['sha256']
 rawkey=c['cell_id']+'/consumer.jsonl';expected=content_inputs[rawkey]['sha256']
 assert expected==historical['primary']['raw_inputs']['consumer_sha256']
 assert expected==archive_by[rawkey]['sha256']
 matching=historical['raw_support']['original_credit_with_same_actual_G_complete_text_match']
 mismatching=historical['raw_support']['original_credit_with_same_actual_G_complete_text_mismatch']
 unknown=historical['raw_support']['original_credit_with_unknown_actual_G_reference_audio_seconds']
 credit=summary['primary']['dual_deadline_audio_credit_audio_seconds'] if 'dual_deadline_audio_credit_audio_seconds' in summary['primary'] else summary['primary']['dual_deadline_audio_credit_seconds']
 assert abs(matching+mismatching+unknown-credit)<1e-8
 jj=bycell[c['cell_id']];assert len({j['job_id'] for j in jj})==len(jj)
 for j in jj:assert (j['source_id'],j['arm'],j['repeat'])==(c['source_id'],c['arm'],c['repeat'])
 cells.append(dict(cell_id=c['cell_id'],source_id=c['source_id'],arm=c['arm'],repeat=c['repeat'],job_rows=len(jj),
  offered_audio_s=summary['primary']['offered_audio_seconds'],deadline_credit_audio_s=credit,
  timely_later_actual_G_fulltext_supported_audio_s=matching,timely_later_G_mismatching_audio_s=mismatching,timely_later_G_unknown_audio_s=unknown))
def budget(jj,cc):
 worker=sum(j['worker_reported_wall_s'] for j in jj)
 infer=sum(j['original_infer_wall_s'] for j in jj if j['original_infer_wall_s'] is not None)
 credit=sum(c['deadline_credit_audio_s'] for c in cc);support=sum(c['timely_later_actual_G_fulltext_supported_audio_s'] for c in cc)
 states={}
 for state in sorted({j['terminal_state'] for j in jj}):
  own=[j for j in jj if j['terminal_state']==state]
  states[state]=dict(jobs=len(own),worker_s=sum(j['worker_reported_wall_s'] for j in own),
   observed_infer_wall_s=sum(j['original_infer_wall_s'] for j in own if j['original_infer_wall_s'] is not None),
   missing_infer_timer_jobs=sum(j['original_infer_wall_s'] is None for j in own))
 return dict(cells=len(cc),jobs=len(jj),by_terminal=states,total_worker_s=worker,
  observed_infer_wall_s=infer,missing_infer_timer_jobs=sum(j['original_infer_wall_s'] is None for j in jj),
  native_model_evaluated_true=sum(j.get('native_model_evaluated') is True for j in jj),
  native_model_evaluated_false=sum(j.get('native_model_evaluated') is False for j in jj),
  native_model_evaluated_unknown=sum('native_model_evaluated' not in j for j in jj),
  offered_audio_s=sum(c['offered_audio_s'] for c in cc),deadline_credit_audio_s=credit,
  timely_later_actual_G_supported_audio_s=support,
  timely_later_G_mismatching_audio_s=sum(c['timely_later_G_mismatching_audio_s'] for c in cc),
  timely_later_G_unknown_audio_s=sum(c['timely_later_G_unknown_audio_s'] for c in cc),
  deadline_credit_per_occupied_worker_s=credit/worker,
  timely_later_actual_G_supported_credit_per_occupied_worker_s=support/worker)
all_arms={arm:budget([j for j in jobs if j['arm']==arm],[c for c in cells if c['arm']==arm]) for arm in sorted({j['arm'] for j in jobs})}
byrepeat=[dict(arm=arm,repeat=rep,**budget([j for j in jobs if j['arm']==arm and j['repeat']==rep],[c for c in cells if c['arm']==arm and c['repeat']==rep])) for arm in all_arms for rep in (0,1)]
for arm,row in all_arms.items():
 expected=content_summary['aggregates'][arm]
 assert abs(row['deadline_credit_audio_s']-expected['original_credit_seconds'])<1e-8
 assert abs(row['timely_later_actual_G_supported_audio_s']-expected['raw_same_actual_G_supported_credit'])<1e-8
base,full=all_arms['two_full_early'],all_arms['two_full_spec_early']
comparisons=dict(worker_cost_relative_change=full['total_worker_s']/base['total_worker_s']-1,
 deadline_credit_per_worker_relative_change=full['deadline_credit_per_occupied_worker_s']/base['deadline_credit_per_occupied_worker_s']-1,
 supported_credit_per_worker_relative_change=full['timely_later_actual_G_supported_credit_per_occupied_worker_s']/base['timely_later_actual_G_supported_credit_per_occupied_worker_s']-1)
for p,record in inputs.items():assert sha(p)==record['sha256']
result=dict(record_type='DERIVED_FROM_FROZEN_OUTPUT_NOT_NEW_RUN',derivation_script_sha256=sha(__file__),
 parent_ledger_experiment='REVTRACE-V16-FULL-JOB-LEDGER-20261111-V2',parent_ledger_execution_source='817ebbbabce15e6d9c2d84f8435bbbc8640d8b22',
 original_neural_source=cfg['measured_neural_commit'],scope='Only old four-speaker16-cell bdfa bank,298 dispatched jobs; two repeats stay within source; no new8/old14/LCP bank mixed',
 input_files=inputs,formulas=dict(worker='sum worker_reported_wall_s over ALL dispatched jobs including abandoned/discarded',
  observed_infer='sum measured original_infer_wall_s; missing timers separately counted, never filled as zero',
  deadline_productivity='sum original D2/C8 credit audio seconds / total occupied worker seconds',
  supported_productivity='sum timely later actual-G wholetext matching credit audio seconds / total occupied worker seconds'),
 all_arms=all_arms,by_repeat=byrepeat,cells=cells,comparisons=comparisons,
 limits='Occupied-worker productivity is an offline resource-denominator ratio, not service-wall goodput, GPU active seconds, energy efficiency, human accuracy or a causal retained-work saving estimate. All24 abandoned ASR infer timers remain missing.',
 new_original_raw_scans=0,new_neural_calls=0,new_GPU_runs=0)
out=H/'LEDGER_FULL_BUDGET_DERIVED_v1.json'
with out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(output=str(out),all_arms=all_arms,by_repeat=byrepeat,comparisons=comparisons),ensure_ascii=False))
