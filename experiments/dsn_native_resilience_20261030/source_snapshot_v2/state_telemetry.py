"""Bounded observational wrappers for original native sliding/context boundaries.

No output, input, threshold or selection is replaced. Complete FeedbackCuts,
not these count/hash diagnostics, remain the task-fidelity oracle.
"""
from collections import Counter,deque
import hashlib,time,weakref

_REGISTRIES={}

def state_counts(engine):
 context_ids=list(engine.context.as_token_ids());prefix=list(engine.context.prefix_token_ids)
 group_lengths=[int(t.shape[1]) for t in engine.tokens]
 segments=[int(s.shape[0]) for s in engine.segments]
 c=len(context_ids)-len(prefix);total=sum(group_lengths)+c
 return dict(audio_segment_samples=segments,audio_buffer_samples=sum(segments),audio_segment_count=len(segments),token_group_lengths=group_lengths,token_group_count=len(group_lengths),current_token_count=sum(group_lengths),context_token_count=c,context_prefix_token_count=len(prefix),context_text_codepoints=len(engine.context.text or ''),context_text_sha256=hashlib.sha256((engine.context.text or '').encode('utf8')).hexdigest(),context_ids_sha256=hashlib.sha256(repr(context_ids).encode('ascii')).hexdigest(),total_decoder_input_tokens=total,max_text_len=int(engine.max_text_len),max_context_tokens=int(engine.max_context_tokens),context_trim_triggered=(c>engine.max_context_tokens or total>engine.max_text_len-20),last_attend_frame=int(engine.last_attend_frame))

class NativeStateObserver:
 """Use once per actual engine; emitted records may stream directly to8TB."""
 def __init__(self,engine,emit=None,history_limit=256):
  if history_limit<1:raise ValueError('positive bounded diagnostic history required')
  self.engine=engine;self.emit=emit;self.recent=deque(maxlen=history_limit);self.counts=Counter();self.context={};self.closed=False
  if any(n in engine.__dict__ for n in ('insert_audio','trim_context')):raise ValueError('requires original class methods, not per-instance native method overrides')
  cls=type(engine);self._class=cls
  if cls not in _REGISTRIES:
   reg=dict(originals={n:getattr(cls,n) for n in ('insert_audio','trim_context')},observers=weakref.WeakKeyDictionary())
   def observer_for(actual):
    ref=reg['observers'].get(actual);return ref() if ref is not None else None
   def insert(actual,segment=None):
    observer=observer_for(actual)
    if observer is None:return reg['originals']['insert_audio'](actual,segment)
    before=state_counts(actual);added=0 if segment is None else int(segment.shape[0]);returned=reg['originals']['insert_audio'](actual,segment);after=state_counts(actual)
    removed=before['audio_buffer_samples']+added-after['audio_buffer_samples']
    observer._record('audio_insert',before,after,added_samples=added,removed_samples=removed,author_last_removed_seconds=returned,buffer_shift=removed>0)
    return returned
   def trim(actual):
    observer=observer_for(actual)
    if observer is None:return reg['originals']['trim_context'](actual)
    before=state_counts(actual);returned=reg['originals']['trim_context'](actual);after=state_counts(actual)
    observer._record('context_trim',before,after,context_changed=before['context_ids_sha256']!=after['context_ids_sha256'],context_reencoded_token_delta=after['context_token_count']-before['context_token_count'],bound_still_exceeded=after['context_trim_triggered'])
    return returned
   reg['wrappers']=dict(insert_audio=insert,trim_context=trim);_REGISTRIES[cls]=reg
   for name,method in reg['wrappers'].items():setattr(cls,name,method)
  reg=_REGISTRIES[cls]
  if reg['observers'].get(engine) is not None:raise ValueError('engine already observed')
  reg['observers'][engine]=weakref.ref(self)
 def bind(self,*,source_id,job_id,start_frontier,end_frontier):
  if self.closed:raise ValueError('observer is closed')
  self.context=dict(source_id=source_id,job_id=job_id,start_frontier=int(start_frontier),end_frontier=int(end_frontier))
 def _record(self,kind,before,after,**values):
  row=dict(boundary=kind,observed_perf=time.perf_counter(),**self.context,before=before,after=after,**values)
  self.counts[kind]+=1
  if values.get('buffer_shift'):self.counts['actual_buffer_shifts']+=1
  if values.get('context_changed'):self.counts['actual_context_trim_changes']+=1
  if values.get('bound_still_exceeded'):self.counts['context_bound_still_exceeded']+=1
  self.recent.append(row)
  if self.emit is not None:self.emit(row)
 def summary(self):return dict(counts=dict(self.counts),recent_records=len(self.recent),recent_limit=self.recent.maxlen,full_records_require_external_stream=True,scope='Observational native boundary diagnostics; complete cut/C/IDs decide fidelity.')
 def close(self):
  if self.closed:return
  reg=_REGISTRIES[self._class];reg['observers'].pop(self.engine,None)
  if not reg['observers']:
   for name,method in reg['originals'].items():setattr(self._class,name,method)
   del _REGISTRIES[self._class]
  self.closed=True
 def __enter__(self):return self
 def __exit__(self,*unused):self.close()
