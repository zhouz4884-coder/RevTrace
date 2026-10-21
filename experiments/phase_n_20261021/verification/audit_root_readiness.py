"""Audit candidate preparation only; no claims of online verification efficacy."""
import argparse,hashlib,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);a=p.parse_args();allrows=[];comparisons=[]
    assert json.loads((a.root/'SUMMARY.json').read_text())['status']=='COMPLETE'
    for repeat in range(3):
        cell=a.root/f'root-shadow-r{repeat}';baseline=a.baseline/f'coarse-decoupled-obs1-r{repeat}'
        events=[json.loads(l) for l in (cell/'events.jsonl').read_text().splitlines()]
        native=[json.loads(l) for l in (cell/'worker_records.jsonl').read_text().splitlines()]
        roots=[json.loads(l) for l in (cell/'root_records.jsonl').read_text().splitlines()]
        root_by_target={(r['job']['session_id'],r['job']['audio_end_sample']):r for r in roots}
        enq={e['job_id']:e for e in events if e['kind']=='enqueue'}
        total=aligned=timely=exact_timely=0
        for record in native:
            j,r=record['job'],record['result']
            if j['role']!='authority':continue
            total+=1;root=root_by_target.get((j['session_id'],j['audio_end_sample']))
            row={'repeat':repeat,'session_id':j['session_id'],'source_id':j['source_id'],'end':j['audio_end_sample'],
                'root_present':root is not None,'aligned':False,'ready_at_logical_eligibility':False,'ready_at_enqueue':False,'ready_at_gpu_model_start':False,
                'root_tokens_equal':False,'root_projection_equal':False}
            if root:
                q,y=root['job'],root['result'];x=y['model_input_audit'];z=r['model_input_audit']
                align=q['parent']==j['parent'] and q['prompt_tokens']==j['prompt_tokens'] and q['chunk_id']==j['chunk_id'] and x['unpadded_input_ids']==z['unpadded_input_ids'] and x['waveform_sha256']==z['waveform_sha256']
                row.update(aligned=align,ready_at_logical_eligibility=y['received_perf']<=enq[j['job_id']]['eligible_perf'],
                    ready_at_enqueue=y['received_perf']<=j['enqueue_perf'],ready_at_gpu_model_start=y['received_perf']<=r['model_started_perf'],
                    root_tokens_equal=y['token_ids']==r['token_ids'],root_projection_equal=y['state_tokens']==r['state_tokens'])
                aligned+=align;timely+=row['ready_at_enqueue'];exact_timely+=row['ready_at_enqueue'] and row['root_tokens_equal'] and row['root_projection_equal']
            allrows.append(row)
        commits=[e for e in events if e['kind']=='commit'];assert all(e['job_id'].startswith('authority-') for e in commits)
        alignment_complete=aligned==len(roots)
        baseevents=[json.loads(l) for l in (baseline/'events.jsonl').read_text().splitlines()]
        fields=['session_id','parent','version','audio_start_sample','audio_end_sample','segment_id','segment_tokens','next_prompt_tokens']
        key=lambda e:(e['session_id'],e['version'])
        whole_history_equal=[{k:e[k] for k in fields} for e in sorted(commits,key=key)]==[
            {k:e[k] for k in fields} for e in sorted([e for e in baseevents if e['kind']=='commit'],key=key)]
        result=json.loads((cell/'result.json').read_text());base=json.loads((baseline/'result.json').read_text())
        terminal_equal=[r['state']['prompt_tokens'] for r in result['final_states']]==[r['state']['prompt_tokens'] for r in base['final_states']]
        comparisons.append({'repeat':repeat,'opportunities':total,'prepared':len(roots),'aligned':aligned,'timely_at_enqueue':timely,
            'exact_and_timely':exact_timely,'xrt_over_baseline':result['audio_seconds_per_wall_second']/base['audio_seconds_per_wall_second'],
            'commit_event_p99_over_baseline':result['commit_p99_seconds']/base['commit_p99_seconds'],
            'gpu_energy_over_baseline':result['energy_joules_per_audio_second']/base['energy_joules_per_audio_second'],
            'actual_root_candidate_admissions':0,'no_new_gpu_worker':True})
        comparisons[-1].update(actual_input_alignment_complete=alignment_complete,
            whole_canonical_history_matches_baseline=whole_history_equal,terminal_matches_baseline=terminal_equal)
    passed=all(r['actual_input_alignment_complete'] and r['whole_canonical_history_matches_baseline'] and r['terminal_matches_baseline'] for r in comparisons)
    value={'decision':'PASS_C3_PREPARATION_ONLY_AUDIT' if passed else 'NO_GO_C3_COUNTERFACTUAL_NEEDS_TRIAGE','rows':allrows,'comparisons':comparisons,
        'scope':'actual extra root generation shares existing proposer FIFO; candidates never displayed/admitted/verified online; not V2 or natural failure rate'}
    (a.root/'ROOT_READINESS_AUDIT.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
