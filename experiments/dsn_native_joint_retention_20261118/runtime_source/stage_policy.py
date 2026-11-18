"""Single-owner ready-only policy with physical worker-channel/job binding."""
from dataclasses import dataclass
import hashlib,time
from feedback_contract import FeedbackCut,BranchStep,Reconciler
from stage_packet import CandidatePacket,input_key

@dataclass(frozen=True)
class OwnedCandidate:
 packet:CandidatePacket
 producer_worker:str
 producer_job_id:str
 source_id:str
 birth_canonical_sha:str
 birth_epoch:int
 birth_start_sha:str
 produced_perf:float
 received_perf:float
 ready_perf:float

class StageCoordinator:
 def __init__(self,*,initials,audio,runtime_identity,source_frames,producer_worker=None,authority_workers=('full0','full1')):
  self.owners={sid:Reconciler(FeedbackCut(s),True) for sid,s in initials.items()};self.epochs={sid:0 for sid in initials};self.audio=audio;self.runtime_identity=runtime_identity;self.frames=source_frames;self.producer=producer_worker;self.authorities=set(authority_workers);self.jobs={};self.active_authority={};self.ready={};self.projections={};self.nodes={};self.consumptions=[]
 def canonical(self,sid):return self.owners[sid].canonical
 def tail(self,sid):return self.owners[sid].tail
 def key(self,sid,start,end):return input_key(start,audio=self.audio[sid],end=end,is_last=end==self.frames[sid],runtime_identity=self.runtime_identity)
 def register(self,*,job_id,worker,kind,source_id,start,end,dispatched_perf,receipt=None):
  if job_id in self.jobs:raise ValueError('job ID reused')
  r=self.owners[source_id];is_producer=worker==self.producer and self.producer is not None
  if is_producer:
   if kind!='full' or not start.same(r.tail):raise ValueError('producer lacks a current legal prediction start')
  else:
   if worker not in self.authorities or source_id in self.active_authority or not start.same(r.canonical):raise ValueError('Authority dispatch source/root/owner mismatch')
   if kind not in ('full','consume'):raise ValueError('Authority command kind')
   if kind=='consume' and (not isinstance(receipt,OwnedCandidate) or receipt.birth_epoch!=self.epochs[source_id] or receipt.packet.key_json!=self.key(source_id,start,end) or receipt.ready_perf>dispatched_perf):raise ValueError('Authority cannot consume an unmatched/unready/foreign-epoch candidate')
   self.active_authority[source_id]=job_id
  job=dict(job_id=job_id,worker=worker,source_id=source_id,start=start,end=end,kind=kind,birth_canonical_sha=r.canonical.sha256,dispatch_epoch=self.epochs[source_id],dispatched_perf=float(dispatched_perf),producer=is_producer,key=self.key(source_id,start,end),receipt=receipt)
  self.jobs[job_id]=job
  return job
 def bind(self,channel_worker,event):
  if event.get('worker')!=channel_worker:raise ValueError('message is not from its bound physical worker channel')
  job=self.jobs.get(event.get('job_id'))
  if job is None or job['worker']!=channel_worker or job['source_id']!=event.get('source_id'):raise ValueError('unsolicited/foreign worker job')
  if event.get('dispatch_epoch')!=job['dispatch_epoch']:raise ValueError('message changed its dispatched session epoch')
  return job
 def admit_asr(self,channel_worker,event,*,received_perf,ready_perf=None):
  job=self.bind(channel_worker,event);start=FeedbackCut(event['start_state'])
  if job['dispatch_epoch']!=self.epochs[job['source_id']]:raise ValueError('ASR event is from an old session epoch')
  if not start.same(job['start']) or event['start_state_sha']!=start.sha256 or event['end_frontier']!=job['end']:raise ValueError('ASR event changed its dispatched input')
  expected_role='protected_asr_stage' if job['producer'] else 'authority'
  if event['producer_role']!=expected_role:raise ValueError('worker role mismatch')
  if event['produced_perf']<job['dispatched_perf'] or received_perf<event['produced_perf']:raise ValueError('ASR receipt is not a fresh same-domain timestamp')
  projection=event['projection'];end=FeedbackCut(projection['end'])
  if projection['kind']!='typed_ASR_stage_identity_feedback_projection' or projection['learned_C_executed'] is not False or projection['original_full_infer_completed'] is not False:raise ValueError('stage projection mislabeled as full C completion')
  if end.frontier!=job['end'] or end.sha256!=projection['end_state_sha'] or end.state['contract']!=start.state['contract']:raise ValueError('projection changed feedback contract/target')
  self.projections[job['job_id']]=projection
  self.nodes[job['job_id']]=dict(kind='typed_ASR_projection',actual_identity_full_step_completed=False)
  receipt=None
  if job['producer']:
   if event['kind']!='candidate' or not isinstance(event.get('candidate_wire'),bytes):raise ValueError('protected producer did not supply a complete wire packet')
   packet=CandidatePacket.from_wire(event['candidate_wire'])
   if packet.key_json!=job['key']:raise ValueError('candidate input is not the input actually dispatched to its protected producer')
   receipt=OwnedCandidate(packet=packet,producer_worker=channel_worker,producer_job_id=job['job_id'],source_id=job['source_id'],birth_canonical_sha=job['birth_canonical_sha'],birth_epoch=job['dispatch_epoch'],birth_start_sha=start.sha256,produced_perf=event['produced_perf'],received_perf=received_perf,ready_perf=time.perf_counter() if ready_perf is None else ready_perf)
   if receipt.ready_perf<received_perf:raise ValueError('candidate became ready before complete receipt')
   self.ready[packet.key_json]=receipt
   while len(self.ready)>64:del self.ready[next(iter(self.ready))]
  elif event['kind']!='asr_early' or event.get('candidate_wire') is not None:raise ValueError('baseline early-view cannot masquerade as a cached candidate')
  r=self.owners[job['source_id']];eligible=start.same(r.tail) and end.frontier>r.canonical.frontier
  if eligible:
   r.append(BranchStep(job['job_id'],start.sha256,start,end));self.nodes[job['job_id']]=dict(kind='typed_ASR_projection',actual_identity_full_step_completed=False)
  return dict(eligible_view=eligible,receipt=receipt,projection=end,job=job)
 def take_ready(self,sid,end,dispatch_perf):
  key=self.key(sid,self.canonical(sid),end);receipt=self.ready.get(key)
  if receipt is None or receipt.birth_epoch!=self.epochs[sid] or receipt.ready_perf>dispatch_perf:return None
  del self.ready[key]
  # Revalidation preserves original birth/producer ownership; matching a new
  # Canonical input does not rename/re-sign the candidate's actual birth.
  receipt.packet.verify();return receipt
 def complete(self,channel_worker,event,*,received_perf):
  job=self.bind(channel_worker,event);start=FeedbackCut(event['start']);end=FeedbackCut(event['end']);record=event['record']
  if job['dispatch_epoch']!=self.epochs[job['source_id']]:raise ValueError('completed job belongs to an old session epoch')
  if not start.same(job['start']) or end.frontier!=job['end'] or end.state['contract']!=start.state['contract'] or record['start_state']!=start.sha256 or record['end_state']!=end.sha256:raise ValueError('completed job changed full input/output binding')
  r=self.owners[job['source_id']]
  if not job['producer']:
   if self.active_authority.get(job['source_id'])!=job['job_id'] or self.epochs[job['source_id']]!=job['dispatch_epoch'] or not start.same(r.canonical):raise ValueError('Canonical parent/epoch/root changed before C/U completed; cannot install')
   if bool(record['candidate_handoff'])!=(job['kind']=='consume'):raise ValueError('Authority reported wrong execution path')
   reconciliation=r.install(end);del self.active_authority[job['source_id']]
   if job['receipt'] is not None:self.consumptions.append(dict(authority_job=job['job_id'],producer_job=job['receipt'].producer_job_id,birth_canonical_sha=job['receipt'].birth_canonical_sha,birth_epoch=job['receipt'].birth_epoch,dispatch_epoch=job['dispatch_epoch'],birth_start_sha=job['receipt'].birth_start_sha,consume_start_sha=start.sha256,received_perf=job['receipt'].received_perf,ready_perf=job['receipt'].ready_perf,dispatch_perf=job['dispatched_perf']))
   result=dict(kind='canonical',reconciliation=reconciliation,job=job,cut=end)
  else:
   projection=self.projections.get(job['job_id'])
   if projection is not None and (projection['end']!=end.state or projection['token_ids']!=record['token_ids']):raise ValueError('stage projection differs from actual original identity full-step')
   self.nodes[job['job_id']]=dict(kind='actual_original_identity_closed_node',actual_identity_full_step_completed=True)
   if projection is None and start.same(r.tail) and end.frontier>r.canonical.frontier:r.append(BranchStep(job['job_id'],start.sha256,start,end))
   result=dict(kind='producer_completed',job=job,cut=end)
  del self.jobs[job['job_id']]
  return result
 def publish_ready_projection(self,receipt):
  if receipt.birth_epoch!=self.epochs[receipt.source_id]:return False
  sid=receipt.source_id;r=self.owners[sid];key=__import__('json').loads(receipt.packet.key_json);start=FeedbackCut(key['complete_start_cut']);p=self.projections[receipt.producer_job_id];end=FeedbackCut(p['end'])
  if start.same(r.tail) and end.frontier>r.canonical.frontier:
   r.append(BranchStep(receipt.producer_job_id,start.sha256,start,end));return True
  return False
 def reset_epoch(self,sid,initial):
  """Session lifecycle hook; pending old jobs remain incapable of installing."""
  self.epochs[sid]+=1;self.owners[sid]=Reconciler(initial,True);self.active_authority.pop(sid,None)
 def view_event(self,sid):
  r=self.owners[sid]
  return dict(kind='private',source_id=sid,canonical_sha=r.canonical.sha256,steps=[dict(job_id=s.job_id,start=s.start.state,end=s.end.state,**self.nodes.get(s.job_id,{})) for s in r.steps])
