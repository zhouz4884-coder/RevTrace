"""Post-service actual-parent diagnostics, separately paid, never SLO credit."""
from pathlib import Path
import sys,json,traceback,subprocess,hashlib,time
from x_gpu_probe import Engine,put
from revtrace.prefix_continuation import CurrentInputExecutor
W=Path(__file__).resolve().parent;B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def main():
    import torch,soundfile as sf,numpy as np
    D=O/'x_service_v2';s=json.loads((D/'SUMMARY.json').read_text());assert s['status']=='COMPLETE' and len(s['completed'])==16
    dest=O/'x_service_oracle_v1';dest.mkdir();rows=[]
    try:
        assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
        source=json.loads((W/'SOURCE_MANIFEST.json').read_text())
        for r in source['files']:assert hashlib.sha256((W/r['path']).read_bytes()).hexdigest()==r['sha256']
        put(dest/'FREEZE.json',dict(source=source,service_raw=str(D),rule='first Authority with chunk>=2 in each cell, independent of match/quality',
            numerical_scope='same original worker default backend; model source/dtype/processor inputs; TWO native repeats and same executor under each actual given parent',
            torch_math=dict(matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,
                deterministic=torch.are_deterministic_algorithms_enabled()),performance_claim=False))
        A=Engine(1,torch.float32);manifest=json.loads((D/'manifest.json').read_text());audio={}
        for r in manifest['sessions']:
            wav,rate=sf.read(r['path'],dtype='float32');assert rate==16000 and wav.ndim==1
            assert hashlib.sha256(np.asarray(wav,dtype='<f4').tobytes()).hexdigest()==r['audio_sha256'];audio[r['source_id']]=wav
        for name in s['completed']:
            records=[json.loads(l) for l in (D/name/'attempt0/worker_records.jsonl').read_text().splitlines()]
            targets=[r for r in records if r['job']['role']=='authority' and r['job']['chunk_id']>=2];r=min(targets,key=lambda r:r['job']['enqueue_perf'])
            j=r['job'];original=r['result'];x,pre=A.prepare(j,audio[j['source_id']]);seed=j.get('prefix_seed');draft=[]
            if seed:
                body=A.tok.decode(seed['state_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
                if body.startswith(pre):
                    draft=A.tok.encode(body[len(pre):])
                    if draft and seed['complete_EOS']:draft.append(min(A.eos))
            z1,a,b=A.native(x);z2,c,d=A.native(x)
            ex=CurrentInputExecutor(A.model.thinker,x,eos=A.eos,budget=256,pad=A.tok.pad_token_id or 0)
            z3,p=ex.select(original['prefix_selection']['mode'],draft)
            row=dict(cell=name,job=j,original=original,native_Z=z1,native_repeat_Z=z2,executor_repeat_Z=z3,
                input=ex.input_identity,proof=p,phases=ex.phases,native_call_seconds=[b-a,d-c],
                native_repeat_equal=z1==z2,original_equal_native=original['token_ids']==z1,executor_repeat_equal=z3==original['token_ids'],
                full_native_render=A.render(j,pre,z1))
            assert row['full_native_render']['P']==original['state_tokens'] or not row['original_equal_native']
            rows.append(row);put(dest/(name+'.json'),row)
        put(dest/'SUMMARY.json',dict(status='PASS_ALL_ACTUAL_PARENT_CONTROLS' if all(r['native_repeat_equal'] and r['original_equal_native'] and r['executor_repeat_equal'] for r in rows) else 'NO_GO_ACTUAL_PARENT_FRESH_EQUIVALENCE',
            targets=len(rows),actual_target_calls=len(rows)*3,rows=rows,scope='post-service actual GPU diagnostics, NOT billed as service throughput or free oracle'))
    except BaseException:put(dest/'STOP.json',dict(error=traceback.format_exc(),completed=rows));raise
if __name__=='__main__':main()
