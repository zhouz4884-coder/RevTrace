"""Actual F2 dose and potential co-batch layout exposure, not a causal oracle."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,sys
import numpy as np,soundfile as sf,torch
from transformers import AutoProcessor
from qwen_asr import Qwen3ASRModel

def main():
    torch.set_num_threads(2);B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'f2_exposure_v1';D.mkdir(exist_ok=False)
    assert json.loads((O/'EXTRA_ROW_CPU_SUMMARY_v1.json').read_text())['status']=='COMPLETE_EXTRA_OWNER_AND_ACTUAL_PRIVATE_DECISION_AUDITS'
    proc=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True);tok=proc.tokenizer
    obj=object.__new__(Qwen3ASRModel);obj.processor=proc;base={l:obj._build_text_prompt('',l) for l in ['English','Chinese']}
    def read(p):return json.loads(p.read_text())
    def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
    waves={}
    for mp in [B/'datasets/revtrace/phaseD_20261021/manifest.json',O/'validation_source_v1/MANIFEST.json']:
        for s in read(mp)['sessions']:
            assert s['source_id'] not in waves
            wave,sr=sf.read(s['path'],dtype='float32');assert sr==16000;waves[s['source_id']]=np.asarray(wave,dtype='<f4')
    def correct_prefix(j):
        raw=tok.decode(j['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False)
        if j['chunk_id']<2 or not raw:return ''
        ids=tok.encode(raw);k=5
        while True:
            prefix=tok.decode(ids[:max(0,len(ids)-k)])
            if '\ufffd' not in prefix or k>=len(ids):return prefix
            k+=1
    cells=[];jobs=[];layouts=[];mappings={}
    try:
        for stage in ['formal_row_v1','validation_row_v1']:
            for C in sorted((O/stage).iterdir()):
                if not C.is_dir() or not (C/'result.json').exists():continue
                cfg=read(C/'config.json');es=lines(C/'events.jsonl');rs=lines(C/'worker_records.jsonl');byid={r['job']['job_id']:r for r in rs}
                ss=read(C/'sessions.json');sourceids={s['source_id'] for s in ss};faults=[r for r in rs if 'fault_actual_prompt_tokens' in r['job']]
                issued=[e for e in es if e['kind']=='F2-injection-issued'];assert {e['job_id'] for e in issued}=={r['job']['job_id'] for r in faults}
                if cfg['online_study']['traffic']=='clean':assert not faults
                per=Counter(r['job']['source_id'] for r in faults);assert all(n==1 for n in per.values())
                mapping={r['job']['source_id']:r['job']['end_window'] for r in faults};mappings[stage,C.name]=mapping
                grouped=defaultdict(list)
                if cfg['result_delivery']=='row':
                    for a in lines(C/'worker_batch_accounting.jsonl'):grouped[a['batch_id']]=[byid[j] for j in a['job_ids']]
                else:
                    for r in rs:grouped[r['job']['role'],r['result']['started_perf'],r['result']['completed_perf']].append(r)
                effective=potential_peers=changed_width_batches=0
                for bid,batch in grouped.items():
                    if not any('fault_actual_prompt_tokens' in r['job'] for r in batch):continue
                    assert all(r['job']['role']=='proposal' for r in batch)
                    ws=[waves[r['job']['source_id']][:r['job']['audio_end_sample']] for r in batch]
                    prompts=[base[r['job']['language']]+correct_prefix(r['job']) for r in batch]
                    counter=proc(text=prompts,audio=ws,return_tensors='pt',padding=True)
                    repeat=proc(text=prompts,audio=ws,return_tensors='pt',padding=True)
                    assert all(torch.equal(counter[k],repeat[k]) for k in counter)
                    original_shape=batch[0]['result']['model_input_audit']['batch_tensors']['input_ids']['shape'];changed_width=original_shape!=list(counter['input_ids'].shape)
                    changed_width_batches+=changed_width
                    for i,r in enumerate(batch):
                        j,z=r['job'],r['result'];a=z['model_input_audit'];correct_ids=counter['input_ids'][i][counter['attention_mask'][i].bool()].tolist()
                        direct='fault_actual_prompt_tokens' in j;different=a['unpadded_input_ids']!=correct_ids
                        if direct:
                            assert z['execution_context_audit']['fault_override'] and z['execution_context_audit']['executed_prompt_tokens']==j['fault_actual_prompt_tokens']
                            effective+=different
                            jobs.append({'stage':stage,'cell':C.name,'source_id':j['source_id'],'job_id':j['job_id'],'window':j['end_window'],'chunk':j['chunk_id'],
                              'actual_feedback_tokens_changed':j['prompt_tokens']!=j['fault_actual_prompt_tokens'],'actual_vs_declared_processed_IDs_changed':different,
                              'same_physical_batch_without_override_counter_is_CPU_only':True,'not_a_generated_clean_output':True})
                        else:potential_peers+=changed_width
                    layouts.append({'stage':stage,'cell':C.name,'batch_id':str(bid),'physical_rows':len(batch),
                      'direct_context_override_rows':sum('fault_actual_prompt_tokens' in r['job'] for r in batch),
                      'actual_input_ID_shape':json.dumps(original_shape),'CPU_no_override_input_ID_shape':json.dumps(list(counter['input_ids'].shape)),
                      'potential_co_batch_shape_exposure':changed_width,'output_change_not_measured_by_CPU_reconstruction':True})
                cells.append({'stage':stage,'cell':C.name,'method':cfg['online_study']['method'],'delivery':cfg['result_delivery'],'traffic':cfg['online_study']['traffic'],
                  'sources':len(sourceids),'F2_issued_and_consumed':len(faults),'sources_without_injection':len(sourceids-set(per)),
                  'actual_processed_ID_change_rows':effective,'physical_F2_batches_with_changed_input_width':changed_width_batches,
                  'noninjected_peer_rows_potentially_exposed_to_changed_batch_shape':potential_peers,
                  'injected_source_window_mapping':json.dumps(mapping,sort_keys=True),'not_a_natural_fault_rate':True})
                print('F2_EXPOSURE',C.name,len(faults),effective,flush=True)
        assert len(cells)==150
        paired=[]
        for method in ['fine','dgft','standard','strict','score']:
            for load in ['sync16','cohort8']:
                for rep in range(3):
                    a=mappings['formal_row_v1',f'{method}-batch-{load}-F2-r{rep}'];b=mappings['formal_row_v1',f'{method}-row-{load}-F2-r{rep}']
                    paired.append({'method':method,'load':load,'repeat':rep,'same_source_target_window_injection_map':a==b,
                      'batch_direct_count':len(a),'row_direct_count':len(b),'same_rule_does_not_imply_same_Parent_or_model_output':True})
        for name,rows in [('F2_EXPOSURE_CELLS.csv',cells),('F2_ACTUAL_CONTEXT_JOBS.csv',jobs),('F2_BATCH_LAYOUT_EXPOSURE.csv',layouts),('PAIRED_F2_TARGETS.csv',paired)]:
            with (D/name).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        out={'status':'COMPLETE_ACTUAL_F2_DOSE_AND_CPU_LAYOUT_COUNTER_AUDIT','cells':150,'injected_jobs':len(jobs),
          'paired_target_maps_equal':sum(x['same_source_target_window_injection_map'] for x in paired),'paired_target_maps_total':len(paired),
          'new_model_calls':0,'co_batch_shape_exposure_not_proven_output_effect':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
    except BaseException as e:
        (D/'STOP.json').write_text(json.dumps({'error':repr(e),'completed_cells':len(cells),'new_model_calls':0,'raw_retained':True})+'\n');raise

if __name__=='__main__':main()
