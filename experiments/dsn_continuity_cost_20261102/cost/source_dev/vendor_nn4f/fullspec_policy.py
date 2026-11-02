"""Two protected full replicas, speculative inputs, actual-parent-only commits.

This is an assembly control of the same input-validity principle. Full results
and their early identity projections are distinct nodes. Unknown parents are
never classified as known wrong, and an identity prediction need not equal C.
"""
from feedback_contract import FeedbackCut,BranchStep
from stage_policy import StageCoordinator


class FullSpecCoordinator(StageCoordinator):
 def __init__(self,**kwargs):
  if kwargs.get('producer_worker') is not None:raise ValueError('fullspec uses protected full Authority replicas only')
  super().__init__(**kwargs)
  self.completed_full={};self.discarded_full=[];self.abandoned_full=[];self.promotions=[]
  self._seen_jobs=set();self._issued_proofs={}
  self._canonical_witnesses={sid:{0:{r.canonical.frontier:r.canonical}} for sid,r in self.owners.items()}

 def _dependencies(self,sid,start):
  r=self.owners[sid];cuts=[r.canonical]
  if start.same(r.canonical):return tuple(cuts)
  previous=r.canonical
  for step in r.steps:
   if not step.start.same(previous):raise ValueError('noncontiguous conditional branch')
   cuts.append(step.end);previous=step.end
   if start.same(previous):return tuple(cuts)
  raise ValueError('fullspec start is not on the current legal conditional chain')

 def _reason(self,job):
  sid=job['source_id'];epoch=self.epochs[sid];canon=self.canonical(sid)
  common=dict(job_id=job['job_id'],source_id=sid,dispatch_epoch=job['dispatch_epoch'])
  if job['dispatch_epoch']!=epoch:
   return dict(common,kind='session_epoch_changed',witness_epoch=epoch)
  # Complete current input equality is sufficient, independently of old birth.
  if job['start'].same(canon):return None
  witnesses=self._canonical_witnesses[sid][epoch]
  # An earlier ancestor mismatch loses the tracked chain's support, but a
  # future complete input may still converge. Only a witness at this job's
  # actual start frontier proves that complete input cannot be current.
  actual=witnesses.get(job['start'].frontier)
  if actual is not None and not actual.same(job['start']):
   return dict(common,kind='actual_canonical_disagrees_with_complete_start',
    witness_frontier=job['start'].frontier,expected_cut_sha=job['start'].sha256,actual_cut_sha=actual.sha256)
  if job['end']<=canon.frontier:
   return dict(common,kind='covered_by_actual_canonical',witness_frontier=canon.frontier,actual_cut_sha=canon.sha256)
  return None

 def dependency_support_losses(self):
  """Diagnostic chain losses, deliberately NOT C-entry cancellation proofs."""
  result={}
  for job_id,job in self.jobs.items():
   sid=job['source_id']
   if job['dispatch_epoch']!=self.epochs[sid]:continue
   if job['start'].same(self.canonical(sid)):continue
   for dep in job['frozen_dependencies']:
    actual=self._canonical_witnesses[sid][self.epochs[sid]].get(dep.frontier)
    if dep.frontier<job['start'].frontier and actual is not None and not actual.same(dep):
     result[job_id]=dict(kind='tracked_chain_lost_support_future_complete_input_unresolved',
      witness_frontier=dep.frontier,expected_cut_sha=dep.sha256,actual_cut_sha=actual.sha256,
      c_entry_cancellation_authorized=False)
     break
  return result

 def invalidations(self):
  """Proofs for known wrong/covered live jobs; unresolved parents stay absent."""
  result={}
  for job_id,job in self.jobs.items():
   reason=self._reason(job)
   if reason is not None:
    # Issued proof remains an immutable account of why cancellation was legal.
    if job_id not in self._issued_proofs:self._issued_proofs[job_id]=reason
    result[job_id]=dict(self._issued_proofs[job_id])
  return result

 def _refresh_active(self):
  self.active_authority.clear()
  for job in self.jobs.values():
   sid=job['source_id']
   if job['dispatch_epoch']==self.epochs[sid] and job['start'].same(self.canonical(sid)):
    if sid in self.active_authority:raise ValueError('duplicate in-flight complete current input')
    self.active_authority[sid]=job['job_id']
    if not job['started_on_canonical'] and not job.get('promoted_to_canonical',False):
     job['promoted_to_canonical']=True
     self.promotions.append(dict(job_id=job['job_id'],source_id=sid,
      birth_canonical_sha=job['birth_canonical_sha'],birth_epoch=job['dispatch_epoch'],
      actual_parent_sha=self.canonical(sid).sha256))

 def _has_work(self,sid,start,end):
  key=self.key(sid,start,end)
  for job in self.jobs.values():
   if job['source_id']==sid and job['dispatch_epoch']==self.epochs[sid] and job['key']==key and self._reason(job) is None:return True
  return any(item['job']['source_id']==sid and item['job']['dispatch_epoch']==self.epochs[sid]
             and item['job']['key']==key and self._reason(item['job']) is None for item in self.completed_full.values())

 def next_full_start(self,sid,accepted,max_ahead_frames=32000):
  """Prefer missing current-root work, otherwise an unduplicated legal tail."""
  self._refresh_active();canon=self.canonical(sid)
  for start in (canon,self.tail(sid)):
   end=min(self.frames[sid],start.frontier+8000)
   if end<=start.frontier or end>accepted:continue
   if not start.same(canon) and end>canon.frontier+max_ahead_frames:continue
   if not self._has_work(sid,start,end):return start
  return None

 def register(self,*,job_id,worker,kind,source_id,start,end,dispatched_perf,receipt=None):
  if job_id in self._seen_jobs:raise ValueError('job ID reused')
  if worker not in self.authorities or kind!='full' or receipt is not None:raise ValueError('fullspec requires an owned original full worker')
  if any(j['worker']==worker for j in self.jobs.values()):raise ValueError('worker already owns an in-flight job')
  if end!=min(self.frames[source_id],start.frontier+8000) or end<=start.frontier:raise ValueError('changed fullspec original cadence/target')
  dependencies=self._dependencies(source_id,start)
  if self._has_work(source_id,start,end):raise ValueError('duplicate full input/target job')
  canon=self.canonical(source_id)
  job=dict(job_id=job_id,worker=worker,source_id=source_id,start=start,end=end,kind='full',
   birth_canonical_sha=canon.sha256,dispatch_epoch=self.epochs[source_id],dispatched_perf=float(dispatched_perf),
   producer=False,key=self.key(source_id,start,end),receipt=None,frozen_dependencies=dependencies,
   started_on_canonical=start.same(canon),promoted_to_canonical=False)
  self.jobs[job_id]=job;self._seen_jobs.add(job_id);self._refresh_active();return job

 def admit_asr(self,channel_worker,event,*,received_perf,ready_perf=None):
  # Same physical-channel/job/epoch, real ASR input, and typed projection checks.
  return super().admit_asr(channel_worker,event,received_perf=received_perf,ready_perf=ready_perf)

 def _replace_conditional_node(self,item):
  job=item['job'];sid=job['source_id'];r=self.owners[sid];start=job['start'];end=item['cut']
  self.nodes[job['job_id']]=dict(kind='actual_original_full_conditional_closed_node',
   actual_identity_full_step_completed=False,actual_full_C_U_completed=True)
  for i,step in enumerate(r.steps):
   if step.start.same(start) and step.end.frontier==end.frontier:
    # Original C may revise its identity prediction. Retain only a suffix that
    # actually starts at the full result; do not relabel incompatible successors.
    kept=r.steps[:i]+[BranchStep(job['job_id'],start.sha256,start,end)];previous=end
    for successor in r.steps[i+1:]:
     if not successor.start.same(previous):break
     kept.append(successor);previous=successor.end
    r.steps=kept;return
  if start.same(r.tail) and end.frontier>r.canonical.frontier:
   r.append(BranchStep(job['job_id'],start.sha256,start,end))

 def _commit(self,item):
  job=item['job'];sid=job['source_id'];r=self.owners[sid]
  if job['dispatch_epoch']!=self.epochs[sid] or not job['start'].same(r.canonical):raise ValueError('unconfirmed full result cannot become Canonical')
  reconciliation=r.install(item['cut'])
  self._canonical_witnesses[sid][self.epochs[sid]][item['cut'].frontier]=item['cut']
  self._refresh_active()
  # pop_ready_commits may install several ready parents before its caller
  # publishes them. Each publication must carry the view for its own Canon,
  # rather than rereading the final owner's later Canon during that loop.
  return dict(item,kind='canonical',reconciliation=reconciliation,
              view_event_snapshot=self.view_event(sid))

 def complete(self,channel_worker,event,*,received_perf):
  job=self.bind(channel_worker,event);start=FeedbackCut(event['start']);end=FeedbackCut(event['end']);record=event['record']
  if (not start.same(job['start']) or end.frontier!=job['end'] or end.state['contract']!=start.state['contract']
      or record['start_state']!=start.sha256 or record['end_state']!=end.sha256
      or record['candidate_handoff'] is not False or record['role']!='authority'):
   raise ValueError('completed full job changed original input/output/path binding')
  if received_perf<job['dispatched_perf']:raise ValueError('full completion predates dispatch')
  item=dict(job=job,cut=end,event=event,record=record,received_perf=float(received_perf))
  reason=self._reason(job);del self.jobs[job['job_id']];self._refresh_active()
  if reason is not None:
   result=dict(item,kind='discarded',proof=reason);self.discarded_full.append(result);return result
  if start.same(self.canonical(job['source_id'])):return self._commit(item)
  self.completed_full[job['job_id']]=item;self._replace_conditional_node(item)
  return dict(item,kind='buffered_full')

 def pop_ready_commits(self):
  """Install only already-completed exact-parent results, in actual order."""
  results=[]
  while True:
   chosen=None
   for job_id,item in sorted(self.completed_full.items(),key=lambda pair:(pair[1]['received_perf'],pair[0])):
    reason=self._reason(item['job'])
    if reason is not None:
     self.discarded_full.append(dict(item,kind='discarded',proof=reason));del self.completed_full[job_id];continue
    if item['job']['start'].same(self.canonical(item['job']['source_id'])):
     chosen=job_id;break
   if chosen is None:break
   item=self.completed_full.pop(chosen);results.append(self._commit(item))
  self._refresh_active();return results

 def abandon(self,channel,jobid,proof):
  """Retire only a previously issued actual-witness proof, without a cut."""
  job=self.jobs.get(jobid)
  if job is None or job['worker']!=channel:raise ValueError('foreign abandoned worker/job')
  if self._issued_proofs.get(jobid)!=proof or proof is None:raise ValueError('no owned actual-witness invalidation proof')
  del self.jobs[jobid];self._refresh_active()
  result=dict(kind='abandoned_full',job=job,proof=proof,certified_output=False)
  self.abandoned_full.append(result);return result

 def reset_epoch(self,sid,initial):
  super().reset_epoch(sid,initial)
  self._canonical_witnesses[sid][self.epochs[sid]]={initial.frontier:initial}
  self._refresh_active()
