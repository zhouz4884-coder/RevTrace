"""Actual installed history adapter and frozen decoder inputs; CPU only."""
from pathlib import Path
import csv,hashlib,inspect,json,sys
from transformers import WhisperProcessor
B=Path(sys.argv[1]);O=B/'results/revtrace/opportunity_20261022';R=B/'results/revtrace/phaseD_20261021/R5_whisper'
proc=WhisperProcessor.from_pretrained(B/'models/whisper-small.en',local_files_only=True);rows=[];raw=[]
for p in sorted(R.glob('*.json')):
 x=json.loads(p.read_text())
 if 'records' not in x:continue
 raw.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for kind,a,b in [('target',x['records']['native'][0],x['records']['fault'][0]),('future',x['baseline_future'],x['fault_future'])]:
  ap=proc.get_prompt_ids(a['prompt']).tolist();bp=proc.get_prompt_ids(b['prompt']).tolist()
  assert a['actual_first_decoder_ids'][:len(ap)]==ap and b['actual_first_decoder_ids'][:len(bp)]==bp
  rows.append({'source_id':x['source_id'],'phase':kind,'logical_history_text_differs':a['prompt']!=b['prompt'],'actual_decoder_prefix_equal':a['actual_first_decoder_ids']==b['actual_first_decoder_ids'],'get_prompt_ids_equal':ap==bp,'native_prompt_tokens':len(ap),'fault_prompt_tokens':len(bp),'native_decoder_tokens':len(a['actual_first_decoder_ids']),'fault_decoder_tokens':len(b['actual_first_decoder_ids']),'output_Z_equal':a['tokens']==b['tokens'],'same_audio':a['audio_sha256']==b['audio_sha256'],'dtype_equal':a['dtype']==b['dtype'],'evidence':'CPU_READ_ONLY_ACTUALLY_CONSUMED_GPU_PREFIXES'})
code=inspect.getsource(type(proc.tokenizer).get_prompt_ids)
longA='first alpha '*250+'shared suffix '*250;longB='second beta '*250+'shared suffix '*250
idsA=proc.get_prompt_ids(longA).tolist();idsB=proc.get_prompt_ids(longB).tolist()
out={'status':'COMPLETE_ACTUAL_HISTORY_AUDIT','pairs':len(rows),'logical_history_diff_pairs':sum(r['logical_history_text_differs'] for r in rows),'different_history_same_decoder_pairs':sum(r['logical_history_text_differs'] and r['actual_decoder_prefix_equal'] for r in rows),'target_input_diff_but_output_equal':sum(r['phase']=='target' and not r['actual_decoder_prefix_equal'] and r['output_Z_equal'] for r in rows),'future_input_diff_but_output_equal':sum(r['phase']=='future' and not r['actual_decoder_prefix_equal'] and r['output_Z_equal'] for r in rows),'maximum_prompt_tokens':max(max(r['native_prompt_tokens'],r['fault_prompt_tokens']) for r in rows),'get_prompt_ids_source_sha256':hashlib.sha256(code.encode()).hexdigest(),'get_prompt_ids_source':code,'synthetic_long_history_CPU_control':{'logical_different':longA!=longB,'prompt_ids_equal':idsA==idsB,'lengths':[len(idsA),len(idsB)],'tier':'CPU_SYNTHETIC_ADAPTER_NOT_REAL_BRANCH_OPPORTUNITY'},'raw_inputs':raw,'no_GPU_calls':True,'no_new_parent_generation_inferred_from_adapter_reinterpretation':True}
(O/'A_WHISPER_SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n')
with (O/'A_WHISPER_PAIRS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in out.items() if k not in ['get_prompt_ids_source','raw_inputs']}))
