"""Immutable complete-row IPC; final physical accounting remains separate."""
import json,math,queue,time
from dataclasses import asdict
from revtrace.certified_display import TrustedQwenRender
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained,CancelRequest,RowCancelled
from revtrace.row_stream import CompleteRowStream
from revtrace.dgft import digest_tokens
import hashlib
from pathlib import Path

class DecodeRetirementCriterion:
    """Fixed-layout HF safe point; only whole-generation return frees a lease."""
    def __init__(self,tap,stream):self.tap=tap;self.stream=stream
    def __call__(self,input_ids,scores,**kwargs):
        import torch
        self.tap.poll_cancellations(self.stream)
        mask=[a or b for a,b in zip(self.stream.done,self.stream.cancelled)]
        return torch.tensor(mask,dtype=torch.bool,device=input_ids.device)


class RowDeliveryTap:
    def __init__(self,results,processor,parse,config,eos,cancel_commands=None):
        self.results=results;self.tok=processor.tokenizer;self.parse=parse;self.cfg=config
        self.eos=set(eos);self.render=TrustedQwenRender(self.tok,parse,eos,config['max_new_tokens'])
        self.rows={};self.receipts={};self.phase_start=None;self.cancel_commands=cancel_commands
        self.cancellation_enabled=bool(config.get('physical_retirement',False))
    def prepare(self,jobs,*,prefixes,contexts,audits,started):
        if len(audits)!=len(jobs):raise ValueError('complete rows require actual model-input records')
        self.jobs=jobs;self.prefixes=prefixes;self.contexts=contexts;self.audits=audits
        self.started=started;self.rows={};self.receipts={};self.phase_start=None
        self.cancelled={};self.physical_completion=None
        # A prior batch's physical phases are never reused for this batch.
        if hasattr(self,'explicit_phases'):del self.explicit_phases
        headers=[j['_delivery'] for j in jobs]
        if len({(h['worker'],h['incarnation'],h['batch_id']) for h in headers})!=1:raise ValueError('mixed physical batch identity')
        self.bindings={i:RowBinding(**h['binding']) for i,h in enumerate(headers)}
    def set_phase(self,name,started,indices):
        self.phase=name;self.phase_start=started;self.phase_indices=list(indices)
    def stream(self,indices=None,proof_factory=None):
        indices=list(range(len(self.jobs))) if indices is None else list(indices)
        def done(i,Z,terminal):
            if i in self.rows:return # A full-layout fallback may compute ignored accepted rows.
            proof=proof_factory(i,time.perf_counter()) if proof_factory else None
            self.emit(i,Z,terminal=terminal,proof=proof)
        return CompleteRowStream(indices,eos=self.eos,budget=self.cfg['max_new_tokens'],on_complete=done)
    def stopping_criterion(self,stream):return DecodeRetirementCriterion(self,stream)
    def _cancel_event(self,kind,request,status):
        body={'kind':kind,'status':status,'observed_perf':time.perf_counter(),
          'physical_worker_released':False}
        if isinstance(request,CancelRequest):body.update(request_id=request.request_id,
          job_id=request.binding.job_id,reason=request.reason,binding=asdict(request.binding))
        self.results.put(body)
    def _pending_cancellations(self):
        if self.cancel_commands is None:return
        while True:
            try:yield self.cancel_commands.get_nowait()
            except queue.Empty:return
    def poll_cancellations(self,stream):
        """Observe requests only after a decode iteration's token event."""
        if not self.cancellation_enabled:return
        by_job={b.job_id:(i,b) for i,b in self.bindings.items()}
        for request in self._pending_cancellations():
            try:
                if not isinstance(request,CancelRequest):raise ValueError('unknown-request-type')
                request.validate()
                match=by_job.get(request.binding.job_id)
                if match is None or match[1]!=request.binding:raise ValueError('stale-binding')
                index=match[0]
                if index in self.rows:
                    self._cancel_event('cancel-completion-win',request,'already-complete');continue
                if index in self.cancelled:
                    self._cancel_event('cancel-rejected',request,'already-cancelled');continue
                if index not in stream.indices:raise ValueError('not-in-active-generation')
                if request.requested_perf>time.perf_counter():raise ValueError('request-clock-in-future')
                counts=stream.cancel([index])
                if index not in counts:
                    self._cancel_event('cancel-completion-win',request,'already-complete');continue
                acknowledged=time.perf_counter()
                message=RowCancelled.seal(request,acknowledged=acknowledged,
                  emitted=time.perf_counter(),decoded_tokens=counts[index])
                self.cancelled[index]=message
                if self.cfg.get('receipt_trace_path'):
                    with Path(self.cfg['receipt_trace_path']).open('a',encoding='utf8') as output:
                        output.write(json.dumps({'kind':'row-cancelled','message':asdict(message)},allow_nan=False)+'\n');output.flush()
                self.results.put({'kind':'row-cancelled','message':message})
            except (ValueError,TypeError) as error:
                self._cancel_event('cancel-rejected',request,str(error))
    def record_physical_completion(self,*,started,completed,indices):
        """Called by worker only after generation returns and CUDA synchronizes."""
        if not all(math.isfinite(x) for x in [started,completed]) or started>completed:
            raise ValueError('invalid physical generation clocks')
        if self.cancelled and completed<max(m.emitted_perf for m in self.cancelled.values()):
            raise ValueError('physical completion precedes cancellation')
        self.physical_completion={'phase':'independent-generate','started_perf':started,
          'completed_perf':completed,'physical_batch_rows':len(indices),
          'executed_job_ids':[self.jobs[i]['job_id'] for i in indices],
          'fixed_layout_until_generation_return':True}
    def _settle_late_cancellations(self):
        if not self.cancellation_enabled:return
        for request in self._pending_cancellations():
            match=next((b for b in self.bindings.values() if isinstance(request,CancelRequest) and b==request.binding),None)
            if match is not None and match.job_id in self.receipts:
                self._cancel_event('cancel-completion-win',request,'generation-already-complete')
            else:self._cancel_event('cancel-rejected',request,'no-unfinished-row-at-physical-completion')
    def emit(self,i,Z,*,terminal,proof=None,complete_result=None):
        if i in self.rows or i in self.cancelled:raise ValueError('row emitted twice or after cancellation')
        j=self.jobs[i];render_start=time.perf_counter();P,text=self.render(j,Z);completed=time.perf_counter()
        row={'job_id':j['job_id'],'runtime_digest':self.cfg['runtime_digest'],
          'prefix_audio_sha256':self.contexts[i]['actual_audio_sha256'],'started_perf':self.started,
          'completed_perf':completed,'model_started_perf':self.phase_start,'model_completed_perf':None,
          'token_ids':list(Z),'state_tokens':list(P),'text':text,'language':j['language'],
          'generated_tokens':len(Z),'hit_token_limit':len(Z)==self.cfg['max_new_tokens'] and Z[-1] not in self.eos,
          'terminated_by_eos':Z[-1] in self.eos,'execution_context_audit':self.contexts[i],
          'model_input_audit':self.audits[i],'physical_batch_id':self.bindings[i].batch_id,
          'row_terminal_perf':terminal,'row_rendered_perf':completed,'row_render_wall_seconds':completed-render_start,
          'row_delivery_protocol':'complete-row-v1'}
        if complete_result is not None:
            row.update({k:v for k,v in complete_result.items() if k not in ['completed_perf','received_perf','text_binding']})
            row.update(completed_perf=completed,physical_batch_id=self.bindings[i].batch_id,
                       row_terminal_perf=terminal,row_rendered_perf=completed,row_delivery_protocol='complete-row-v1')
        if proof is not None:row['online_verification']=proof
        if 'fault_actual_prompt_tokens' in j:
            raw=self.prefixes[i]+self.tok.decode(list(Z),skip_special_tokens=True,clean_up_tokenization_spaces=False)
            _,actual_text=self.parse(raw,user_language=j['language'])
            row.update(F2_raw_execution_state_tokens=self.tok.encode(raw),F2_raw_execution_text=actual_text,
              F2_normalization_scope='declared-parent fields of actual wrong-context Z, not regeneration')
        message=RowComplete.seal(self.bindings[i],row,terminal=terminal,rendered=completed,emitted=time.perf_counter())
        self.rows[i]=row;self.receipts[j['job_id']]=message.payload_digest
        if self.cfg.get('receipt_trace_path'):
            with Path(self.cfg['receipt_trace_path']).open('a',encoding='utf8') as stream:
                stream.write(json.dumps({'kind':'row-complete','message':asdict(message)},allow_nan=False)+'\n');stream.flush()
        self.results.put({'kind':'row-complete','message':message})
    def finish(self,final_rows):
        if len(final_rows)!=len(self.jobs):raise ValueError('final physical row set changed')
        if self.cancelled and self.physical_completion is None:
            raise ValueError('cancel masking without synchronized physical completion')
        for i,r in enumerate(final_rows):
            if i in self.cancelled:
                if r is not None:raise ValueError('cancelled row must not carry a complete result')
                continue
            if r is None:raise ValueError('missing complete row without cancellation')
            if i not in self.rows:self.emit(i,r['token_ids'],terminal=r['completed_perf'],proof=r.get('online_verification'),complete_result=r)
            early=self.rows[i]
            if any(early[k]!=r[k] for k in ['job_id','token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']):raise ValueError('complete row differs from final physical output')
        h=self.jobs[0]['_delivery']
        # Selected content/own input and checker evidence are already immutable
        # row receipts. Do not resend each large full peer proof16 times merely
        # to bill a single physical invocation. Preserve all new physical facts.
        complete_rows=[r for r in final_rows if r is not None]
        first=complete_rows[0] if complete_rows else {}
        proof=first.get('online_verification')
        phases=list(proof['phases']) if proof else []
        if not proof and first.get('model_started_perf') is not None:
            phases=[{'phase':'independent-generate','started_perf':first['model_started_perf'],
              'completed_perf':first['model_completed_perf'],'physical_batch_rows':len(final_rows),
              'executed_job_ids':[j['job_id'] for j in self.jobs]}]
        if self.physical_completion is not None:phases=[self.physical_completion]
        phases=getattr(self,'explicit_phases',phases)
        batch_proof={k:proof[k] for k in ['mode','dtype','physical_batch_rows','verify_batch_seconds',
          'fallback_batch_seconds','fallback_requested_layout','fallback_row_indices','fallback_executed_job_ids',
          'fallback_input_ids','fallback_input_row_origins','fallback_batch_rows'] if k in proof} if proof else None
        accounting={'schema':'row-cost-v1','batch_id':h['batch_id'],
          'row_receipt_digests':dict(self.receipts),
          'worker_started_perf':min((r['started_perf'] for r in complete_rows),default=self.started),
          'batch_result_complete_perf':max((r['completed_perf'] for r in complete_rows),default=time.perf_counter()),
          'job_ids':[j['job_id'] for j in self.jobs],'phases':phases,'verification_batch':batch_proof,
          'selected_output_digests':[{'job_id':r['job_id'],'Z_sha256':digest_tokens(r['token_ids']),
             'P_sha256':digest_tokens(r['state_tokens']),'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),
             'generated_tokens':len(r['token_ids']),'hit_token_limit':r['hit_token_limit'],
             'terminated_by_eos':r['terminated_by_eos']} for r in complete_rows]}
        self._settle_late_cancellations()
        cancelled_digests={m.binding.job_id:m.terminal_digest for m in self.cancelled.values()}
        if self.cancelled:
            accounting.update(cancelled_row_receipt_digests=cancelled_digests,
              cancelled_rows=[asdict(m) for m in self.cancelled.values()],
              cancelled_row_inputs={self.jobs[i]['job_id']:{'execution_context_audit':self.contexts[i],
                  'model_input_audit':self.audits[i]} for i in self.cancelled},
              physical_retirement_scope='fixed-layout-decode-boundary-v1',
              physical_release_basis='generation-return-and-CUDA-synchronize',
              masked_row_compute_charged_until_batch_drain=True)
        msg=BatchDrained(h['worker'],h['incarnation'],h['batch_id'],tuple(self.receipts.items()),time.perf_counter(),tuple(cancelled_digests.items()))
        accounting['batch_drained_perf']=msg.completed_perf
        if self.cfg.get('receipt_trace_path'):
            with Path(self.cfg['receipt_trace_path']).open('a',encoding='utf8') as stream:
                stream.write(json.dumps({'kind':'batch-drained','message':asdict(msg),'physical_accounting':accounting},allow_nan=False)+'\n');stream.flush()
        self.results.put({'kind':'batch-drained','message':msg,'physical_accounting':accounting})
