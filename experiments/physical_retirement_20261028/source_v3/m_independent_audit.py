"""Independent saved receipts + actual SQLite + future token-input recount."""
from pathlib import Path
import sys,json,hashlib,collections,sqlite3,csv,statistics
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.composed_kernel import State,step,sha
from memory_app import canonical
from m_orthogonal import answer_messages
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def read(p):return json.loads(p.read_text())
def parsed(tok,z):
    raw=tok.decode(z,skip_special_tokens=True).strip()
    if raw.startswith('```'):
        lines=raw.splitlines();assert lines[-1].strip()=='```' and len(lines)>=3
        raw='\n'.join(lines[1:-1])
    value=json.loads(raw);assert set(value)=={'destination','owner'} and all(isinstance(v,str) for v in value.values())
    return value
def main():
    from transformers import AutoTokenizer
    D=O/'m_gpu_v2';s=read(D/'SUMMARY.json');freeze=read(D/'FREEZE.json');assert s['status']=='COMPLETE' and len(s['rows'])==320
    tasks={t['id']:t for t in freeze['tasks']};tok=AutoTokenizer.from_pretrained(B/'models/Qwen2.5-1.5B-Instruct',local_files_only=True)
    out=[];mat=collections.defaultdict(list)
    for r in s['rows']:
        directory=next(D.glob('*-'+r['task']+'-'+r['condition']+'-'+r['method']+'-r'+str(r['repeat'])))
        db=sqlite3.connect('file:'+str(directory/'project.sqlite')+'?mode=ro',uri=True)
        versions=dict(db.execute('SELECT k,version FROM docs'));m=db.execute('SELECT payload,readset,receipt FROM memory').fetchone()
        inputrows=list(db.execute('SELECT seq,payload,origin FROM inputs ORDER BY seq'));db.close()
        assert sha(inputrows)==r['current_snapshot']['prefix'] and len(inputrows)==r['current_snapshot']['accepted']
        task=tasks[r['task']];expected=task['expected_new'] if r['condition'].startswith('stale') else task['expected_old']
        memory=json.loads(m[0]) if m else None;readset=json.loads(m[1]) if m else None;receipt=json.loads(m[2]) if m else None
        assert bool(m)==r['installed'];assert (memory==expected)==r['memory_correct']
        assert (m is not None and readset==versions)==r['current_result_available']
        A=r['actual_neural_consumer'];neuralinput=False
        if A:
            assert m is not None and A['physical_worker_role']=='authority' and A['purpose']=='read-only-neural-consumer-no-state-write'
            ids=tok.apply_chat_template(answer_messages(memory),tokenize=True,add_generation_prompt=True)
            assert ids==A['actual_first_input_ids']==A['request']['input_ids'];neuralinput=True
            value=parsed(tok,A['new_tokens']);assert value==A['value']
        assert bool(A and A['value']==expected)==r['task_exact_correct']
        selected=r['selected'];v=r['verification'];protected=r['method']!='occ-only'
        if selected:
            assert selected['physical_worker_role']=='authority' and selected['value']==memory
            ids=selected['request']['input_ids'];assert sha(dict(input_ids=ids,contract=selected['request']['contract']))==selected['request_identity']
            if selected.get('operation')=='full_correct_context_verification':
                assert selected['accepted'] and selected['predicted']==selected['new_tokens'];assert selected['actual_first_input_ids']==ids+selected['new_tokens']
            else:assert selected['actual_first_input_ids']==ids
            assert parsed(tok,selected['new_tokens'])==memory
            assert readset==versions
        if v:
            assert v['actual_first_input_ids']==v['request']['input_ids']+r['returned_candidate']['new_tokens']
            assert v['accepted']==(v['predicted']==r['returned_candidate']['new_tokens'])
            assert r['actual_fallback']==(not v['accepted'])
        kernel=False
        if r['method']=='revtrace-strict':
            job=receipt['job'];fact=receipt['fact']
            contract=sha(dict(A=selected['request']['contract'],P=r['proposal']['request']['contract'],adapter='orthogonal-stable-id-memory-v1',tasks=freeze['tasks']))
            k=State(contract,1,r['current_snapshot']['origin'])
            # The original stored job/result/readset and fact, not a caller's
            # pass flag, reconstruct the same admission operation in pure core.
            k,ef=step(k,'recover-fact',dict(sid=0,fact=dict(v=0,F=0,P=sha({}),Z='',textsha=hashlib.sha256(b'{}').hexdigest(),txn='')))
            item=dict(accepted=len(inputrows),offered=len(inputrows),reserved=len(inputrows),sources=versions,
                prefix=sha(inputrows),origin=r['current_snapshot']['origin'])
            k,ef=step(k,'input-synced',dict(items={0:item},recovery=True))
            k,ef=step(k,'worker-ready',dict(worker='a'));k,ef=step(k,'dispatch',dict(worker='a',jobs=[job]))
            k,ef=step(k,'row-complete',dict(id=job['id'],worker='a',identity=selected['request_identity'],P=sha(memory),Z=sha(selected['new_tokens']),textsha=hashlib.sha256(canonical(memory).encode()).hexdigest()))
            k,ef=step(k,'batch-drained',dict(worker='a'))
            k,ef=step(k,'admission-request',dict(sid=0,job=job['id'],operation='audit',fact=fact));assert ef==['fsync-canonical']
            k,ef=step(k,'canonical-synced',dict(operation='audit'));k,ef=step(k,'install',dict(sid=0,fact=fact));kernel=True
        injected=r['condition'].endswith('coherent');candidate=r['returned_candidate'];orig=r['proposal']
        assert orig['physical_worker_role']=='proposal' and candidate['physical_worker_role']=='proposal'
        if injected:assert candidate['value']==task['fault'] and candidate['substitution_only_on_low_trust_pipe']
        unauthorized=injected and m is not None and r['method']=='occ-only'
        record=dict(task=r['task'],split=r['split'],condition=r['condition'],method=r['method'],repeat=r['repeat'],
            installed=m is not None,current_memory=m is not None and readset==versions,explicit_unfulfilled=m is None,
            memory_correct=memory==expected,task_correct=bool(A and A['value']==expected),
            low_trust_injected_content_installed=unauthorized,
            trusted_authority_content_error=bool(selected and selected['value']!=expected),
            future_model_actually_consumed_stored_memory=neuralinput,
            full_verify_accepted=bool(v and v['accepted']),fallback=bool(r['actual_fallback']),kernel_replay_pass=kernel,
            wall_seconds=r['wall_seconds'],both_GPU_joules=r['measured_both_GPU_joules'])
        if protected:assert not unauthorized and record['current_memory'] and not record['explicit_unfulfilled']
        out.append(record);mat[r['split'],r['condition'],r['method']].append(record)
    groups=[]
    for keys,rs in mat.items():
        groups.append(dict(split=keys[0],condition=keys[1],method=keys[2],n=len(rs),
            unique_tasks=len({r['task'] for r in rs}),
            counts={k:sum(r[k] for r in rs) for k in ['installed','current_memory','explicit_unfulfilled','memory_correct','task_correct',
                'low_trust_injected_content_installed','trusted_authority_content_error','future_model_actually_consumed_stored_memory','full_verify_accepted','fallback','kernel_replay_pass']},
            median_wall_seconds=statistics.median(r['wall_seconds'] for r in rs),mean_GPU_joules=statistics.mean(r['both_GPU_joules'] for r in rs)))
    calls=read(D/'CALLS.json');audit=dict(status='PASS_INDEPENDENT_SQLITE_RECEIPT_AND_ACTUAL_FUTURE_INPUT_AUDIT',episodes=320,development=64,validation=256,
        groups=groups,rows=out,worker_result_messages=len(calls),actual_GPU_model_operations=sum('actual_gpu_seconds' in r for r in calls),
        CPU_only_token_encode_messages=sum('actual_gpu_seconds' not in r for r in calls),
        limitations='raw actual_calls counts result messages including CPU token encoding; true GPU operations separated here.8 validation tasks,2 timing repeats, constructed source changes and injected returns, not natural incidence or independent320tasks. Full Standard can match RevTrace.')
    (O/'M_INDEPENDENT_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
    with (O/'M_EPISODES.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print(json.dumps({k:v for k,v in audit.items() if k not in ['rows','groups']}))
if __name__=='__main__':main()
