"""Paid production RowGPUExecutor replay; it grants no service/admission credit."""
from pathlib import Path
import argparse,copy,hashlib,importlib.metadata,json,os,platform,subprocess,sys,time,traceback
W=Path(__file__).resolve().parent
sys.path[:0]=[str(W/'runtime/src'),str(W/'runtime/scripts')]
from revtrace.dgft import digest_tokens
from row_delivery_executor import RowGPUExecutor
from memory_gpu_pilot import Power
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(4194304),b''):h.update(part)
    return h.hexdigest()


def put(p,value):
    with Path(p).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def resolve_model_path(value,root=B/'models'):
    path=Path(value)
    if not path.is_absolute():
        if path.name!=str(path) or path.name in ('','.','..'):raise ValueError('model basename required')
        path=root/path
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('model path outside declared model store')
    return path


def prepare_jobs(case,variant,repeat,audio,now):
    assert variant in ('old','new')
    original=case['fixed_physical_batch_order']
    members=case['members_in_original_order'];assert [m['job']['job_id'] for m in members]==original
    target=case['witness']['job_id'];before=case['witness']['input_before_wait'];after=case['witness']['actual_frozen_input']
    jobs=[];mapping={}
    for m in members:
        j=copy.deepcopy(m['job']);original_id=j['job_id'];j.pop('_delivery',None)
        if original_id==target:
            selected=before if variant=='old' else after
            for field,key in [('prompt_tokens','prompt_tokens'),('chunk_id','chunk_id'),('parent','parent'),('audio_start_sample','root_frontier')]:j[field]=copy.deepcopy(selected[key])
            assert j['audio_end_sample']==selected['target_frontier']
            if variant=='old':
                parent=case['before_parent_commit'];assert parent['version']==j['parent']
                j['parent_prompt_digest']=digest_tokens(parent['next_prompt_tokens'])
                j['branch_generation']=case['old_branch_generation']
            waveform=audio[j['source_id']]
            j['interval_audio_sha256']=hashlib.sha256(waveform[j['audio_start_sample']:j['audio_end_sample']].tobytes()).hexdigest()
        assert j['role']=='proposal'
        j['job_id']=original_id+f':PAID-{variant}-r{repeat}'
        # Fresh physical timing only. Historical parents remain diagnostic data;
        # no owner, WAL, Consumer or authorization path receives these outputs.
        j['enqueue_perf']=now;j['audio_ready_perf']=now-1.
        mapping[j['job_id']]=original_id;jobs.append(j)
    return jobs,mapping


def complete_signature(row):
    return {k:row[k] for k in ('token_ids','state_tokens','text','terminated_by_eos','hit_token_limit')}


def input_signature(row):
    a=row['model_input_audit']
    return {k:a[k] for k in ('input_ids','attention_mask','batch_tensors','row_features','rollback_prefix','dtype','batch_rows','max_new_tokens','waveform_sha256')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--reference-source-manifest',type=Path,required=True)
    args=p.parse_args();D=args.out.resolve()
    assert D.is_relative_to(B/'results/revtrace/freeze_boundary_20261027') and not D.exists()
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    source=json.loads(args.source_manifest.read_text());old=json.loads(args.reference_source_manifest.read_text())
    for f in source['files']:assert sha(W/f['path'])==f['sha256'],f['path']
    previous={f['path']:f['sha256'] for f in old['files']}
    closure=['runtime/scripts/tc_live_worker.py','runtime/scripts/row_delivery_worker.py','runtime/scripts/row_delivery_executor.py','runtime/src/revtrace/dgft.py','runtime/src/revtrace/sequence_verifier.py','runtime/src/revtrace/row_lifecycle.py']
    assert all(sha(W/n)==previous[n] for n in closure),'production executor changed since reference'
    spec=json.loads(args.cases.read_text());cases=spec['cases'];assert 0<len(cases)<=4
    D.mkdir(parents=True);worker=None;power=None;completed=[]
    try:
        env=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers','numpy','soundfile']})
        put(D/'ENVIRONMENT.json',env)
        put(D/'FREEZE.json',dict(experiment_id='REVTRACE-PAID-WAIT-INPUT-OPERATOR-20261028',source_commit=source['code_commit'],source_manifest_sha256=sha(args.source_manifest),reference_source_commit=old['code_commit'],case_manifest_sha256=sha(args.cases),environment_sha256=sha(D/'ENVIRONMENT.json'),cases=[c['case_id'] for c in cases],order=[['new',0],['old',0],['old',1],['new',1]],scope='paid model operators with original complete physical batch membership; no serving/Goodput/certificate claim; old snapshot may no longer be service legal',raw_result_location=str(D),aggregate_summary_location=str(D/'SUMMARY.json'),gate_decision_location=str(D/'GATE.json')))
        import numpy as np,soundfile as sf
        first=cases[0];manifest=json.loads(Path(first['manifest_path']).read_text())
        assert sha(first['manifest_path'])==first['manifest_sha256']
        audio={}
        for s in manifest['sessions']:
            x,rate=sf.read(s['path'],dtype='float32');assert rate==16000 and x.ndim==1
            x=np.asarray(x,dtype='<f4');assert hashlib.sha256(x.tobytes()).hexdigest()==s['audio_sha256'];audio[s['source_id']]=x
        rt=copy.deepcopy(first['config']['proposal_runtime']);model=resolve_model_path(rt['model'])
        weights={p.name:sha(p) for p in model.iterdir() if p.suffix in ('.safetensors','.bin')};assert weights
        put(D/'MODEL_WEIGHTS.json',weights)
        power=Power(D/'power.jsonl');init=time.perf_counter()
        digest=first['members_in_original_order'][0]['job']['runtime_digest']
        worker=RowGPUExecutor('paid-proposal-0',dict(rt,model=str(model),gpu=0,manifest=first['manifest_path'],runtime_digest=digest,capture_model_inputs=True,lifecycle_instrumentation=True,receipt_trace_path=str(D/'worker-receipts.jsonl')))
        worker.wait_ready();put(D/'WORKER_READY.json',dict(ready=worker.ready,initialization_seconds=time.perf_counter()-init))
        observations={}
        for ci,case in enumerate(cases):
            assert case['config']['proposal_runtime']==first['config']['proposal_runtime']
            for variant,repeat in [('new',0),('old',0),('old',1),('new',1)]:
                name=f'{ci:02}-{variant}-r{repeat}';jobs,mapping=prepare_jobs(case,variant,repeat,audio,time.perf_counter())
                started=time.perf_counter();worker.submit(jobs);rows={};telemetry=[];limit=started+120.
                while not worker.batch_drained:
                    batch=worker.poll()
                    if batch:
                        for r in batch:assert r['job_id'] not in rows;rows[r['job_id']]=r
                    telemetry.extend(worker.drain_telemetry())
                    if time.perf_counter()>limit:raise TimeoutError('paid physical batch failed to drain')
                    time.sleep(.001)
                ended=time.perf_counter();assert set(rows)==set(mapping)
                by_original={mapping[k]:r for k,r in rows.items()}
                reference_matches={}
                for original in case['members_in_original_order']:
                    jid=original['job']['job_id'];r=by_original[jid]
                    reference_matches[jid]=dict(input_equal=input_signature(r)==input_signature(original['result']),complete_equal=complete_signature(r)==complete_signature(original['result']))
                result=dict(case=case['case_id'],variant=variant,repeat=repeat,jobs=jobs,rows=rows,mapping=mapping,physical_telemetry=telemetry,paid_owner_lease_seconds=ended-started,both_GPU_joules=power.joules(started,ended),original_new_input_matches=reference_matches,scope='actual paid production executor; no service admission or saved-time assertion')
                put(D/(name+'.json'),result);completed.append(name);observations[ci,variant,repeat]=result
                put(D/('PROGRESS_'+str(len(completed))+'.json'),dict(completed=completed))
        repeats=[]
        for ci,case in enumerate(cases):
            for variant in ['old','new']:
                a,b=observations[ci,variant,0],observations[ci,variant,1]
                def mapped(x,signature):return {x['mapping'][k]:signature(r) for k,r in x['rows'].items()}
                repeats.append(dict(case=case['case_id'],variant=variant,inputs_identical=mapped(a,input_signature)==mapped(b,input_signature),complete_outputs_identical=mapped(a,complete_signature)==mapped(b,complete_signature)))
        reproduction=all(all(m['input_equal'] and m['complete_equal'] for m in v['original_new_input_matches'].values()) for k,v in observations.items() if k[1]=='new')
        repeat_ok=all(r['inputs_identical'] and r['complete_outputs_identical'] for r in repeats)
        summary=dict(status='COMPLETE_PAID_OPERATOR_MEASUREMENTS',cases=len(cases),batches=len(completed),new_reference_exact_match=reproduction,same_input_repeats=repeats,costs=[dict(case=v['case'],variant=v['variant'],repeat=v['repeat'],paid_owner_lease_seconds=v['paid_owner_lease_seconds'],both_GPU_joules=v['both_GPU_joules']) for v in observations.values()],scope='conditional input and physical batch experiment; no deployable speedup or future service legality inferred')
        put(D/'SUMMARY.json',summary);put(D/'GATE.json',dict(gate='PASS_BOUNDED_REPRODUCTION' if reproduction and repeat_ok else 'REPRODUCTION_OR_NUMERIC_DIFFERENCE_RETAINED',new_reference_exact_match=reproduction,repeated_input_and_output_match=repeat_ok,source_commit=source['code_commit']))
    except BaseException:
        put(D/'STOP.json',dict(completed=completed,error=traceback.format_exc()));raise
    finally:
        if worker is not None:worker.close()
        if power is not None:power.close()


if __name__=='__main__':main()
