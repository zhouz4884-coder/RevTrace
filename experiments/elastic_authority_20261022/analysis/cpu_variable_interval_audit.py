"""Audit original admission/WAL on variable spans. NOT Elastic scheduler evidence."""
from pathlib import Path
from dataclasses import asdict
import hashlib,itertools,json,math,sys,tempfile
S=Path(r'D:\StreamTxn\outputs\revtrace_phaseD_20261021\public_release\runtime');sys.path.insert(0,str(S/'src'))
from revtrace.dgft import FeedbackTransactionState,CanonicalSegmentJob,build_dual_axis_certificate,commit_canonical_segment,digest_tokens
from revtrace.durable_journal import DurableCommitJournal
W=Path(__file__).resolve().parent;patterns=list(itertools.product([1,2,3],repeat=4));rows=[];accepted=0
for idx,pattern in enumerate(patterns):
 initial=FeedbackTransactionState(0,1,'elastic-cpu-audit',contract_digest='fixed-chi-allowed-1-2-3',canonical_runtime_digest='trusted-fixture');state=initial
 with tempfile.TemporaryDirectory() as td:
  wal=DurableCommitJournal(Path(td)/'state.wal',[initial])
  for k,rho in enumerate(pattern):
   if k==2:
    old=state;wal.close();wal=DurableCommitJournal(Path(td)/'state.wal',[initial]);state=wal.states()[0]
    assert state.audio_frontier_window==old.audio_frontier_window and state.prompt_tokens==old.prompt_tokens and state.contract_epoch==2
   start=state.audio_frontier_window;end=start+rho*2;txn=f'0:{start}:{end}';audio=bytes(end-start);A=hashlib.sha256(audio).hexdigest();Z=[idx,k,rho];P=[idx,k,end]
   job=CanonicalSegmentJob(0,state.contract_epoch,state.policy_version,state.checkpoint_id,start,end,txn,digest_tokens(state.prompt_tokens),state.contract_digest,state.canonical_runtime_digest,A)
   cert=build_dual_axis_certificate(job=job,audio=audio,display_tokens=Z,feedback_state_tokens=P,canonical_runtime_digest=state.canonical_runtime_digest)
   step=commit_canonical_segment(state,job,certificate=cert,display_tokens=Z,segment_tokens=Z,next_prompt_tokens=P);assert step.accepted
   event={'event':'canonical-segment-committed','session_id':0,'segment_id':txn,'parent_checkpoint_id':state.checkpoint_id,'checkpoint_id':step.state.checkpoint_id,'audio_start_sample':start,'audio_end_sample':end,'certificate':asdict(cert),'invalidated_speculative_versions':[]}
   wal.commit_transition(session_id=0,transaction_id=txn,request_sha256=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest(),parent_state=state,next_state=step.state,event=event)
   assert not commit_canonical_segment(step.state,job,certificate=cert,display_tokens=Z,segment_tokens=Z,next_prompt_tokens=P).accepted
   state=step.state;accepted+=1
  wal.close();assert state.audio_frontier_window==sum(pattern)*2
 rows.append({'pattern':pattern,'accepted_transitions':4,'recovered_after_first_two':True,'final_F':state.audio_frontier_window,'epoch':state.contract_epoch,'evidence':'CPU_ORIGINAL_PRIMITIVE_AND_REAL_WAL_SYNTHETIC_CONTENT_NOT_GPU'})
# The original V does not interpret opaque chi as an executable range policy.
state=FeedbackTransactionState(0,1,'elastic-cpu-audit',contract_digest='fixed-chi-allowed-1-2-3',canonical_runtime_digest='trusted-fixture');job=CanonicalSegmentJob(0,1,state.policy_version,0,0,8,'0:0:8',digest_tokens([]),state.contract_digest,state.canonical_runtime_digest,hashlib.sha256(bytes(8)).hexdigest());cert=build_dual_axis_certificate(job=job,audio=bytes(8),display_tokens=[1],feedback_state_tokens=[1],canonical_runtime_digest=state.canonical_runtime_digest)
unrestricted=commit_canonical_segment(state,job,certificate=cert,display_tokens=[1],segment_tokens=[1],next_prompt_tokens=[1]);assert unrestricted.accepted
out={'status':'PASS_VARIABLE_INTERVAL_PRIMITIVE_AUDIT_NOT_DYNAMIC_RUNTIME','patterns':len(rows),'accepted_transitions':accepted,'all_duplicate_admissions_rejected':True,'close_reopen_WAL_patterns':len(rows),'caller_range_guard_required':True,'opaque_chi_does_not_reject_rho4_by_itself':unrestricted.accepted,'counterexample_fixed_count':{'lengths':[1,3,2],'actual_commits':3,'incorrect_ceil_total_over_3':math.ceil(6/3)},'model_generations':0,'rows':rows}
(W/'CPU_VARIABLE_INTERVAL_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
