"""Audit-only admission guard. Not a production supervisor or new WAL format."""
from dataclasses import asdict
import hashlib,json
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
INPUT_FIELDS=('session_id','role','source_id','language','parent','parent_prompt_digest','prompt_tokens','chunk_id','chunk_advance','end_window','audio_start_sample','audio_end_sample','contract_digest','runtime_digest','prefix_audio_sha256','interval_audio_sha256')
def semantic(job):return {k:job[k] for k in INPUT_FIELDS}
def inspect_adoption(state,expected,record,*,manifest_digest,worker_live,supervisor_id,worker_incarnation,owner_epoch):
 """Source trust is Supervisor IPC identity, not a self-asserted result hash."""
 if not worker_live:return 'worker-dead'
 if owner_epoch!=state.contract_epoch:return 'not-current-owner'
 if record.get('supervisor_id')!=supervisor_id:return 'wrong-supervisor'
 if record.get('worker_incarnation')!=worker_incarnation:return 'wrong-worker-incarnation'
 if record.get('manifest_digest')!=manifest_digest:return 'manifest-mismatch'
 if record.get('source_role')!='authority':return 'not-authority-source'
 if record.get('dispatch_epoch',owner_epoch)>=owner_epoch:return 'not-prior-epoch'
 job=record['job'];result=record.get('result')
 if digest(job)!=record.get('job_sha256'):return 'mutated-dispatch'
 if f"{job['session_id']}:{job['audio_start_sample']}:{job['audio_end_sample']}" in state.committed_segment_ids:return 'already-durable'
 if semantic(job)!=semantic(expected):return 'not-current-logical-job'
 if result is None:return 'pending'
 if digest(result)!=record.get('result_sha256'):return 'mutated-result'
 if result.get('job_id')!=job['job_id']:return 'result-job-mismatch'
 if result.get('runtime_digest')!=expected['runtime_digest']:return 'result-runtime-mismatch'
 if result.get('prefix_audio_sha256')!=expected['prefix_audio_sha256']:return 'result-audio-mismatch'
 return 'eligible-for-new-epoch-authorization'

def install_result(journal,state,job,result,text_binding):
 """Use unchanged frozen admission+WAL; the NEW epoch authorizes the old work."""
 from revtrace.dgft import CanonicalSegmentJob,build_dual_axis_certificate,commit_canonical_segment,digest_tokens
 txn=f"{state.session_id}:{job['audio_start_sample']}:{job['audio_end_sample']}"
 j=CanonicalSegmentJob(state.session_id,state.contract_epoch,state.policy_version,state.checkpoint_id,job['audio_start_sample'],job['audio_end_sample'],txn,job['parent_prompt_digest'],state.contract_digest,state.canonical_runtime_digest,job['interval_audio_sha256'])
 cert=build_dual_axis_certificate(job=j,audio=b'',display_tokens=result['token_ids'],feedback_state_tokens=result['state_tokens'],canonical_runtime_digest=result['runtime_digest'])
 install=commit_canonical_segment(state,j,certificate=cert,display_tokens=result['token_ids'],segment_tokens=result['token_ids'],next_prompt_tokens=result['state_tokens'])
 if not install.accepted:raise ValueError('original admission rejected: '+install.reason)
 event={'event':'canonical-segment-committed','session_id':state.session_id,'segment_id':txn,'parent_checkpoint_id':state.checkpoint_id,'checkpoint_id':install.state.checkpoint_id,'audio_start_sample':job['audio_start_sample'],'audio_end_sample':job['audio_end_sample'],'invalidated_speculative_versions':list(install.invalidated_speculative_versions),'certificate_consumed':True,'certificate':asdict(cert),'committed_text':result['text'],'text_binding':text_binding}
 request=digest({'kind':'canonical-segment','session_id':state.session_id,'transaction_id':txn,'parent_checkpoint_id':state.checkpoint_id,'audio_start_sample':job['audio_start_sample'],'audio_end_sample':job['audio_end_sample'],'interval_audio_sha256':job['interval_audio_sha256'],'parent_prompt_digest':job['parent_prompt_digest'],'display_sha256':digest_tokens(result['token_ids']),'feedback_state_sha256':digest_tokens(result['state_tokens']),'contract_digest':state.contract_digest,'runtime_digest':state.canonical_runtime_digest})
 sequence,sync=journal.commit_transition(session_id=state.session_id,transaction_id=txn,request_sha256=request,parent_state=state,next_state=install.state,event=event)
 return install.state,event,sequence,sync
