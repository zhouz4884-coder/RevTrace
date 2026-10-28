"""Independent content-only byte/token, real DB/future-input and core audit."""
from pathlib import Path
import sys,json,sqlite3,hashlib,collections,tarfile,subprocess,csv
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/lp1_20261026';O=B/'results/revtrace/dependability_20261025/lp1_20261026'
R=P/'m_format_execution_v1';sys.path[:0]=[str(R),str(R/'runtime/src')]
from revtrace.composed_kernel import State,step,sha
from memory_app import canonical
from m_orthogonal import answer_messages,stable_tasks
from content_fault import parse_json_memory
def read(p):return json.loads(p.read_text())
def main():
    from transformers import AutoTokenizer
    D=O/'m_format_v1';s=read(D/'SUMMARY.json');assert s['status']=='COMPLETE' and len(s['rows'])==64
    tok=AutoTokenizer.from_pretrained(B/'models/Qwen2.5-1.5B-Instruct',local_files_only=True)
    old={(r['task'],r['method'],r['repeat']):r for r in read(O/'m_gpu_v2/SUMMARY.json')['rows'] if r['split']=='validation' and r['condition']=='current-coherent'}
    tasks={t['id']:t for t in stable_tasks()};out=[]
    for r in s['rows']:
        task=tasks[r['task']];a=r['proposal'];c=r['returned_candidate'];control=c['content_only_control'];z0=a['new_tokens'];z1=c['new_tokens']
        raw=a['decoded'];expected=raw.replace(json.dumps(a['value']['destination']),json.dumps(task['fault']['destination']))
        assert c['decoded']==expected and tok.decode(z1,skip_special_tokens=True)==expected
        begin,end=control['original_token_span'];new=control['replacement_tokens']
        assert z1==z0[:begin]+new+z0[end:-1]+[z0[-1]]
        assert c['value']==dict(a['value'],destination=task['fault']['destination'])==task['fault']
        assert a['physical_worker_role']==c['physical_worker_role']=='proposal'
        assert c['self_checksum']==sha(dict(tokens=z1,value=c['value']))
        prior=old[r['task'],r['method'],r['repeat']]
        assert a['request_identity']==prior['proposal']['request_identity'] and z0==prior['proposal']['new_tokens']
        E=next(D.glob('*-'+r['task']+'-'+r['method']+'-r'+str(r['repeat'])))
        db=sqlite3.connect('file:'+str(E/'project.sqlite')+'?mode=ro',uri=True)
        mem,readset,receipt=db.execute('SELECT payload,readset,receipt FROM memory').fetchone();versions=dict(db.execute('SELECT k,version FROM docs'))
        inputs=list(db.execute('SELECT seq,payload,origin FROM inputs ORDER BY seq'));db.close()
        mem,readset,receipt=json.loads(mem),json.loads(readset),json.loads(receipt);assert readset==versions and sha(inputs)==r['current_snapshot']['prefix']
        A=r['actual_neural_consumer'];ids=tok.apply_chat_template(answer_messages(mem),tokenize=True,add_generation_prompt=True)
        assert A['actual_first_input_ids']==ids==A['request']['input_ids'];assert parse_json_memory(tok.decode(A['new_tokens'],skip_special_tokens=True))==A['value']
        correct=A['value']==task['expected_old'];protected=r['method']!='occ-only';first_mismatch=None;core=False
        if protected:
            selected=r['selected'];assert selected['physical_worker_role']=='authority' and selected['value']==mem
            assert mem==task['expected_old'] and parse_json_memory(tok.decode(selected['new_tokens'],skip_special_tokens=True))==mem
            assert selected['request_identity']==prior['selected']['request_identity'] and selected['new_tokens']==prior['selected']['new_tokens']
            if r['verification']:
                v=r['verification'];assert not v['accepted'] and r['actual_fallback']
                assert v['actual_first_input_ids']==v['request']['input_ids']+z1
                first_mismatch=next(i for i,(x,y) in enumerate(zip(z1,v['predicted'])) if x!=y)
                assert begin<=first_mismatch<begin+len(new),'rejection starts outside content replacement span'
            if r['method']=='revtrace-strict':
                contract=sha(dict(A=selected['request']['contract'],P=a['request']['contract'],adapter='orthogonal-stable-id-memory-v1',tasks=stable_tasks()))
                k=State(contract,1,r['current_snapshot']['origin']);job=receipt['job'];fact=receipt['fact']
                k,_=step(k,'recover-fact',dict(sid=0,fact=dict(v=0,F=0,P=sha({}),Z='',textsha=hashlib.sha256(b'{}').hexdigest(),txn='')))
                item=dict(accepted=len(inputs),offered=len(inputs),reserved=len(inputs),prefix=sha(inputs),origin=k.owner,sources=versions)
                k,_=step(k,'input-synced',dict(items={0:item},recovery=True));k,_=step(k,'worker-ready',dict(worker='a'))
                k,_=step(k,'dispatch',dict(worker='a',jobs=[job]));k,_=step(k,'row-complete',dict(id=job['id'],worker='a',identity=selected['request_identity'],Z=sha(selected['new_tokens']),P=sha(mem),textsha=hashlib.sha256(canonical(mem).encode()).hexdigest()))
                k,_=step(k,'batch-drained',dict(worker='a'));k,_=step(k,'admission-request',dict(sid=0,job=job['id'],fact=fact,operation='audit'))
                k,_=step(k,'canonical-synced',dict(operation='audit'));k,_=step(k,'install',dict(sid=0,fact=fact));core=True
        else:assert mem==task['fault']
        out.append(dict(task=r['task'],method=r['method'],repeat=r['repeat'],content_only_byte_token_control=True,
            original_neural_Z_equal_prior=True,first_mismatch=first_mismatch,changed_token_start=begin,
            actual_memory_correct=mem==task['expected_old'],actual_task_correct=correct,actual_future_consumption=True,
            full_fallback=r['actual_fallback'],original_kernel_replay=core))
    groups=[]
    for method in sorted({r['method'] for r in out}):
        rs=[r for r in out if r['method']==method];groups.append(dict(method=method,n=len(rs),unique_tasks=len({r['task'] for r in rs}),
            memory_correct=sum(r['actual_memory_correct'] for r in rs),task_correct=sum(r['actual_task_correct'] for r in rs),
            actual_fallbacks=sum(r['full_fallback'] for r in rs),core_passes=sum(r['original_kernel_replay'] for r in rs)))
    calls=read(D/'CALLS.json');result=dict(status='PASS_INDEPENDENT_CONTENT_ONLY_FORMAT_TOKEN_AND_FUTURE_INPUT_AUDIT',episodes=64,groups=groups,rows=out,
        actual_GPU_operations=sum('actual_gpu_seconds' in r for r in calls),CPU_encode_messages=sum('actual_gpu_seconds' not in r for r in calls),
        scope='same8 validation tasks,two timing repeats,independent fresh application executions; not64 independent tasks.32 Strict rejections begin inside edited content span, not formatting.')
    (O/'M_FORMAT_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    dest=O/'format_export_v1';dest.mkdir();files=sorted([p for p in D.glob('*.json')]+[D/'power.jsonl']+list(D.glob('*/RESULT.json'))+list(D.glob('*/project.sqlite'))+[O/'M_FORMAT_AUDIT.json'])
    index=[dict(path=p.relative_to(O).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in files]
    with tarfile.open(dest/'M_FORMAT_RAW.tar.gz','w:gz') as arc:
        for p in files:arc.add(p,arcname=p.relative_to(O).as_posix())
    (dest/'INDEX.json').write_text(json.dumps(dict(files=index,archive_sha256=hashlib.sha256((dest/'M_FORMAT_RAW.tar.gz').read_bytes()).hexdigest()),indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
