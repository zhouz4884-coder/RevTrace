"""Logical completions do not release a physical GPU lease."""
import queue,time,uuid,json
from pathlib import Path
from dataclasses import asdict
from tc_live_worker import GPUExecutor
from revtrace.row_lifecycle import RowBinding,RowInbox,digest

class RowGPUExecutor(GPUExecutor):
    row_delivery=True
    def __init__(self,name,config):
        if config.get('result_delay_seconds',0):raise ValueError('sparse artificial result hold is outside the row-interface experiment')
        self.incarnation=uuid.uuid4().hex;self.counter=0;self.batch_drained=False
        self.inbox=RowInbox(name,self.incarnation)
        self.crash_trace_path=config.get('receipt_trace_path')
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
            if kind=='row-complete':
                state,row=self.inbox.receive(item['message'])
                if state=='new-complete':
                    if '_row_receipt' in row:raise ValueError('reserved receipt metadata in worker body')
                    message=item['message']
                    row['_row_receipt']={'payload_sha256':message.payload_digest,'binding':asdict(message.binding),
                      'terminal_perf':message.terminal_perf,'rendered_perf':message.rendered_perf,'emitted_perf':message.emitted_perf}
                    rows.append(row)
                continue
            if kind=='batch-drained':
                self.inbox.drain(item['message']);self.batch_drained=True;self.execution_phase='idle'
                self._telemetry.append({'kind':'batch-accounting',**item['physical_accounting']})
                return rows
            raise RuntimeError('unexpected physical worker event '+kind)
