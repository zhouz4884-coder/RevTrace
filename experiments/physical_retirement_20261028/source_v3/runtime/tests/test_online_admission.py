"""CPU deterministic protocol controls; not model/fault prevalence evidence."""
import copy
import numpy as np
import pytest
from test_live_qwen import Clock,Fake
from revtrace.online_admission import OnlineAdmissionScheduler,gate_candidate,target_identity,fallback_row_plan,cohort_offset

@pytest.mark.parametrize('mode',['strict','score'])
@pytest.mark.parametrize('row,pred,margin,eos,budget,expected',[
 ([1,9],[1,9],[.1,.1],[9],8,True),
 ([1],[1],[1.],[9],8,False),
 ([1,9,2],[1,9,2],[1.,1.,1.],[9],8,False),
 ([],[],[],[9],8,False),
 ([1,2,3],[1,2,3],[1.,1.,1.],[9],2,False),
 ([1,2],[1,2],[1.,1.],[9],2,True),
 ])
def test_full_sequence_not_just_scored_prefix(mode,row,pred,margin,eos,budget,expected):
 assert gate_candidate(mode,row,pred,margin,eos=eos,budget=budget)[0]==expected

def test_high_own_context_margin_is_not_correct_context_evidence():
 assert not gate_candidate('strict',[1,9],[2,9],[.9,.9],eos=[9],budget=8)[0]
 assert not gate_candidate('score',[1,9],[2,9],[-.1,.9],eos=[9],budget=8)[0]
 assert not gate_candidate('score',[1,9],[1,9],[float('nan'),.9],eos=[9],budget=8)[0]

class CheckedFake(Fake):
 def poll(self):
  rs=super().poll()
  if rs is None:return rs
  for r in rs:
   j=self.saved[r['job_id']]
   if j['role']=='authority':
    mode=j['online_selection_mode'];z=j['candidate_token_ids']
    r['token_ids']=z;r['state_tokens']=z
    r['online_verification']={'mode':mode,'target_identity':target_identity(j),'executed_prompt_tokens':j['prompt_tokens'],'actual_audio_sha256':j['prefix_audio_sha256'],'dtype':'float32','context_override_used':False,'fallback_used':False,'fallback_generated':False,'fallback_batch_seconds':0.,'predicted_token_ids':z,'candidate_margins':[.1]*len(z),'eos_token_ids':[]}
  return rs
 def submit(self,jobs):
  self.saved={j['job_id']:copy.deepcopy(j) for j in jobs};super().submit(jobs)

def build(mode='strict',path=None,corrupt=None,traffic='clean'):
 clock=Clock();cfg={'policy':'fine_certified','rho':1,'fine_seconds':.01,'sample_rate':16000,'authority_runtime':{'dtype':'float32','max_new_tokens':1},'proposal_runtime':{'dtype':'float16'},'microbatch':2,'timeout_seconds':5,'proposal_barrier':'decoupled','proposal_reconciliation':'lazy','verification_policy':'online_'+mode,'journal_sync_mode':'group_ready','retain_verified_private_prefix':True,'online_study':{'method':mode,'traffic':traffic,'score_threshold':.05,'donors':[{'id':'known-CPU-donor','tokens':[30,31,32,33,34,35]}]},'evidence_type':'cpu_deterministic_online_fixture_not_GPU'}
 ss=[{'session_id':i,'audio':np.zeros(1920,dtype='<f4').tobytes(),'source_id':str(i),'language':'English','offset':i*.004} for i in range(2)]
 p=Fake('p',clock,.008);p.same_projection=True;a=CheckedFake('a',clock,.009)
 s=OnlineAdmissionScheduler(sessions=ss,contract=cfg,executors={'proposal':[p],'authority':[a]},emit=lambda e:None,clock=clock,sleep=clock.sleep,durable_journal_path=path)
 if corrupt:
  orig=a.poll
  def poll():
   rs=orig()
   if rs:
    for r in rs:corrupt(r['online_verification'])
   return rs
  a.poll=poll
 return s

@pytest.mark.parametrize('mode',['unprotected','score','strict'])
def test_ready_candidate_audio_and_same_WAL_pipeline(mode,tmp_path):
 s=build(mode,tmp_path/'w.wal');r=s.run();assert r['fine_window_accounting_complete']
 for e in s.events:
  if e['kind']=='online-candidate-attached':assert e['candidate_completed']<=e['authority_enqueue']
 for j in s.jobs.values():
  assert j['audio_ready_perf']<=j['enqueue_perf']
  if j['role']=='authority':assert 'candidate_token_ids' in j
 assert all(x.state.audio_frontier_window==1920 for x in s.sessions.values());s.close()

@pytest.mark.parametrize('corrupt',[
 lambda x:x.update(target_identity='wrong-parent-context'),
 lambda x:x.update(executed_prompt_tokens=[999]),
 lambda x:x.update(actual_audio_sha256='wrong-audio'),
 lambda x:x.update(dtype='float16'),
 lambda x:x.update(context_override_used=True),
 lambda x:x.update(predicted_token_ids=[888]),
 lambda x:x.update(fallback_used=True,fallback_generated=False,fallback_batch_seconds=0),
 ])
def test_protected_receipt_fail_closed(corrupt):
 s=build(corrupt=corrupt)
 with pytest.raises(ValueError):s.run()
 assert not any(e['kind']=='commit' for e in s.events)

def test_F2_only_after_consumed_chunk_and_once_per_session():
 s=build(traffic='F2');s.run();faults=[e for e in s.events if e['kind']=='F2-injection-issued']
 assert len(faults)==2 and all(e['chunk_id']>=2 and e['end_window']>=5 for e in faults)
 assert len({e['session_id'] for e in faults})==2

def test_no_candidate_no_authority_dispatch():
 s=build();s.clock.sleep(.02)
 assert not s._ready('authority') and not s._proposal_results

def test_long_sequence_checks_beyond64():
 z=[1]*130+[9];p=z.copy();p[100]=2
 assert not gate_candidate('strict',z,p,[],eos=[9],budget=256)[0]

def test_consumer_failure_still_closes_only_owned_workers(monkeypatch):
 import importlib.util
 from pathlib import Path
 path=Path(__file__).resolve().parents[1]/'scripts/run_tc_live_qwen.py'
 monkeypatch.syspath_prepend(str(path.parent))
 spec=importlib.util.spec_from_file_location('online_cli_cleanup',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 closed=[]
 class Component:
  def __init__(self,name,fail=False):self.name=name;self.fail=fail
  def close(self):
   closed.append(self.name)
   if self.fail:raise RuntimeError('consumer correctly failed closed')
 with pytest.raises(RuntimeError):m.close_owned_components(Component('consumer',True),Component('WAL'),{'proposal':[Component('owned-p')],'authority':[Component('owned-a')]})
 assert closed==['consumer','WAL','owned-p','owned-a']

@pytest.mark.parametrize('shapes,failed,policy,expected',[
 ({'ids':[4,40],'features':[4,128,400]},[1,3],'selective',[1,3]),
 ({'ids':[4,40],'features':[5,128,400]},[1,3],'selective',[0,1,2,3]),
 ({'ids':[4,40],'scalar':[]},[1],'selective',[0,1,2,3]),
 ({'ids':[4,40]},[1],'full',[0,1,2,3]),
 ({'ids':[4,40]},[0,1,2,3],'selective',[0,1,2,3]),
 ])
def test_fallback_row_mapping_fail_closed(shapes,failed,policy,expected):
 assert fallback_row_plan(shapes,4,failed,policy)==expected

@pytest.mark.parametrize('bad',[[4],[-1],[1,1],[True]])
def test_fallback_cannot_select_unsubmitted_or_duplicate_rows(bad):
 with pytest.raises(ValueError):fallback_row_plan({'ids':[4,40]},4,bad,'selective')

def test_cohort_arrivals_are_explicit_and_same_for_all_policies():
 assert [cohort_offset(i,8) for i in [0,7,8,15]]==[0.,1.75,32.,33.75]
 with pytest.raises(ValueError):cohort_offset(1,0)
