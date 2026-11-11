"""Surviving actual Consumer: durable facts and provisional whole views stay distinct."""
from __future__ import annotations
import hashlib,time
from feedback_contract import FeedbackCut,BranchStep,Reconciler
from native_service import Journal
from resilience_storage import canonical,verify_frame,JournalIntegrityError
class ConsumerIntegrityError(RuntimeError):pass
class SurvivorConsumer:
 def __init__(self,initials,path,rejections,fact_path):
  self.states={sid:Reconciler(FeedbackCut(s),True) for sid,s in initials.items()};self.processed={sid:0 for sid in initials}
  self.log=Journal(path,True);self.rejects=Journal(rejections,True);self.fact_path=fact_path;self.owner_epoch=-1;self.pub_highwater=0;self.pub_digest=None
  self.durable_highwater=1;self.last_durable_sha=None;self.applied=0;self.rejected=0
 def begin_owner(self,epoch):
  if epoch!=self.owner_epoch+1:raise ConsumerIntegrityError('owner epoch not monotonic')
  self.owner_epoch=epoch;self.pub_highwater=0;self.pub_digest=None
 def snapshot(self,sid):
  r=self.states[sid];v=r.visible();v['certified_frontier']=self.processed[sid]
  if not v['text']:v['visible_frontier']=0
  return v
 def protocol_sizes(self):
  return dict(owner_namespaces=1,publication_highwater_entries=1,durable_highwater_entries=1,view_dependency_nodes=sum(len(r.steps) for r in self.states.values()),applied_total=self.applied,rejected_total=self.rejected)
 def _reject(self,reason,event,source):
  before={sid:self.snapshot(sid) for sid in self.states};self.rejected+=1
  self.rejects.write(dict(kind='consumer_local_reject',reason=reason,observed=time.perf_counter(),owner_epoch=self.owner_epoch,source_epoch=source,publication_id=event.get('publication_id'),state_unchanged=True,state_sha256=hashlib.sha256(canonical(before)).hexdigest()))
  return dict(applied=False,reason=reason)
 def _fact(self,receipt,replay,expected_state=None,expected_source_id=None):
  obj=verify_frame(self.fact_path,receipt)
  if obj['kind']!='canonical':raise ConsumerIntegrityError('publication is not a durable original C/U fact')
  b=obj['body'];sid=b['source_id']
  if expected_source_id is not None and sid!=expected_source_id:raise ConsumerIntegrityError('publication changed durable source identity')
  r=self.states[sid];end=FeedbackCut(b['next_state']);parent=FeedbackCut(b['parent_state']);record=b['record']
  if expected_state is not None and b['next_state']!=expected_state:raise ConsumerIntegrityError('published state changed durable fact')
  if receipt['sequence']<self.durable_highwater:return None
  if receipt['sequence']==self.durable_highwater:
   if self.last_durable_sha!=receipt['record_sha256']:raise ConsumerIntegrityError('same durable sequence has changed contents')
   return None
  if receipt['sequence']!=self.durable_highwater+1:raise ConsumerIntegrityError('durable fact delivery has a gap')
  if not replay and b['owner_epoch']!=self.owner_epoch:raise ConsumerIntegrityError('old fact needs explicit recovery replay authority')
  if not parent.same(r.canonical) or record['start_state']!=parent.sha256 or record['end_state']!=end.sha256 or record['role']!='authority':raise ConsumerIntegrityError('actual Consumer original transition binding failed')
  r.install(end)
  if record['native_model_evaluated']:self.processed[sid]=end.frontier
  self.durable_highwater=receipt['sequence'];self.last_durable_sha=receipt['record_sha256']
  return sid,b
 def replay_fact(self,receipt):
  result=self._fact(receipt,True)
  if result is None:return dict(applied=False,reason='already_applied_durable_fact')
  sid,b=result;return self._observe('canonical',sid,dict(recovery_replay=True,transition_id=b['transition_id'],journal_sequence=receipt['sequence'],original_fact_owner_epoch=b['owner_epoch']))
 def apply(self,event,bound_owner_epoch):
  if bound_owner_epoch<self.owner_epoch:return self._reject('retired_owner_namespace',event,bound_owner_epoch)
  if bound_owner_epoch!=self.owner_epoch:raise ConsumerIntegrityError('unregistered physical Owner publication')
  seq=event['publication_id'];fp=hashlib.sha256(canonical(event)).hexdigest()
  if seq<self.pub_highwater:return self._reject('covered_publication_sequence',event,bound_owner_epoch)
  if seq==self.pub_highwater:
   if fp!=self.pub_digest:raise ConsumerIntegrityError('same publication identity has contradictory contents')
   return self._reject('exact_duplicate_publication',event,bound_owner_epoch)
  if seq!=self.pub_highwater+1:raise ConsumerIntegrityError('FIFO Owner publication sequence has a gap')
  sid=event['source_id'];r=self.states[sid]
  if event['kind']=='canonical':
   result=self._fact(event['durable_receipt'],False,event['state'],sid)
   if result is None:
    self.pub_highwater=seq;self.pub_digest=fp;return self._reject('already_applied_durable_fact',event,bound_owner_epoch)
   _,body=result
   extra=dict(transition_id=body['transition_id'],journal_sequence=event['durable_receipt']['sequence'],recovery_replay=False)
  elif event['kind']=='private':
   if r.canonical.sha256!=event['canonical_sha']:
    self.pub_highwater=seq;self.pub_digest=fp;return self._reject('stale_private_root',event,bound_owner_epoch)
   previous=r.canonical;steps=[]
   for s in event['steps']:
    start=FeedbackCut(s['start']);end=FeedbackCut(s['end'])
    if not start.same(previous) or end.frontier<=start.frontier:raise ConsumerIntegrityError('invalid actual whole-view dependency path')
    steps.append(BranchStep(s['job_id'],start.sha256,start,end));previous=end
   if previous.frontier>=r.tail.frontier:r.steps=steps
   extra=dict(recovery_replay=False)
  else:raise ConsumerIntegrityError('unknown privileged publication kind')
  self.pub_highwater=seq;self.pub_digest=fp
  return self._observe(event['kind'],sid,dict(publication_id=seq,**extra))
 def _observe(self,kind,sid,extra):
  row=dict(kind=kind,source_id=sid,observed=time.perf_counter(),owner_epoch=self.owner_epoch,**self.snapshot(sid),**extra)
  self.log.write(row);self.applied+=1
  return dict(applied=True,row=row,visible_job_ids=[s.job_id for r in self.states.values() for s in r.steps])
 def close(self):self.log.close();self.rejects.close()

