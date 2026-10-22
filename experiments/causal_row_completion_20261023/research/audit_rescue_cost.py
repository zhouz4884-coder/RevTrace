"""Independent raw-repeat/provenance/cost audit, no generation or state writes."""
from pathlib import Path
import csv,hashlib,json,sys

def main():
    B=Path(sys.argv[1]);P=Path(__file__).resolve().parent;O=B/'results/revtrace/row_completion_20261023';D=O/'rescue_cost_gpu_v1';A=O/'rescue_cost_independent_v1'
    assert not A.exists();A.mkdir();S=P/'source_row_sdk_v2';sys.path[:0]=[str(S/'src'),str(S/'scripts')]
    from revtrace.dgft import digest_tokens
    from revtrace.row_lifecycle import digest as receipt_digest
    from revtrace.certified_display import TrustedQwenRender,validate_bound_text
    from revtrace.sequence_verifier import token_stop_certificate
    from transformers import AutoProcessor,GenerationConfig
    from qwen_asr import parse_asr_output
    def read(p):return json.loads(p.read_text())
    report=read(D/'SUMMARY.json');assert report['actual_generation_calls']==12 and not (D/'STOP.json').exists()
    recipe_path=O/'rescue_feasibility_v1/COST_RECIPES_FROZEN.json';recipes=read(recipe_path)['recipes'];run=read(D/'RUN.json')
    assert hashlib.sha256(recipe_path.read_bytes()).hexdigest()==run['recipe_sha256']
    model=B/'models/Qwen3-ASR-1.7B';proc=AutoProcessor.from_pretrained(model,local_files_only=True)
    eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id;eos=[eos] if isinstance(eos,int) else eos
    render=TrustedQwenRender(proc.tokenizer,parse_asr_output,eos,256);table=[];index=[]
    for recipe in recipes:
        raw=[];costs=[]
        for rep in range(2):
            p=D/f"recipe{recipe['recipe_id']}-r{rep}.json";x=read(p);raw.append(x);j,z=x['job'],x['result']
            assert j['role']=='proposal' and not j['Canonical_admission_or_publication_permitted']
            assert j['base_canonical_parent_contract_digest']==recipe['parent_contract_digest'] and j['contract_digest']!=recipe['parent_contract_digest']
            assert j['prompt_tokens']==recipe['parent_P'] and j['parent_prompt_digest']==digest_tokens(recipe['parent_P'])
            assert j['audio_start_sample']==recipe['parent_frontier'] and j['audio_end_sample']==recipe['target_frontier']
            assert z['execution_context_audit']['executed_prompt_tokens']==recipe['parent_P'] and not z['execution_context_audit']['fault_override']
            assert z['model_input_audit']['dtype']=='float32' and z['model_input_audit']['batch_rows']==1 and z['model_input_audit']['max_new_tokens']==256
            assert token_stop_certificate(z['token_ids'],z['token_ids'],eos_token_ids=eos,max_new_tokens=256)[0]
            assert validate_bound_text(render,j,z)==x['owner_Render_binding']
            body={k:v for k,v in z.items() if k!='_row_receipt'};assert receipt_digest(body)==z['_row_receipt']['payload_sha256']
            assert z['_row_receipt']['binding']==j['_delivery']['binding']
            ac=[e for e in x['telemetry'] if e['kind']=='batch-accounting'];assert len(ac)==1
            assert ac[0]['batch_drained_perf']<=j['enqueue_perf']+x['complete_paid_operator_s']
            assert len(ac[0]['phases'])==1 and ac[0]['phases'][0]['phase']=='independent-generate'
            assert ac[0]['selected_output_digests'][0]['Z_sha256']==digest_tokens(z['token_ids'])
            assert x['row_owner_available_s']<=x['complete_paid_operator_s'] and x['no_Canonical_install_or_publication']
            costs.append(x['complete_paid_operator_s'])
            index.append({'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        for key in ['token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']:
            assert raw[0]['result'][key]==raw[1]['result'][key]
        assert raw[0]['result']['model_input_audit']['batch_tensors']==raw[1]['result']['model_input_audit']['batch_tensors']
        summary=next(r for r in report['recipes'] if r['recipe_id']==recipe['recipe_id']);assert costs==summary['complete_cost_s']
        table.append({'recipe_id':recipe['recipe_id'],'cell':recipe['cell'],'source_id':recipe['source_id'],
          'available_window_s':recipe['available_window_s'],'repeat0_full_cost_s':costs[0],'repeat1_full_cost_s':costs[1],
          'both_repeats_fit_isolated':max(costs)<=recipe['available_window_s'],
          'remaining_after_worst_cost_s':recipe['available_window_s']-max(costs),'even_best_cost_too_large':min(costs)>recipe['available_window_s'],
          'same_input_new_neural_generations_equal':True,'no_Canonical_permission_or_publication':True})
    with (A/'COST_VS_LEGAL_WINDOW.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    (A/'RAW_OPERATOR_HASHES.json').write_text(json.dumps({'files':index,'full_operator_inputs_outputs_retained':True},indent=2)+'\n')
    f2=[r for r in table if '-F2-' in r['cell']];fits=[r for r in table if r['both_repeats_fit_isolated']]
    out={'status':'PASS_INDEPENDENT_FRESH_PRIVATE_COST_AND_WINDOW_AUDIT','actual_generation_calls':12,'distinct_input_recipes':6,
      'distinct_audio_sources':len({r['source_id'] for r in recipes}),'both_repeats_fit_isolated':len(fits),
      'even_best_measured_cost_too_large':sum(r['even_best_cost_too_large'] for r in table),
      'F2_recipes_tested':len(f2),'F2_both_fit':sum(r['both_repeats_fit_isolated'] for r in f2),
      'only_fitting_worst_case_remaining_s':[r['remaining_after_worst_cost_s'] for r in fits],
      'no_deployed_Rescue_goodput_or_contract_extension_tested':True,'not_an_impossibility_theorem_for_all_future_designs':True,
      'decision':'NO_GO_INTEGRATED_RESCUE_NO_STRONG_TARGET_REGIME_OPPORTUNITY',
      'reason':'5/6 selected favourable recipes exceed their slot even at best observed cost;all3 tested F2 recipes fail;the lone clean fit has only milliseconds headroom and no repeated target-regime system advantage',
      'new_model_calls_by_this_audit':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (A/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
