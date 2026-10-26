"""Saved common-upstream/actual downstream diagnosis; no new GPU inference."""
from pathlib import Path
import json,hashlib,collections
W=Path(__file__).resolve().parent;E=W.parent/'evidence_retirement_20261026'
def eq(a,b):return all(a.get(k,'').casefold()==v.casefold() for k,v in b.items())
def main():
    spec=json.loads((E/'MEMORY_TASKS_v4.json').read_text());tasks={t['id']:t for t in spec['tasks']}
    summary=json.loads((E/'MEMORY_DEVELOPMENT_v3_SUMMARY.json').read_text());calls=json.loads((E/'MEMORY_DEVELOPMENT_v3_CALLS.json').read_text())
    groups=collections.defaultdict(list);out=[];ai=0
    for ri,saved in enumerate(summary['rows']):
        r=dict(saved,answer=calls['responder'][ri],old_selection=calls['authority'][ai]);ai+=1+saved['actual_fallback_generations']
        task=tasks[r['task_id']];expected=task['expected_old'] if r['condition']=='clean_same_versions' else task['expected_new']
        m=r['stored_memory']['value'];answer=r['answer']['value'];extract=eq(m,expected);faithful=eq(answer,m);correct=eq(answer,expected)
        group=hashlib.sha256(json.dumps(r['answer']['request']['input_ids']).encode()).hexdigest()
        groups[group].append(dict(episode=r['episode'],answer=answer,answer_Z=r['answer']['new_tokens']))
        out.append(dict(episode=r['episode'],task=r['task_id'],method=r['method'],condition=r['condition'],
            actual_memory=m,actual_answer=answer,expected=expected,memory_current_fact_correct=extract,
            downstream_faithful_to_installed_memory=faithful,task_correct=correct,
            attribution=('both_correct' if extract and correct else 'downstream_error_given_correct_memory' if extract else
                         'wrong_memory_answer_accidentally_correct' if correct else 'upstream_wrong_memory_and_task_error'),
            answer_input_group=group,old_generation=r['old_selection']['value'],old_installed=r['old_result_installed'],
            old_readset=r['actual_old_input_snapshot']['readset'],installed_readset=r['stored_memory']['readset']))
    upstream=collections.defaultdict(list)
    assert ai==len(calls['authority']) and len(summary['rows'])==len(calls['responder'])
    ai=0
    for r in summary['rows']:
        raw=calls['authority'][ai];ai+=1+r['actual_fallback_generations'];key=hashlib.sha256(json.dumps(raw['request']['input_ids']).encode()).hexdigest()
        upstream[key].append(dict(episode=r['episode'],value=raw['value'],Z=raw['new_tokens']))
    result=dict(status='COMPLETE_CPU_SAVED_UPSTREAM_ATTRIBUTION',episodes=len(out),rows=out,
        shared_actual_answer_input_groups=[dict(identity=k,count=len(v),identical_complete_Z=len({json.dumps(x['answer_Z']) for x in v})==1,rows=v) for k,v in groups.items()],
        shared_actual_upstream_inputs=[dict(identity=k,count=len(v),identical_complete_Z=len({json.dumps(x['Z']) for x in v})==1,rows=v) for k,v in upstream.items()],
        counts=dict(collections.Counter(r['attribution'] for r in out)),
        limitations='No new answer inference. This saved-input diagnosis cannot estimate old/current truthful-control answer rates; FP32 ideal-memory control is separately reported, not merged with old FP16 consumer.')
    (W/'M_OLD24_ATTRIBUTION.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(counts=result['counts'],shared_answer_groups=len(groups),shared_upstream_groups=len(upstream))))
if __name__=='__main__':main()
