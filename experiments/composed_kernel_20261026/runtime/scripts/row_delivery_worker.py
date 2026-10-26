"""Immutable complete-row IPC; final physical accounting remains separate."""
import json,time
from dataclasses import asdict
from revtrace.certified_display import TrustedQwenRender
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained
from revtrace.row_stream import CompleteRowStream
from revtrace.dgft import digest_tokens
import hashlib
from pathlib import Path

class RowDeliveryTap:
    def __init__(self,results,processor,parse,config,eos):
        self.results=results;self.tok=processor.tokenizer;self.parse=parse;self.cfg=config
        self.eos=set(eos);self.render=TrustedQwenRender(self.tok,parse,eos,config['max_new_tokens'])
        self.rows={};self.receipts={};self.phase_start=None
    def prepare(self,jobs,*,prefixes,contexts,audits,started):
        if len(audits)!=len(jobs):raise ValueError('complete rows require actual model-input records')
        self.jobs=jobs;self.prefixes=prefixes;self.contexts=contexts;self.audits=audits
        self.started=started;self.rows={};self.receipts={};self.phase_start=None
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
    def emit(self,i,Z,*,terminal,proof=None,complete_result=None):
        if i in self.rows:raise ValueError('row emitted twice')
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
        for i,r in enumerate(final_rows):
            if i not in self.rows:self.emit(i,r['token_ids'],terminal=r['completed_perf'],proof=r.get('online_verification'),complete_result=r)
            early=self.rows[i]
            if any(early[k]!=r[k] for k in ['job_id','token_ids','state_tokens','text','terminated_by_eos','hit_token_limit']):raise ValueError('complete row differs from final physical output')
        h=self.jobs[0]['_delivery']
        # Selected content/own input and checker evidence are already immutable
        # row receipts. Do not resend each large full peer proof16 times merely
        # to bill a single physical invocation. Preserve all new physical facts.
        proof=final_rows[0].get('online_verification')
        phases=list(proof['phases']) if proof else []
        if not proof and final_rows[0].get('model_started_perf') is not None:
            phases=[{'phase':'independent-generate','started_perf':final_rows[0]['model_started_perf'],
              'completed_perf':final_rows[0]['model_completed_perf'],'physical_batch_rows':len(final_rows),
              'executed_job_ids':[r['job_id'] for r in final_rows]}]
        phases=getattr(self,'explicit_phases',phases)
        batch_proof={k:proof[k] for k in ['mode','dtype','physical_batch_rows','verify_batch_seconds',
          'fallback_batch_seconds','fallback_requested_layout','fallback_row_indices','fallback_executed_job_ids',
          'fallback_input_ids','fallback_input_row_origins','fallback_batch_rows'] if k in proof} if proof else None
        accounting={'schema':'row-cost-v1','batch_id':h['batch_id'],
          'row_receipt_digests':dict(self.receipts),
          'worker_started_perf':min(r['started_perf'] for r in final_rows),
          'batch_result_complete_perf':max(r['completed_perf'] for r in final_rows),
          'job_ids':[r['job_id'] for r in final_rows],'phases':phases,'verification_batch':batch_proof,
          'selected_output_digests':[{'job_id':r['job_id'],'Z_sha256':digest_tokens(r['token_ids']),
             'P_sha256':digest_tokens(r['state_tokens']),'text_sha256':hashlib.sha256(r['text'].encode()).hexdigest(),
             'generated_tokens':len(r['token_ids']),'hit_token_limit':r['hit_token_limit'],
             'terminated_by_eos':r['terminated_by_eos']} for r in final_rows]}
        msg=BatchDrained(h['worker'],h['incarnation'],h['batch_id'],tuple(self.receipts.items()),time.perf_counter())
        accounting['batch_drained_perf']=msg.completed_perf
        if self.cfg.get('receipt_trace_path'):
            with Path(self.cfg['receipt_trace_path']).open('a',encoding='utf8') as stream:
                stream.write(json.dumps({'kind':'batch-drained','message':asdict(msg),'physical_accounting':accounting},allow_nan=False)+'\n');stream.flush()
        self.results.put({'kind':'batch-drained','message':msg,'physical_accounting':accounting})
