"""CPU-validated immutable transport lifecycle; admission stays with old predicates."""
from dataclasses import asdict,dataclass
import hashlib,json,math

def _wire(value):
    if isinstance(value,float) and not math.isfinite(value):return {'__revtrace_float__':'nan' if math.isnan(value) else 'inf' if value>0 else '-inf'}
    if isinstance(value,dict):return {k:_wire(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_wire(v) for v in value]
    return value
def _unwire(value):
    if isinstance(value,dict) and set(value)=={'__revtrace_float__'}:return float(value['__revtrace_float__'])
    if isinstance(value,dict):return {k:_unwire(v) for k,v in value.items()}
    if isinstance(value,list):return [_unwire(v) for v in value]
    return value
def digest(value):return hashlib.sha256(json.dumps(_wire(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

@dataclass(frozen=True)
class RowBinding:
    worker:str
    worker_incarnation:str
    batch_id:str
    job_id:str
    session_id:int
    role:str
    parent:int
    contract_epoch:int
    contract_digest:str
    runtime_digest:str
    audio_start_sample:int
    audio_end_sample:int
    interval_audio_sha256:str
    input_identity:str

@dataclass(frozen=True)
class RowComplete:
    binding:RowBinding
    payload_json:str
    payload_digest:str
    terminal_perf:float
    rendered_perf:float
    emitted_perf:float

    @classmethod
    def seal(cls,binding,payload,*,terminal,rendered,emitted):
        encoded=json.dumps(_wire(payload),sort_keys=True,separators=(',',':'),allow_nan=False)
        return cls(binding,encoded,digest(payload),terminal,rendered,emitted)

    def decode(self):
        encoded=json.loads(self.payload_json)
        if digest(encoded)!=self.payload_digest:raise ValueError('mutated row payload')
        row=_unwire(encoded)
        if row.get('row_terminal_kind')=='cancelled' or row.get('row_cancelled') is True:
            raise ValueError('cancelled prefix is not a complete result')
        if not all(math.isfinite(x) for x in [self.terminal_perf,self.rendered_perf,self.emitted_perf]):raise ValueError('nonfinite row clocks')
        if not self.terminal_perf<=self.rendered_perf<=self.emitted_perf:raise ValueError('noncausal row clocks')
        for k in ['started_perf','completed_perf','model_started_perf','model_completed_perf']:
            if row.get(k) is not None and not math.isfinite(row[k]):raise ValueError('nonfinite result clocks')
        if row.get('started_perf') is not None and row['started_perf']>self.terminal_perf:raise ValueError('terminal precedes execution')
        if row.get('completed_perf') is not None and row['completed_perf']>self.emitted_perf:raise ValueError('result completed after emission')
        b=self.binding
        if row.get('job_id')!=b.job_id or row.get('runtime_digest')!=b.runtime_digest:raise ValueError('wrong result identity')
        return row

@dataclass(frozen=True)
class CancelRequest:
    """An owner request, not a row terminal or proof of released GPU work."""
    binding:RowBinding
    request_id:str
    reason:str
    requested_perf:float

    def validate(self):
        if not isinstance(self.binding,RowBinding) or self.binding.role!='proposal':
            raise ValueError('only private proposal rows may be cancelled')
        if not isinstance(self.request_id,str) or not self.request_id:
            raise ValueError('cancellation request identity required')
        if not isinstance(self.reason,str) or not self.reason:
            raise ValueError('cancellation reason required')
        if not math.isfinite(self.requested_perf):raise ValueError('nonfinite cancellation request clock')
        return self

@dataclass(frozen=True)
class RowCancelled:
    """A decode-safe-point terminal with counts only; no usable partial output."""
    binding:RowBinding
    request_id:str
    reason:str
    requested_perf:float
    acknowledged_perf:float
    emitted_perf:float
    decoded_tokens:int
    terminal_digest:str

    def _body(self):
        return {'kind':'row-cancelled-v1','binding':asdict(self.binding),
          'request_id':self.request_id,'reason':self.reason,
          'requested_perf':self.requested_perf,'acknowledged_perf':self.acknowledged_perf,
          'emitted_perf':self.emitted_perf,'decoded_tokens':self.decoded_tokens}

    @classmethod
    def seal(cls,request,*,acknowledged,emitted,decoded_tokens):
        request.validate()
        result=cls(request.binding,request.request_id,request.reason,request.requested_perf,
          acknowledged,emitted,decoded_tokens,'')
        result=cls(**{**asdict(result),'binding':result.binding,'terminal_digest':digest(result._body())})
        result.decode()
        return result

    def decode(self):
        CancelRequest(self.binding,self.request_id,self.reason,self.requested_perf).validate()
        if not all(math.isfinite(x) for x in [self.acknowledged_perf,self.emitted_perf]):
            raise ValueError('nonfinite cancellation terminal clock')
        if not self.requested_perf<=self.acknowledged_perf<=self.emitted_perf:
            raise ValueError('noncausal cancellation clocks')
        if type(self.decoded_tokens) is not int or self.decoded_tokens<0:
            raise ValueError('invalid cancelled decode count')
        if digest(self._body())!=self.terminal_digest:raise ValueError('mutated cancellation terminal')
        return {'job_id':self.binding.job_id,'runtime_digest':self.binding.runtime_digest,
          'row_terminal_kind':'cancelled','request_id':self.request_id,'reason':self.reason,
          'requested_perf':self.requested_perf,'acknowledged_perf':self.acknowledged_perf,
          'emitted_perf':self.emitted_perf,'decoded_tokens':self.decoded_tokens}

@dataclass(frozen=True)
class BatchDrained:
    worker:str
    worker_incarnation:str
    batch_id:str
    row_digests:tuple
    completed_perf:float
    cancelled_digests:tuple=()

class RowInbox:
    """Only trusted worker messages enter here; this is not GPU attestation."""
    def __init__(self,worker,incarnation):
        self.worker=worker;self.incarnation=incarnation;self.active=None
        self.bindings={};self.seen={};self.completion_times={};self.batch_ids=set();self.poisoned=False
        self.terminal_kinds={};self.cancel_requests={}
    @property
    def worker_reusable(self):return self.active is None and not self.poisoned
    @property
    def completed_digests(self):return {j:d for j,d in self.seen.items() if self.terminal_kinds[j]=='complete'}
    @property
    def cancelled_digests(self):return {j:d for j,d in self.seen.items() if self.terminal_kinds[j]=='cancelled'}
    def begin(self,batch_id,bindings):
        if not self.worker_reusable or batch_id in self.batch_ids:raise ValueError('physical worker occupied or batch reused')
        if not bindings or len({b.job_id for b in bindings})!=len(bindings):raise ValueError('unique jobs required')
        for b in bindings:
            if (b.worker,b.worker_incarnation,b.batch_id)!=(self.worker,self.incarnation,batch_id):raise ValueError('cross worker/batch binding')
            if b.role not in ['proposal','authority'] or b.audio_end_sample<=b.audio_start_sample:raise ValueError('invalid role or interval')
        self.active=batch_id;self.bindings={b.job_id:b for b in bindings};self.seen={};self.completion_times={};self.batch_ids.add(batch_id)
        self.terminal_kinds={};self.cancel_requests={}
    def request_cancel(self,request):
        """Register before IPC send; completion may still win the race."""
        request.validate();b=request.binding
        if self.poisoned or self.active!=b.batch_id or self.bindings.get(b.job_id)!=b:
            raise ValueError('unexpected or stale cancellation binding')
        prior=self.cancel_requests.get(request.request_id)
        if prior is not None:
            if prior!=request:raise ValueError('conflicting cancellation request identity')
            return 'duplicate-request'
        if b.job_id in self.seen:return 'already-terminal'
        self.cancel_requests[request.request_id]=request
        return 'new-request'
    def receive(self,message):
        try:
            if not isinstance(message,(RowComplete,RowCancelled)):raise ValueError('unknown row terminal')
            b=message.binding
            if self.active!=b.batch_id or self.bindings.get(b.job_id)!=b:raise ValueError('unexpected or stale row binding')
            row=message.decode()
            cancelled=isinstance(message,RowCancelled)
            terminal_kind='cancelled' if cancelled else 'complete'
            receipt_digest=message.terminal_digest if cancelled else message.payload_digest
            if cancelled:
                request=self.cancel_requests.get(message.request_id)
                if request!=CancelRequest(b,message.request_id,message.reason,message.requested_perf):
                    raise ValueError('cancellation terminal lacks matching owner request')
            prior=self.seen.get(b.job_id)
            if prior:
                if self.terminal_kinds[b.job_id]!=terminal_kind or prior!=receipt_digest:
                    raise ValueError('conflicting row terminal')
                return 'duplicate',None
            self.seen[b.job_id]=receipt_digest
            self.terminal_kinds[b.job_id]=terminal_kind
            self.completion_times[b.job_id]=message.emitted_perf
            return ('new-cancelled' if cancelled else 'new-complete'),row
        except BaseException:
            self.poisoned=True;raise
    def drain(self,message):
        try:
            if (message.worker,message.worker_incarnation,message.batch_id)!=(self.worker,self.incarnation,self.active):raise ValueError('wrong drain identity')
            if set(self.seen)!=set(self.bindings):raise ValueError('missing terminal rows')
            if dict(message.row_digests)!=self.completed_digests or len(message.row_digests)!=len(self.completed_digests):raise ValueError('wrong or repeated complete manifest')
            if dict(message.cancelled_digests)!=self.cancelled_digests or len(message.cancelled_digests)!=len(self.cancelled_digests):raise ValueError('wrong or repeated cancelled manifest')
            if not math.isfinite(message.completed_perf) or message.completed_perf<max(self.completion_times.values()):raise ValueError('drain precedes complete rows')
            self.active=None;self.bindings={};self.seen={};self.completion_times={}
            self.terminal_kinds={};self.cancel_requests={}
        except BaseException:
            self.poisoned=True;raise

def owner_action(binding,*,current_parent,contract_epoch,contract_digest,runtime_digest,provisional_compatible=False):
    """A decision obligation, not a replacement for Trusted Render/A/B/C/D/WAL."""
    if (binding.contract_epoch,binding.contract_digest,binding.runtime_digest)!=(contract_epoch,contract_digest,runtime_digest):
        return 'reject-contract'
    if binding.role=='authority':return 'validate-admission-and-WAL' if binding.parent==current_parent else 'reject-stale-authority'
    return 'validate-provisional-only' if binding.parent==current_parent or provisional_compatible else 'reject-incompatible-private'
