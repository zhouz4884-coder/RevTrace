"""Same-input FP32/BF16/FP16 diagnostics; no admission or application writes.

Three-token generations measure a prefix only and cannot be presented as a
complete selected result or as native task success.
"""
from pathlib import Path
import argparse,gc,hashlib,importlib.metadata,json,os,subprocess,sys,time,traceback
from actual_provider import ActualModel,load_asset_manifest
from native_power import PowerSampler


def put(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    p.add_argument('--model-manifest',type=Path,required=True);p.add_argument('--native-reference',type=Path,required=True);a=p.parse_args()
    B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');assert a.out.resolve().is_relative_to(B/'results/revtrace/freeze_boundary_20261027') and not a.out.exists()
    source=json.loads(a.source_manifest.read_text())
    for r in source['files']:assert sha(a.source_root/r['path'])==r['sha256']
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    a.out.mkdir(parents=True);config=json.loads(a.config.read_text())['provider'];config['model_manifest']=str(a.model_manifest)
    config['verified_asset_sha256']=load_asset_manifest(a.model_manifest,config['model_path']);config['max_new_tokens']=3
    refs=[json.loads((a.native_reference/'operator_self_check'/f'{task}.json').read_text()) for task in ['ops-dev-0','resource-dev-0']]
    put(a.out/'FREEZE.json',dict(experiment_id='REVTRACE-NATIVE-SAME-INPUT-NUMERICS-20261028',source_commit=source['code_commit'],source_manifest_sha256=sha(a.source_manifest),model_manifest_sha256=sha(a.model_manifest),config=config,dtypes=['float32','bfloat16','float16'],repeats=2,requests=[r['request'] for r in refs],expected_first_forward_calls=12,expected_three_token_generations=12,scope='paid numerical operators on two prior development requests; no complete-sequence/task/serving credit',raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');os.environ['HF_HUB_OFFLINE']='1';rows=[];power=PowerSampler(a.out/'power.jsonl')
    try:
        import torch,numpy as np
        for dtype in ['float32','bfloat16','float16']:
            started=time.perf_counter();model=ActualModel(config,'numerical-diagnostic',0,dtype)
            put(a.out/(dtype+'_LOAD.json'),dict(seconds=time.perf_counter()-started,contract=model.contract))
            for qi,ref in enumerate(refs):
                ids=ref['request']['input_ids'];assert model.input_ids(ref['request']['messages'])==ids
                for repeat in range(2):
                    x=torch.tensor([ids],device='cuda:0',dtype=torch.long);model.observed=None;torch.cuda.synchronize()
                    start=time.perf_counter()
                    with torch.inference_mode():out=model.model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False,return_dict=True)
                    torch.cuda.synchronize();end=time.perf_counter();last=out.logits[0,-1,:];finite=torch.isfinite(last)
                    assert model.observed==[ids]
                    numerical=dict(logits_total=last.numel(),finite_count=int(finite.sum()),nan_count=int(torch.isnan(last).sum()),positive_inf_count=int(torch.isposinf(last).sum()),negative_inf_count=int(torch.isneginf(last).sum()))
                    array=last.float().detach().cpu().numpy();path=a.out/f'{dtype}-q{qi}-r{repeat}-last_logits.npy';np.save(path,array,allow_pickle=False)
                    record=dict(dtype=dtype,request=qi,repeat=repeat,actual_input_ids=ids,forward_seconds=end-start,forward_both_GPU_energy=power.finish_interval(start,end),last_logits_file=path.name,last_logits_sha256=sha(path),numerics=numerical,top1_if_finite=int(last.argmax()) if bool(finite.all()) else None)
                    del out,last,finite,array,x
                    generated=model.generate(ids,'three-token-prefix-not-complete-admission')
                    record['three_token_generation']=generated;record['historical_prefix_equal']=generated['tokens']==ref['first']['tokens'][:len(generated['tokens'])]
                    rows.append(record);put(a.out/f'{dtype}-q{qi}-r{repeat}.json',record)
            model.hook.remove();del model;gc.collect();torch.cuda.empty_cache()
        put(a.out/'SUMMARY.json',dict(status='COMPLETE_SAME_INPUT_NUMERICAL_DIAGNOSTIC',rows=rows,scope='nonfinite counts distinguish numerical selection failure from task interpretation; three-token output is not a complete answer'))
        put(a.out/'GATE.json',dict(gate='DIAGNOSTIC_RECORDED',rows=len(rows),source_commit=source['code_commit'],application_writes=0))
    except BaseException:
        put(a.out/'STOP.json',dict(completed=rows,error=traceback.format_exc()));raise
    finally:power.close()


if __name__=='__main__':main()
