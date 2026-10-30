"""Unfrozen draft: release returned diagnostic generation before generator yield.

The raw original insert/infer/export sequence is copied from frozen9492.
No model/input/C/U/closed-cut semantics are changed. CUDA storage inventory
returns scalar metadata only, never tensor references that would defeat del.
"""
import hashlib,json,time

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')

def semantic_row(row):
 result=row['original_full_result']
 return dict(source_id=row['source_id'],end=row['end'],complete_start=row['original_full_start_cut'],complete_end=row['original_full_cut'],selected_original_C=result['selected_correction'],returned_IDs=result['token_ids'])

def compare_rows(old_rows,new_rows):
 """Pure full-semantic comparison; permits controls repeated at one input."""
 bykey={}
 for index,row in enumerate(new_rows):bykey.setdefault((row['source_id'],row['end']),[]).append((index,row))
 matches=[];missing=[];failures=[]
 for old_index,old in enumerate(old_rows):
  key=(old['source_id'],old['end']);candidates=bykey.get(key,[])
  if not candidates:missing.append(dict(old_index=old_index,source_id=key[0],end=key[1]));continue
  for new_index,new in candidates:
   a=semantic_row(old);b=semantic_row(new);different=[k for k in a if canonical(a[k])!=canonical(b[k])]
   record=dict(old_index=old_index,new_index=new_index,source_id=key[0],end=key[1],all_equal=not different,different_fields=different,semantic_sha256=hashlib.sha256(canonical(a)).hexdigest())
   matches.append(record)
   if different:failures.append(record)
 oldkeys=list(dict.fromkeys((r['source_id'],r['end']) for r in old_rows));newkeys=list(dict.fromkeys((r['source_id'],r['end']) for r in new_rows))
 return dict(all_old_rows_matched=not missing,all_common_semantics_equal=bool(matches) and not failures,old_rows=len(old_rows),new_rows=len(new_rows),compared_pairs=len(matches),old_keys_are_contiguous_new_prefix=oldkeys==newkeys[:len(oldkeys)],missing=missing,first_mismatches=failures[:8],comparisons=matches,scope='Entire start/end cut including every contract/source marker, selected C and returned IDs compared via strict canonical bytes. Timing/diagnostic metadata outside those objects is not semantic output. Repeated same-input controls are not new acoustic units.')

def storage_inventory(value,*,cuda_only=True):
 import torch
 seen=set();storages={};tensor_objects=0
 def visit(x):
  nonlocal tensor_objects
  identity=id(x)
  if identity in seen:return
  seen.add(identity)
  if torch.is_tensor(x):
   if cuda_only and x.device.type!='cuda':return
   tensor_objects+=1;storage=x.untyped_storage();key=(str(x.device),int(storage.data_ptr()),int(storage.nbytes()))
   item=storages.setdefault(key,dict(device=str(x.device),storage_bytes=int(storage.nbytes()),tensor_views=0,representative_dtype=str(x.dtype),representative_shape=list(x.shape)))
   item['tensor_views']+=1
  elif isinstance(x,dict):
   for item in x.values():visit(item)
  elif isinstance(x,(tuple,list,set)):
   for item in x:visit(item)
  elif type(x).__module__.endswith('generation_progress') and type(x).__name__ in ('Logits','Tokens','BeamTokens'):visit(x.tokens)
 visit(value)
 return storages,tensor_objects

def generation_storage_report(generation,engine,semantic_result,*,cuda_only=True):
 """Exclusive relative to explicit live engine/model and retained result roots."""
 g,count=storage_inventory(generation,cuda_only=cuda_only);excluded={}
 roots=[semantic_result]
 for name in ('segments','tokens','initial_tokens','kv_cache','dec_attns'):
  if hasattr(engine,name):roots.append(getattr(engine,name))
 if hasattr(engine,'inference'):roots.append(getattr(engine.inference,'kv_cache',{}))
 for root in roots:
  values,_=storage_inventory(root,cuda_only=cuda_only);excluded.update(values)
 for name in ('model','_speechlm_model'):
  module=getattr(engine,name,None)
  if module is not None and hasattr(module,'parameters'):
   for tensor in module.parameters():
    values,_=storage_inventory(tensor,cuda_only=cuda_only);excluded.update(values)
   if hasattr(module,'buffers'):
    for tensor in module.buffers():
     values,_=storage_inventory(tensor,cuda_only=cuda_only);excluded.update(values)
 only=set(g)-set(excluded);shared=set(g)&set(excluded)
 return dict(g_tensor_objects=count,g_unique_storages=len(g),g_unique_storage_bytes=sum(v['storage_bytes'] for v in g.values()),g_exclusive_storage_bytes=sum(g[k]['storage_bytes'] for k in only),g_shared_with_engine_or_semantic_result_storage_bytes=sum(g[k]['storage_bytes'] for k in shared),exclusive_storages=[g[k] for k in sorted(only)],cuda_only=cuda_only,scope='Distinct reachable tensor storages in returned g, excluding enumerated live engine/model/retained semantic roots. Not allocator workspace, reserved memory or a universal ownership proof.')

def cuda_memory_stats():
 import torch
 if not torch.cuda.is_available():return dict(allocated=None,reserved=None,scope='CUDA unavailable; no GPU measurement')
 return dict(allocated=torch.cuda.memory_allocated(),reserved=torch.cuda.memory_reserved())

def continuous_transitions_release_g(model,source,audio,*,cut_export,to_tensor,sync,observer=None,stop_at=None,memory_stats=cuda_memory_stats,storage_reporter=generation_storage_report):
 """Exact original raw calls; diagnostics are released after semantic extraction."""
 engine=model.engine;contract=model.initial_for(source['audio_sha256']).state['contract'];previous=0;text=''
 ends=list(range(8000,source['frames'],8000))+[source['frames']]
 for index,end in enumerate(ends):
  if stop_at is not None and end>stop_at:break
  start=cut_export(engine,frontier=previous,transcript=text,contract=contract)
  if observer:observer.bind(source_id=source['source_id'],job_id=f'continuous_{index:06d}',start_frontier=previous,end_frontier=end)
  engine.insert_audio(to_tensor(audio[previous:end]));sync();begun=time.perf_counter();wall=time.time()
  ids,g=engine.infer(is_last=end==source['frames'],start_time=wall,corrector_model=model.corrector_model,corrector_processor=model.corrector_processor,corrector_type='speechlm')
  sync();finished=time.perf_counter();appended=engine.tokenizer.decode(ids);text+=appended
  closed=cut_export(engine,frontier=end,transcript=text,contract=contract)
  result=dict(token_ids=list(ids),selected_correction=g.get('error_corrector'),appended_text=appended,native_model_evaluated='starting_tokens' in g)
  # Inventory contains only integers/strings/shapes, not a tensor or g alias.
  storage=storage_reporter(g,engine,result);before=memory_stats()
  del g
  sync();after=memory_stats()
  release=dict(storage=storage,before=before,after=after,allocated_drop_bytes=before['allocated']-after['allocated'] if before['allocated'] is not None and after['allocated'] is not None else None,empty_cache_called=False,original_semantic_result_preserved=True)
  yield dict(source_id=source['source_id'],end=end,original_full_start_cut=start.state,original_full_cut=closed.state,original_full_result=result,continuous_original_no_between_step_restore=True,reference_only=True,original_model_start=begun,original_model_end=finished,diagnostic_generation_release=release)
  previous=end
