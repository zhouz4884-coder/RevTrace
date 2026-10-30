"""Checksummed durable native facts. Recovery never promotes provisional nodes."""
from __future__ import annotations
import hashlib,json,os,pathlib,struct
from feedback_contract import FeedbackCut,digest
MAGIC=b'RVN1';MAX_FRAME=16*1024*1024
class JournalIntegrityError(RuntimeError):pass
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def encoded(x):
 p=canonical(x)
 if len(p)>MAX_FRAME:raise JournalIntegrityError('frame exceeds bounded native fact size')
 return MAGIC+struct.pack('>I',len(p))+p+hashlib.sha256(p).digest()
def scan(path,repair_tail=False):
 """Stream a complete verified prefix. Only an incomplete final frame is torn."""
 path=pathlib.Path(path)
 if not path.exists():return
 previous='0'*64;seq=0;valid=0
 with path.open('rb') as f:
  while True:
   start=f.tell();header=f.read(8)
   if not header:break
   if len(header)<8:
    if repair_tail:break
    raise JournalIntegrityError('incomplete tail header')
   if header[:4]!=MAGIC:raise JournalIntegrityError('complete frame magic corruption')
   n=struct.unpack('>I',header[4:])[0]
   if n>MAX_FRAME:raise JournalIntegrityError('frame size corruption')
   payload=f.read(n);checksum=f.read(32)
   if len(payload)!=n or len(checksum)!=32:
    if repair_tail:break
    raise JournalIntegrityError('incomplete tail payload')
   if hashlib.sha256(payload).digest()!=checksum:raise JournalIntegrityError('complete frame digest corruption')
   try:obj=json.loads(payload)
   except Exception as e:raise JournalIntegrityError('complete frame JSON invalid') from e
   if canonical(obj)!=payload or obj['sequence']!=seq+1 or obj['previous']!=previous:raise JournalIntegrityError('journal ordering/encoding changed')
   seq=obj['sequence'];previous=checksum.hex();valid=f.tell()
   yield obj,dict(sequence=seq,record_sha256=previous,offset=start,end_offset=valid)
 if repair_tail and path.stat().st_size!=valid:
  with path.open('r+b') as f:f.truncate(valid);f.flush();os.fsync(f.fileno())
def verify_frame(path,receipt):
 with pathlib.Path(path).open('rb') as f:
  f.seek(receipt['offset']);raw=f.read(receipt['end_offset']-receipt['offset'])
 if len(raw)<40 or raw[:4]!=MAGIC:raise JournalIntegrityError('missing durable publication frame')
 n=struct.unpack('>I',raw[4:8])[0]
 if len(raw)!=n+40 or hashlib.sha256(raw[8:8+n]).digest()!=raw[-32:]:raise JournalIntegrityError('durable publication binding failed')
 obj=json.loads(raw[8:8+n])
 if obj['sequence']!=receipt['sequence'] or raw[-32:].hex()!=receipt['record_sha256']:raise JournalIntegrityError('wrong durable receipt')
 if 'journal_seq' in receipt and receipt['journal_seq']!=receipt['sequence']:raise JournalIntegrityError('receipt sequence alias changed')
 if 'record_sha' in receipt and receipt['record_sha']!=receipt['record_sha256']:raise JournalIntegrityError('receipt digest alias changed')
 if 'transition_id' in receipt and receipt['transition_id']!=obj['body'].get('transition_id'):raise JournalIntegrityError('receipt transition identity changed')
 return obj
class FactStore:
 def __init__(self,path,initials,metadata,repair_tail=False):
  self.path=pathlib.Path(path);self.initials={k:FeedbackCut(v) for k,v in initials.items()};self.roots=dict(self.initials)
  self.sequence=0;self.previous='0'*64;self.metadata=metadata;self.processed={k:0 for k in initials};self.last_receipt=None;self.writes_frozen=False
  existed=self.path.exists()
  for obj,receipt in scan(self.path,repair_tail=repair_tail):
   self._replay(obj);self.sequence=obj['sequence'];self.previous=receipt['record_sha256'];self.last_receipt=receipt
  if existed and self.sequence==0:raise JournalIntegrityError('existing journal has no durable header')
  self.f=self.path.open('ab' if existed else 'xb',buffering=0)
  if not existed:self._append('genesis',dict(initials=initials,metadata=metadata))
 def _replay(self,obj):
  b=obj['body']
  if obj['sequence']==1 and obj['kind']!='genesis':raise JournalIntegrityError('first durable frame must be genesis')
  if obj['kind']=='genesis':
   if obj['sequence']!=1 or b['initials']!={k:v.state for k,v in self.initials.items()} or b['metadata']!=self.metadata:raise JournalIntegrityError('changed journal contract/genesis')
  elif obj['kind']=='canonical':
   self._validate_transition(b)
   sid=b['source_id'];self.roots[sid]=FeedbackCut(b['next_state'])
   if b['record']['native_model_evaluated']:self.processed[sid]=self.roots[sid].frontier
  else:raise JournalIntegrityError('unknown durable fact kind')
 def _validate_transition(self,b):
  sid=b['source_id'];parent=FeedbackCut(b['parent_state']);end=FeedbackCut(b['next_state']);r=b['record'];job=b['job']
  if b.get('kind')!='original_full_canonical_transition' or b.get('parent_state_sha256')!=parent.sha256 or b.get('next_state_sha256')!=end.sha256:raise JournalIntegrityError('durable transition type or explicit cut digest changed')
  required={'start','end','start_state','end_state','role','candidate_handoff','token_ids','selected_correction','native_model_evaluated','model_start','model_end'}
  if not required.issubset(r) or type(r['native_model_evaluated']) is not bool or not isinstance(r['token_ids'],list) or any(type(t) is not int for t in r['token_ids']):raise JournalIntegrityError('incomplete original C/U record')
  if r['selected_correction'] is not None and not isinstance(r['selected_correction'],dict):raise JournalIntegrityError('invalid original correction object')
  if r['start']!=parent.frontier or r['end']!=end.frontier:raise JournalIntegrityError('record input boundaries changed')
  if not parent.same(self.roots[sid]) or end.frontier<=parent.frontier or end.state['contract']!=parent.state['contract']:raise JournalIntegrityError('durable actual parent/contract invalid')
  if r['start_state']!=parent.sha256 or r['end_state']!=end.sha256 or r['role']!='authority' or r['candidate_handoff'] is not False:raise JournalIntegrityError('durable record not original complete C/U')
  if job['source_id']!=sid or job['start']!=parent.state or job['end']!=end.frontier or job['dispatch_epoch']!=b['session_epoch']:raise JournalIntegrityError('durable job input/epoch changed')
  if r['model_end']<r['model_start']:raise JournalIntegrityError('invalid actual model interval')
 def _append(self,kind,body):
  if self.writes_frozen:raise JournalIntegrityError('uncertain durable writer must recover before reuse')
  obj=dict(sequence=self.sequence+1,previous=self.previous,kind=kind,body=body);raw=encoded(obj);offset=self.f.tell()
  try:
   pending=memoryview(raw)
   while pending:
    written=self.f.write(pending)
    if written is None or written<=0:raise OSError('durable frame short write made no progress')
    pending=pending[written:]
   self.f.flush();os.fsync(self.f.fileno())
  except BaseException:
   self.writes_frozen=True;raise
  receipt=dict(sequence=obj['sequence'],record_sha256=raw[-32:].hex(),offset=offset,end_offset=offset+len(raw))
  self.sequence+=1;self.previous=receipt['record_sha256'];self.last_receipt=receipt
  return receipt
 def commit(self,body):
  self._validate_transition(body)
  body=dict(body);body.setdefault('transition_id',digest(dict(source_id=body['source_id'],job_id=body['job']['job_id'],owner_epoch=body['owner_epoch'],parent=FeedbackCut(body['parent_state']).sha256,end=FeedbackCut(body['next_state']).sha256)))
  receipt=self._append('canonical',body);sid=body['source_id'];self.roots[sid]=FeedbackCut(body['next_state'])
  if body['record']['native_model_evaluated']:self.processed[sid]=self.roots[sid].frontier
  return dict(receipt,journal_seq=receipt['sequence'],record_sha=receipt['record_sha256'],transition_id=body['transition_id'],source_id=sid)
 def close(self):self.f.close()

