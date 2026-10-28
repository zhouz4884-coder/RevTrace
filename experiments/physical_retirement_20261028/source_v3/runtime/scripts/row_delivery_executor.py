"""Logical completions do not release a physical GPU lease."""
import queue,time,uuid,json
from pathlib import Path
from dataclasses import asdict
from tc_live_worker import GPUExecutor
from revtrace.row_lifecycle import RowBinding,RowInbox,CancelRequest,digest

class RowGPUExecutor(GPUExecutor):
    row_delivery=True
    def __init__(self,name,config):
        if config.get('result_delay_seconds',0):raise ValueError('sparse artificial result hold is outside the row-interface experiment')
        self.incarnation=uuid.uuid4().hex;self.counter=0;self.batch_drained=False
        self.inbox=RowInbox(name,self.incarnation)
        self.crash_trace_path=config.get('receipt_trace_path')
        self._physical_retirement=bool(config.get('physical_retirement',False))
        self._cancellations=[];self.cancel_request_history=[]
        super().__init__(name,dict(config,row_delivery='row'))
    def submit(self,jobs):
        self.counter+=1;bid=f'{self.name}:{self.incarnation}:{self.counter}'
        bindings=[]
        for j in jobs:
            identity=digest({k:j.get(k) for k in ['session_id','source_id','role','parent','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','fault_actual_prompt_tokens']})
            b=RowBinding(self.name,self.incarnation,bid,j['job_id'],j['session_id'],j['role'],j['parent'],
              j.get('contract_epoch',1),j['contract_digest'],j['runtime_digest'],j['audio_start_sample'],
              j['audio_end_sample'],j['interval_audio_sha256'],identity)
            bindings.append(b);j['_delivery']={'worker':self.name,'incarnation':self.incarnation,'batch_id':bid,'binding':asdict(b)}
        self.inbox.begin(bid,bindings);self.batch_drained=False
        if getattr(self,'crash_trace_path',None):
            # Owner-side immutable pre-dispatch identities; the worker's own
            # receipt file remains a separate source of completed GPU facts.
            with Path(self.crash_trace_path+'.submissions').open('a',encoding='utf8') as f:
                f.write(json.dumps({'kind':'batch-submit','observed_perf':time.perf_counter(),
                    'worker':self.name,'batch_id':bid,'jobs':jobs},allow_nan=False)+'\n');f.flush()
        super().submit(jobs)
    def cancel_job(self,job_id,reason,requested_perf=None):
        """Logical request only. Retain the physical lease until BatchDrained."""
        when=time.perf_counter() if requested_perf is None else requested_perf
        audit={'kind':'cancel-request','job_id':job_id,'reason':reason,
          'requested_perf':when,'observed_perf':time.perf_counter(),
          'physical_worker_released':False}
        try:
            if not self._physical_retirement:raise ValueError('physical retirement disabled')
            binding=self.inbox.bindings.get(job_id)
            if binding is None:raise ValueError('job has no active physical binding')
            request=CancelRequest(binding,uuid.uuid4().hex,reason,when)
            status=self.inbox.request_cancel(request)
            audit.update(status=status,request_id=request.request_id,binding=asdict(binding))
            # Registering first prevents a fast worker response from outrunning
            # the immutable owner-side cancellation obligation.
            if status=='new-request':self.cancel_commands.put(request)
        except (ValueError,TypeError) as error:
            audit.update(status='rejected',rejection=str(error))
        self.cancel_request_history.append(dict(audit))
        self._telemetry.append(dict(audit))
        return audit
    def drain_cancellations(self):
        value,self._cancellations=self._cancellations,[]
        return value
    def poll(self):
        rows=[]
        while True:
            try:item=self.results.get_nowait()
            except queue.Empty:
                if not self.process.is_alive() and not self.batch_drained:raise RuntimeError('row worker died before physical drain')
                return rows or None
            kind=item['kind']
            if kind in ['batch-started','model-started','model-completed']:
                self.execution_phase={'batch-started':'preprocessing','model-started':'model-executing','model-completed':'postprocessing'}[kind]
                self._telemetry.append(item);continue
            if kind=='error':raise RuntimeError(item)
            if kind in ['cancel-rejected','cancel-completion-win']:
                self._telemetry.append(item);continue
            if kind=='row-cancelled':
                state,audit=self.inbox.receive(item['message'])
                if state=='new-cancelled':
                    message=item['message']
                    audit.update(kind='cancel-applied',binding=asdict(message.binding),
                      terminal_digest=message.terminal_digest,
                      message=asdict(message),
                      physical_worker_released=False,
                      terminal_scope='decode-terminal-not-physical-worker-release')
                    if not hasattr(self,'_cancellations'):self._cancellations=[]
                    self._cancellations.append(audit);self._telemetry.append(dict(audit))
                continue
            if kind=='row-complete':
                state,row=self.inbox.receive(item['message'])
                if state=='new-complete':
                    if '_row_receipt' in row:raise ValueError('reserved receipt metadata in worker body')
                    message=item['message']
                    row['_row_receipt']={'payload_sha256':message.payload_digest,'binding':asdict(message.binding),
                      'terminal_perf':message.terminal_perf,'rendered_perf':message.rendered_perf,'emitted_perf':message.emitted_perf}
                    rows.append(row)
                    for request in self.inbox.cancel_requests.values():
                        if request.binding==message.binding:
                            self._telemetry.append({'kind':'cancel-completion-win',
                              'status':'complete-receipt-won','job_id':message.binding.job_id,
                              'request_id':request.request_id,'observed_perf':time.perf_counter(),
                              'source':'owner-observed-complete','physical_worker_released':False})
                continue
            if kind=='batch-drained':
                self.inbox.drain(item['message']);self.batch_drained=True;self.execution_phase='idle'
                self._telemetry.append({'kind':'batch-accounting',**item['physical_accounting']})
                return rows
            raise RuntimeError('unexpected physical worker event '+kind)
