"""Minimal online candidate protection, not an availability selector or KV cache."""
import math
from .sequence_verifier import token_stop_certificate
from .live_qwen import LiveQwenScheduler,fingerprint

def complete_candidate(row,predicted,*,eos,budget):
    return token_stop_certificate(row,predicted,eos_token_ids=eos,max_new_tokens=budget)

def gate_candidate(mode,row,predicted,margins,*,eos,budget,threshold=.05):
    exact,reason=complete_candidate(row,predicted,eos=eos,budget=budget)
    # Shape/termination is independently required by common D1, not supplied by
    # a high score. Full-token correct-context scoring is intentionally strong.
    shape,shape_reason=complete_candidate(row,row,eos=eos,budget=budget)
    if mode=='strict':return exact,reason
    if mode=='score':
        good=len(margins)>=len(row) and all(math.isfinite(x) and x>=threshold for x in margins[:len(row)])
        return bool(shape and good),'score-and-D1-shape' if shape and good else shape_reason if not shape else 'low-correct-context-score'
    if mode=='unprotected':return shape,shape_reason
    raise ValueError('undeclared online selection rule')

def target_identity(job):
    return fingerprint({k:job[k] for k in ['session_id','parent','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','contract_digest','runtime_digest']})

def fallback_row_plan(shapes,batch_rows,failed,policy):
    if policy not in ['full','selective']:raise ValueError('undeclared fallback layout')
    if len(set(failed))!=len(failed) or any(type(i) is not int or not 0<=i<batch_rows for i in failed):raise ValueError('invalid failed-row set')
    if policy=='selective' and all(shape and shape[0]==batch_rows for shape in shapes.values()):return list(failed)
    return list(range(batch_rows))

def cohort_offset(sid,cohort,gap=32.,stagger=.25):
    if cohort<1:raise ValueError('positive cohort required')
    return (sid//cohort)*gap+(sid%cohort)*stagger

class OnlineAdmissionScheduler(LiveQwenScheduler):
    def __init__(self,**kwargs):
        self.online=kwargs['contract']['online_study'];self.mode=self.online['method'];self.injected=set()
        self.needs_candidate=self.mode in ['unprotected','score','strict']
        super().__init__(**kwargs)
    def _make_job(self,s,role):
        job=super()._make_job(s,role)
        if role=='proposal' and self.online['traffic']=='F2' and s.sid not in self.injected and job['end_window']>=5 and job['chunk_id']>=2:
            donors=self.online['donors'];donor=donors[s.sid%len(donors)]
            job['fault_actual_prompt_tokens']=list(donor['tokens']);job['fault_donor_id']=donor['id'];self.injected.add(s.sid)
            self._event('F2-injection-issued',job_id=job['job_id'],session_id=s.sid,donor_id=donor['id'],end_window=job['end_window'],chunk_id=job['chunk_id'],declared_prompt_tokens=job['prompt_tokens'],executed_prompt_tokens=job['fault_actual_prompt_tokens'],controlled_fault=True)
        if role=='authority' and self.needs_candidate:
            candidate=self._proposal_results.get((s.sid,s.segment_end))
            if candidate is None:raise AssertionError('online verifier cannot invent a ready candidate')
            origin=self.jobs[candidate['job_id']]
            if origin['audio_end_sample']!=job['audio_end_sample']:raise ValueError('candidate target audio mismatch')
            job.update(candidate_token_ids=list(candidate['token_ids']),candidate_state_tokens=list(candidate['state_tokens']),candidate_text=candidate['text'],candidate_origin_job_id=origin['job_id'],candidate_origin_parent=origin['parent'],candidate_origin_prompt_tokens=origin['prompt_tokens'],candidate_ready_perf=candidate['completed_perf'],online_selection_mode=self.mode)
            self._event('online-candidate-attached',job_id=job['job_id'],session_id=s.sid,candidate_job_id=origin['job_id'],candidate_completed=candidate['completed_perf'],authority_enqueue=job['enqueue_perf'],same_parent=origin['parent']==job['parent'],same_prompt=origin['prompt_tokens']==job['prompt_tokens'])
        return job
    def _ready(self,role):
        values=super()._ready(role)
        if role=='authority' and self.needs_candidate:
            return [s for s in values if (s.sid,s.segment_end) in self._proposal_results]
        return values
    def _commit_ready(self):
        if self.needs_candidate:
            for s in self.sessions.values():
                if s.done or s.auth_done or s.auth_result is None:continue
                r=s.auth_result;j=self.jobs[r['job_id']];proof=r.get('online_verification')
                if not proof or proof['mode']!=self.mode or proof['target_identity']!=target_identity(j):raise ValueError('missing/wrong online selection receipt')
                if proof['executed_prompt_tokens']!=j['prompt_tokens'] or proof['actual_audio_sha256']!=j['prefix_audio_sha256']:raise ValueError('verification did not consume current target context/audio')
                if self.mode!='unprotected':
                    if proof['dtype']!='float32' or proof['context_override_used']:raise ValueError('untrusted target execution')
                    if proof['fallback_used']:
                        if not proof['fallback_generated'] or proof['fallback_batch_seconds']<=0:raise ValueError('unpaid/absent fallback')
                        if j['job_id'] not in proof['fallback_executed_job_ids']:raise ValueError('fallback did not execute this row')
                    else:
                        ok,_=gate_candidate(self.mode,j['candidate_token_ids'],proof['predicted_token_ids'],proof['candidate_margins'],eos=proof['eos_token_ids'],budget=self.contract['authority_runtime']['max_new_tokens'],threshold=self.online['score_threshold'])
                        if not ok or r['token_ids']!=j['candidate_token_ids']:raise ValueError('invalid verified candidate installation')
        return super()._commit_ready()
