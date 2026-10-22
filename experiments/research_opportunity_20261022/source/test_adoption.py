"""CPU fixtures only: actual original WAL/admission, no inference claims."""
import copy,json,sys,tempfile,time,os
from pathlib import Path
from dataclasses import replace
FROZEN=Path(os.environ.get('REVTRACE_FROZEN_RUNTIME',r'D:\StreamTxn\outputs\revtrace_phaseD_20261021\public_release\runtime'))
sys.path.insert(0,str(FROZEN/'src'))
from revtrace.dgft import FeedbackTransactionState,digest_tokens
from revtrace.durable_journal import DurableCommitJournal,JournalError
from adoption_core import digest,inspect_adoption,install_result
W=Path(__file__).resolve().parent
initial=FeedbackTransactionState(0,1,'coarse',contract_digest='c',canonical_runtime_digest='r')
job={'session_id':0,'role':'authority','source_id':'s','language':'English','parent':0,'parent_prompt_digest':digest_tokens([]),'prompt_tokens':[],'chunk_id':0,'chunk_advance':3,'end_window':3,'audio_start_sample':0,'audio_end_sample':96000,'contract_digest':'c','runtime_digest':'r','prefix_audio_sha256':'a'*64,'interval_audio_sha256':'a'*64,'job_id':'old-job'}
result={'job_id':'old-job','runtime_digest':'r','prefix_audio_sha256':'a'*64,'token_ids':[4,9],'state_tokens':[4],'text':'test'}
base={'supervisor_id':'sup','worker_incarnation':'w1','manifest_digest':'m','source_role':'authority','dispatch_epoch':1,'job':job,'job_sha256':digest(job),'result':result,'result_sha256':digest(result)}
state=replace(initial,contract_epoch=2);rows=[]
def check(name,r=None,s=state,e=job,live=True,owner=2,wanted=None):
 value=inspect_adoption(s,e,copy.deepcopy(base if r is None else r),manifest_digest='m',worker_live=live,supervisor_id='sup',worker_incarnation='w1',owner_epoch=owner)
 assert value==wanted,(name,value,wanted);rows.append({'case':name,'observed':value,'expected':wanted,'evidence':'CPU_FIXTURE_NO_GPU'})
check('legal prior computation under current parent',wanted='eligible-for-new-epoch-authorization')
for field,value in [('supervisor_id','fake'),('worker_incarnation','old'),('manifest_digest','other'),('source_role','proposal'),('dispatch_epoch',2)]:
 r=copy.deepcopy(base);r[field]=value;check(field,r,wanted={'supervisor_id':'wrong-supervisor','worker_incarnation':'wrong-worker-incarnation','manifest_digest':'manifest-mismatch','source_role':'not-authority-source','dispatch_epoch':'not-prior-epoch'}[field])
check('worker died',live=False,wanted='worker-dead');check('old owner raced after recovery',owner=1,wanted='not-current-owner')
new_state=replace(state,checkpoint_id=1,audio_frontier_window=32000,prompt_tokens=(7,))
new_expected=dict(job,parent=1,audio_start_sample=32000,prompt_tokens=[7],parent_prompt_digest=digest_tokens([7]),chunk_id=1,chunk_advance=2)
check('ledger parent advanced while old work still runs',s=new_state,e=new_expected,wanted='not-current-logical-job')
for field,value in [('session_id',1),('parent',1),('prompt_tokens',[7]),('audio_end_sample',64000),('contract_digest','wrong'),('runtime_digest','bad'),('source_id','cross-source'),('prefix_audio_sha256','b'*64),('interval_audio_sha256','b'*64),('chunk_id',1),('language','Chinese')]:
 r=copy.deepcopy(base);r['job'][field]=value;r['job_sha256']=digest(r['job']);check(field+' mismatch',r,wanted='not-current-logical-job')
r=copy.deepcopy(base);r['job']['prompt_tokens']=[7];check('dispatch mutated',r,wanted='mutated-dispatch')
r=copy.deepcopy(base);r['result']['text']='fake';check('result mutated',r,wanted='mutated-result')
for field,value,why in [('job_id','fake','result-job-mismatch'),('runtime_digest','bad','result-runtime-mismatch'),('prefix_audio_sha256','b'*64,'result-audio-mismatch')]:
 r=copy.deepcopy(base);r['result'][field]=value;r['result_sha256']=digest(r['result']);check(field+' result',r,wanted=why)
r=copy.deepcopy(base);r['result']=None;check('still executing with trusted dispatch',r,wanted='pending')
proof={'text_sha256':digest('test'),'render_inputs':{},'rendered_text':'test'} # fixture; GPU uses real trusted Render
with tempfile.TemporaryDirectory() as folder:
 path=Path(folder)/'ledger.wal'
 with DurableCommitJournal(path,[initial]) as wal:pass
 with DurableCommitJournal(path,[initial]) as wal:
  recovered=wal.states()[0];assert recovered.contract_epoch==2
  # Original lock blocks concurrent live owners before an authorization race.
  try:other=DurableCommitJournal(path,[initial]);raise AssertionError('double writer opened')
  except JournalError:rows.append({'case':'concurrent owner WAL lock','observed':'rejected','expected':'rejected','evidence':'CPU_ACTUAL_WAL'})
  installed,event,seq,sync=install_result(wal,recovered,job,result,proof)
  try:from gpu_feasibility_v3 import publish_certified
  except ImportError:from gpu_feasibility import publish_certified
  for restored_view in [False,True]:
   d=Path(folder)/str(restored_view);d.mkdir();views=publish_certified(d,{'contract_digest':'c'},installed,event,result,restored_view)
   assert views[-1]['certified_text']==result['text']
   rows.append({'case':'real FIFO '+('recovered' if restored_view else 'fresh')+' publication schema','observed':'consumed valid certificate','expected':'consumed valid certificate','evidence':'CPU_REAL_CONSUMER_NOT_GPU'})
  check('already committed duplicate after install',s=installed,wanted='already-durable')
  # Both orderings of new-vs-old result race have one installed transaction.
  for label in ['old result second','new result second']:
   check(label,s=installed,wanted='already-durable')
 with DurableCommitJournal(path,[initial]) as wal:
  restored=wal.states()[0];assert restored.checkpoint_id==1 and len(restored.committed_segment_ids)==1
  check('already WAL committed but never published',s=restored,owner=3,wanted='already-durable')
rows.append({'case':'new epoch original admission + persistent replay','observed':'one install survives epoch3','expected':'one install survives epoch3','evidence':'CPU_ACTUAL_WAL'})
start=time.perf_counter();iterations=20000
for _ in range(iterations):inspect_adoption(state,job,base,manifest_digest='m',worker_live=True,supervisor_id='sup',worker_incarnation='w1',owner_epoch=2)
out={'status':'PASS_CPU_FAULT_MATRIX','cases':rows,'cpu_guard_calls':iterations,'cpu_guard_mean_seconds':(time.perf_counter()-start)/iterations,'does_not_measure_IPC_or_GPU_or_production_tail':True}
destination=Path(os.environ.get('REVTRACE_AUDIT_OUTPUT',str(W/'CPU_FAULT_MATRIX.json')));destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'cases':len(rows),'guard_mean_us':out['cpu_guard_mean_seconds']*1e6}))
