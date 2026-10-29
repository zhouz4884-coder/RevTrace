"""Post-run native feedback characterization; never changes the witness gate.

Whitespace-normalized surface difference is not semantic benefit. Exact state
comparisons require the complete actual same-source input state and frontier.
No native runtime/model code or approximate text-to-state oracle is imported.
"""
import argparse,collections,datetime,hashlib,json,pathlib,platform,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in pathlib.Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def hfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def surface(before,after):
    if before==after:return 'raw_equal'
    if ''.join(before.split())==''.join(after.split()):return 'whitespace_only_surface_difference'
    return 'nonwhitespace_surface_difference_benefit_unknown'
def characterize_cell(cell):
    out=pathlib.Path(cell['out']);p=out/'native_jobs.jsonl'
    if not p.exists():return dict(cell_id=cell['cell_id'],stage=cell['stage'],status='UNEXECUTED_OR_NO_NATIVE_COMPLETIONS')
    jobs=lines(p);private=collections.defaultdict(list);updates=[];pairs=[]
    for j in jobs:
        if j['record']['role']=='private':
            private[(j['source_id'],j['record']['start'],j['record']['end'],canonical(j['start']))].append(j)
    for j in jobs:
        r=j['record']
        if r['role']!='authority':continue
        c=r['selected_correction']
        if c is not None:
            before=c['candidates'][0];after=(c['previous_transcription']+c['corrected_appended_text']).strip()
            if (before!=after)!=r['selection_changed']:raise ValueError('raw original gate classification changed')
            previous=c['previous_transcription'].rstrip('\ufffd').strip();candidate=before.rstrip('\ufffd').strip()
            continuation=candidate[len(previous):].strip() if candidate.startswith(previous) else None
            updates.append(dict(source_id=j['source_id'],job_id=j['job_id'],frontier=r['end'],
                original_raw_selection_changed=r['selection_changed'],surface_class=surface(before,after),
                candidate_continuation=continuation,selected_continuation=c['corrected_appended_text'],
                selected_continuation_empty=not bool(c['corrected_appended_text'].strip()),
                candidate_and_selected_both_empty=continuation=='' and not c['corrected_appended_text'].strip(),
                native_all_candidate_texts=c['candidates'],previous_transcription=c['previous_transcription'],
                chosen_full_text=after,selected_appended_token_ids=c.get('corrected_appended_token_ids'),
                actual_returned_token_ids=r['token_ids'],actual_start_state_sha=r['start_state'],actual_end_state_sha=r['end_state'],
                semantic_correctness_or_benefit_inferred=False))
        key=(j['source_id'],r['start'],r['end'],canonical(j['start']))
        for q in private.get(key,[]):
            qr=q['record'];changed=sorted(k for k in set(j['end'])|set(q['end']) if j['end'].get(k)!=q['end'].get(k))
            pairs.append(dict(source_id=j['source_id'],authority_job=j['job_id'],private_job=q['job_id'],start=r['start'],end=r['end'],
                complete_start_state_equal=j['start']==q['start'],complete_end_state_equal=j['end']==q['end'],
                actual_returned_token_ids_equal=r['token_ids']==qr['token_ids'],actual_text_equal=r['text']==qr['text'],
                changed_complete_end_state_fields=changed,authority_end_state_sha=r['end_state'],private_end_state_sha=qr['end_state']))
    gate=read(out/'GATE.json') if (out/'GATE.json').exists() else None
    return dict(cell_id=cell['cell_id'],stage=cell['stage'],cohort=cell['cohort'],arm=cell['arm'],repeat=cell['repeat'],
        status='CHARACTERIZED_ACTUAL_COMPLETIONS',cell_gate_preserved=gate,native_completion_count=len(jobs),
        authority_feedback_updates=len(updates),surface_counts=dict(collections.Counter(x['surface_class'] for x in updates)),
        empty_selected_continuations=sum(x['selected_continuation_empty'] for x in updates),
        both_candidate_and_selected_continuations_empty=sum(x['candidate_and_selected_both_empty'] for x in updates),
        actual_same_input_authority_private_pairs=len(pairs),same_input_full_end_matches=sum(x['complete_end_state_equal'] for x in pairs),
        raw_native_jobs_sha256=hfile(p),updates=updates,same_input_full_state_pairs=pairs)
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--controller-out',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    commit=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True).strip():raise ValueError('analysis source must be frozen and clean')
    a.out.mkdir(parents=True,exist_ok=False);plan=read(a.plan)
    record=dict(experiment_id='SC_NATIVE_FEEDBACK_CHARACTERIZATION_V1',code_commit=commit,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        frozen_config=str(a.plan),frozen_config_sha256=hfile(a.plan),environment=dict(python=sys.version,platform=platform.platform(),dependencies='Python standard library only'),
        native_runtime_commit=plan['source_commit'],raw_result_location='unchanged per-cell native jobs on designated experiment disk',
        aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),
        scope='post-run explanatory classification only; original witness gate, source set, service measurements and native choices unchanged')
    (a.out/'RUN_RECORD.json').write_text(json.dumps(record,indent=2));rows=[];failures=[]
    for cell in plan['cells']:
        try:rows.append(characterize_cell(cell))
        except Exception as e:failures.append(dict(cell_id=cell['cell_id'],error=type(e).__name__+': '+str(e)))
    original={}
    for name in ['GATE.json','WITNESS_GATE.json']:
        f=a.controller_out/name
        if f.exists():original[name]=dict(sha256=hfile(f),content=read(f))
    status='PASS_OBSERVED_NATIVE_FEEDBACK_CHARACTERIZED_ORIGINAL_GATE_UNCHANGED' if not failures else 'INCOMPLETE_CHARACTERIZATION_PRESERVED'
    summary=dict(status=status,original_controller_gates=original,planned_cells=len(plan['cells']),native_completion_cells=sum(x['status']=='CHARACTERIZED_ACTUAL_COMPLETIONS' for x in rows),
        unexecuted_or_no_completion_cells=sum(x['status']=='UNEXECUTED_OR_NO_NATIVE_COMPLETIONS' for x in rows),failures=failures,cells=rows,
        interpretation='Non-whitespace surface changes are actual selected-feedback surface changes, not established semantic correction success. No original beam token matrix is reconstructed from text.')
    (a.out/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(a.out/'GATE.json').write_text(json.dumps(dict(status=status),indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='cells'},indent=2))
if __name__=='__main__':main()
