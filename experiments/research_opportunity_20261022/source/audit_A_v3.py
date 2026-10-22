"""CPU-only opportunity count on real frozen GPU records. Never regenerate Z."""
import csv,hashlib,inspect,json,sys,time
from pathlib import Path
from collections import defaultdict,Counter
B=Path(sys.argv[1]);D=B/'results/revtrace/phaseD_20261021';O=B/'results/revtrace/opportunity_20261022';O.mkdir(exist_ok=True)
from transformers import AutoProcessor,WhisperForConditionalGeneration
import qwen_asr # registers the checkpoint-specific processor; not a model load
tok=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).tokenizer
def prefix(P,chunk):
 raw=tok.decode(P,skip_special_tokens=False,clean_up_tokenization_spaces=False)
 if chunk<2 or not raw:return ''
 ids=tok.encode(raw);k=5
 while True:
  out=tok.decode(ids[:max(0,len(ids)-k)])
  if '\ufffd' not in out or k>=len(ids):return out
  k+=1
rows=[];counts=Counter();hashes=[];depths=[];batchgroups={};examples=[]
for stage in ['R2_continuity','R2_strong_async','R2_transfer','R4_strict']:
 for c in sorted((D/stage).iterdir()):
  if not (c/'result.json').exists():continue
  es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];rs={}
  for l in (c/'worker_records.jsonl').open():
   x=json.loads(l);rs[x['job']['job_id']]=x
  hashes.append({'cell':stage+'/'+c.name,'events_sha256':hashlib.sha256((c/'events.jsonl').read_bytes()).hexdigest(),'worker_records_sha256':hashlib.sha256((c/'worker_records.jsonl').read_bytes()).hexdigest()})
  commits={(e['session_id'],e['version']):e for e in es if e['kind']=='commit'};cache={};jobs={e['job_id']:e for e in es if e['kind']=='enqueue'};dispatches=[(i,e) for i,e in enumerate(es) if e['kind']=='enqueue' and e['role']=='proposal'];completed={e['job_id']:i for i,e in enumerate(es) if e['kind']=='executor-complete'}
  for i,e in enumerate(es):
   if e['kind']=='display':cache[e['session_id'],jobs[e['job_id']]['end_window']]=rs[e['job_id']]
   if e['kind']!='private-continuity-proof':continue
   counts['all_continuity_checks']+=1
   if e['eligible']:counts['exact_P_eligible']+=1;continue
   counts['rejected_'+str(e['witness'])]+=1
   if e['witness']!='boundary-projection-mismatch':continue
   counts['exact_P_mismatch_checks']+=1
   cm=commits[e['session_id'],e['canonical_version']];sid=e['session_id'];F=cm['audio_end_sample'];window=round(F/32000);r=cache.get((sid,window))
   assert r and r['result']['state_tokens']!=cm['next_prompt_tokens']
   old=r['result']['state_tokens'];new=cm['next_prompt_tokens'];p0=prefix(old,window);p1=prefix(new,window);root_eq=p0==p1
   normalized_input_eq=tok.encode(p0)==tok.encode(p1)
   # Existing descendants must actually have executed before the new parent.
   cursor=window;P=old;children=[]
   for (s,w),node in sorted(cache.items()):
    if s!=sid or not(window<w<=e['branch_chunk']):continue
    j=node['job'];z=node['result']
    if j.get('branch_generation')!=e['branch_generation']:continue
    if j['chunk_id']!=cursor or j['prompt_tokens']!=P:break
    children.append(node);cursor=w;P=z['state_tokens']
   pending=[rs[x['job_id']] for k,x in dispatches if x['session_id']==sid and k<i<completed.get(x['job_id'],-1) and x.get('branch_generation')==e['branch_generation']]
   future=[x for k,x in dispatches if k>i and x['session_id']==sid]
   completed_reexecution=[x for x in future if any(x['audio_end_sample']==n['job']['audio_end_sample'] and x['audio_start_sample']==n['job']['audio_start_sample'] for n in children)]
   all_z_adapter_equal=True;prior_new=new
   for node in children:
    j,z=node['job'],node['result'];a,b=prefix(j['prompt_tokens'],j['chunk_id']),prefix(prior_new,j['chunk_id'])
    if a!=b:all_z_adapter_equal=False;break
    # This is deterministic re-render of recorded Z under identical prefix.
    # It is NOT generation under a changed model input.
    prior_new=tok.encode(b+tok.decode(z['token_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False))
    if prior_new!=z['state_tokens']:all_z_adapter_equal=False;break
   row={'stage':stage,'cell':c.name,'session_id':sid,'version':cm['version'],'source_id':jobs[cm['job_id']]['source_id'],'F':F,'root_window':window,'old_P_tokens':len(old),'new_P_tokens':len(new),'old_reencode_tokens':len(tok.encode(tok.decode(old,skip_special_tokens=False,clean_up_tokenization_spaces=False))),'new_reencode_tokens':len(tok.encode(tok.decode(new,skip_special_tokens=False,clean_up_tokenization_spaces=False))),'old_P_changed_by_reencode':list(old)!=tok.encode(tok.decode(old,skip_special_tokens=False,clean_up_tokenization_spaces=False)),'new_P_changed_by_reencode':list(new)!=tok.encode(tok.decode(new,skip_special_tokens=False,clean_up_tokenization_spaces=False)),'rollback_prefix_equal':root_eq,'prefix_tokenizer_normalized_equal':normalized_input_eq,'actual_existing_descendants':len(children),'actual_inflight_descendants':len(pending),'identical_prefix_rerender_chain':bool(root_eq and all_z_adapter_equal),'actual_future_same_interval_reexecutions':len(completed_reexecution),'completed_descendant_target_seconds_upper_bound':sum(n['result']['completed_perf']-n['result']['started_perf'] for n in children),'evidence':'CPU_REINTERPRETATION_OF_RECORDED_GPU_Z_NOT_NEW_PARENT_GENERATION'}
   rows.append(row)
   if root_eq and (children or pending):examples.append({'case':row,'old_root_P':old,'new_root_P':new,'first_child':children[0] if children else None,'pending':pending[:1]})
  counts['actual_serving_cells']+=1
with (O/'A_OPPORTUNITIES.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(O/'A_EXAMPLES.json').write_text(json.dumps(examples,indent=2)+'\n')
# Read actual installed decoder-history implementation, no model allocation.
from transformers.models.whisper.generation_whisper import WhisperGenerationMixin
code=inspect.getsource(WhisperGenerationMixin._prepare_decoder_input_ids)
relevant='\n'.join(l for l in code.splitlines() if any(t in l for t in ['prompt','prev','max','cut','start','decoder_input']))
(O/'WHISPER_HISTORY_IMPLEMENTATION.json').write_text(json.dumps({'library_file':inspect.getfile(WhisperGenerationMixin),'method_sha256':hashlib.sha256(code.encode()).hexdigest(),'actual_source':code,'relevant_lines':relevant,'no_GPU_executed':True},indent=2)+'\n')
out={'status':'COMPLETE_CPU_REAL_TRACE_AUDIT','counts':dict(counts),'P_mismatch_cases':len(rows),'rollback_root_prefix_equal':sum(r['rollback_prefix_equal'] for r in rows),'normalized_prefix_equivalent':sum(r['prefix_tokenizer_normalized_equal'] for r in rows),'old_P_changed_by_reencode':sum(r['old_P_changed_by_reencode'] for r in rows),'new_P_changed_by_reencode':sum(r['new_P_changed_by_reencode'] for r in rows),'root_equivalent_with_completed_descendants':sum(r['rollback_prefix_equal'] and r['actual_existing_descendants']>0 for r in rows),'root_equivalent_with_inflight_descendants':sum(r['rollback_prefix_equal'] and r['actual_inflight_descendants']>0 for r in rows),'proven_same_prefix_adapter_chains':sum(r['identical_prefix_rerender_chain'] and r['actual_existing_descendants']>0 for r in rows),'maximum_existing_descendant_depth':max(r['actual_existing_descendants'] for r in rows),'actual_future_same_interval_reexecutions_all_cases':sum(r['actual_future_same_interval_reexecutions'] for r in rows),'warning':'target-seconds upper bound sums batch-shared job service and is NOT deduplicated GPU work or saving; no root equivalence itself treated as model reexecution','raw_hashes':hashes,'new_GPU_calls':0}
(O/'A_SUMMARY_v3.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='raw_hashes'}))
