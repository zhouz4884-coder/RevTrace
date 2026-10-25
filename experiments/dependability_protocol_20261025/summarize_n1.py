from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,statistics
W=Path(__file__).resolve().parent;R=W/'formal_collected/formal'
audit=json.loads((W/'formal_independent_audit_v2/SUMMARY.json').read_text())
assert audit['cells']==54
groups=defaultdict(list);runs={r['cell']:r for r in audit['runs']}
canonical_histories={};target_data={};comparisons=[]
for name,r in runs.items():
    config=json.loads((R/name/'config.json').read_text())
    method='omit' if config['diagnostic_omit_receive_freshness'] else 'standard' if config['async_implementation']=='standard' else 'full'
    order=config['post_compute_order'];window='none' if not order else 'covered' if order['proposal_window']==1 else 'ahead'
    groups[method,config['consumer_policy'],window].append(r)
    events=[json.loads(x) for x in (R/name/'events.jsonl').read_text().splitlines()]
    records=[json.loads(x) for x in (R/name/'worker_records.jsonl').read_text().splitlines()]
    jobs={e['job']['job_id']:e['job'] for e in records};results={e['job']['job_id']:e['result'] for e in records}
    hist=sorted([dict(session_id=e['session_id'],parent=e['parent'],version=e['version'],
        start=e['audio_start_sample'],end=e['audio_end_sample'],Z=e['segment_tokens'],P=e['next_prompt_tokens'],
        text=results[e['job_id']]['text']) for e in events if e['kind']=='commit'],key=lambda x:(x['session_id'],x['end']))
    canonical_histories[name]=hist
    target_data[name]={(e['job']['role'],e['job']['session_id']):(e['job'],e['result'])
        for e in ([json.loads(x) for x in (R/name/'ipc_completed_payloads.jsonl').read_text().splitlines()] if order else [])}
freeze=json.loads((R/'FREEZE.json').read_text());index={tuple(c[k] for k in ['method','consumer','window','order','repeat']):c for c in freeze['cells']}
name=lambda c:'-'.join(str(c[k]) for k in ['method','consumer','window','order','repeat'])
job_keys=['role','session_id','source_id','parent','prompt_tokens','chunk_id','chunk_advance',
    'audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','language','branch_generation']
for key,c in index.items():
    if c['order']!='proposal_first':continue
    other=dict(c,order='authority_first');left=name(c);right=name(other)
    assert canonical_histories[left]==canonical_histories[right]
    for rk,(j,r) in target_data[left].items():
        j2,r2=target_data[right][rk]
        logical=all(j.get(k)==j2.get(k) for k in job_keys)
        processed=r['model_input_audit']==r2['model_input_audit']
        output=all(r[k]==r2[k] for k in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit'])
        comparisons.append(dict(left=left,right=right,role=rk[0],session_id=rk[1],
            frozen_logical_input_equal=logical,actual_full_input_layout_equal=processed,complete_output_equal=output,
            qualified_fixed_input_output_pair=logical and processed and output))
assert len(comparisons)==192
first=next(iter(canonical_histories.values()))
assert all(h==first for h in canonical_histories.values()),'do not assume only same WER means same history'
group_rows=[]
for key,rs in sorted(groups.items()):
    v=dict(zip(['method','consumer','window'],key));v['runs']=len(rs)
    for k in ['stale_publications','incompatible_ahead_publications','illegal_actual_views','false_dual_deadline_credits','event_only_false_display_P99_pass']:
        v[k]=sum(r[k] for r in rs)
    for k in ['legal_goodput','legal_display_p99','commit_p99','GPU_J_per_audio_second_observed_window','consumer_erased_characters']:
        v[k+'_median']=statistics.median(r[k] for r in rs)
    group_rows.append(v)
summary={'status':'PASS_LOCAL_COMPLETE54_EVENTS_COST_QUALITY_AND_MATCHED_HISTORY_RECOUNT',
    'formal_cells':54,'reused_sources':4,'matched_order_run_pairs':24,
    'target_row_comparisons':192,'qualified_full_input_output_comparisons':sum(r['qualified_fixed_input_output_pair'] for r in comparisons),
    'logical_input_equal':sum(r['frozen_logical_input_equal'] for r in comparisons),
    'complete_output_equal':sum(r['complete_output_equal'] for r in comparisons),
    'canonical_full_history_equal_all54':True,'canonical_transitions_per_run':len(first),
    'WER_errors_per_run':sorted({r['WER_errors'] for r in runs.values()}),
    'WER_words_per_run':sorted({r['WER_words'] for r in runs.values()}),
    'stale_publications_all':sum(r['stale_publications'] for r in runs.values()),
    'incompatible_ahead_publications_all':sum(r['incompatible_ahead_publications'] for r in runs.values()),
    'illegal_actual_views_all':sum(r['illegal_actual_views'] for r in runs.values()),
    'false_dual_deadline_credits_all':sum(r['false_dual_deadline_credits'] for r in runs.values()),
    'event_only_false_display_P99_pass_runs':sum(r['event_only_false_display_P99_pass'] for r in runs.values()),
    'scope':'post-compute ordering/freshness study; one root-incompatible actual view in the existing incomplete snapshot Consumer, before the selected IPC intervention; complete two_lane RevTrace and Standard controls have no such view; not natural prevalence or exclusive performance win',
    'presentation_labels':{'standard-snapshot':'conventional owner plus snapshot Consumer ablation, NOT complete Standard Safe Async',
        'standard-two_lane':'complete Standard Safe Async with identical full protections',
        'full-snapshot':'RevTrace owner plus snapshot Consumer ablation, NOT complete end-to-end protocol',
        'full-two_lane':'complete RevTrace end-to-end protection'},
    'groups':group_rows}
(W/'N1_LOCAL_SUMMARY_v3.json').write_text(json.dumps(summary,indent=2)+'\n')
for file,rs in [('N1_GROUPS_v3.csv',group_rows),('N1_MATCHED_TARGETS_v3.csv',comparisons)]:
    with (W/file).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
print(json.dumps({k:v for k,v in summary.items() if k!='groups'}))
