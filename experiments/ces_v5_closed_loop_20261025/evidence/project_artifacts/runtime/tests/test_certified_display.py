"""CPU fixtures with legal adapter oracle, not Qwen neural evidence."""
import importlib.util,json,time
from pathlib import Path
import pytest
from revtrace.live_qwen import LiveQwenScheduler
from revtrace.certified_display import TrustedQwenRender,validate_bound_text,ContinuityView,RealtimeConsumer,text_sha
from revtrace.dgft import digest_tokens
spec=importlib.util.spec_from_file_location('d_fixture',Path(__file__).with_name('test_live_qwen.py'));f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
class Tok:
 def encode(self,s):return [ord(c) for c in s]
 def decode(self,Z,skip_special_tokens=False,**kw):return ''.join(chr(t) for t in Z if not (skip_special_tokens and t==0))
def render(budget=256):return TrustedQwenRender(Tok(),lambda s,user_language:('English',s),[0],budget)
def build(path=None,tamper=None):
 ref=f.build(rho=3,barrier='decoupled');clock=f.Clock();r=render()
 class Worker(f.Fake):
  def poll(self):
   jobs=self.jobs;rows=super().poll()
   if rows:
    for job,row in zip(jobs,rows):
     Z=[ord(c) for c in '你好🙂 '+str(job['end_window'])]+[0];P,text=r(job,Z)
     row.update(token_ids=Z,state_tokens=P,text=text)
     if tamper and job['role']=='authority':tamper(row)
   return rows
 cfg=dict(ref.contract,proposal_reconciliation='lazy',display_protocol='canonical-snapshot-v1',trusted_text_binding=True,durability_mode='wal' if path else 'volatile')
 return LiveQwenScheduler(sessions=[{'session_id':ss.sid,'audio':ss.audio,'source_id':ss.source_id,'language':ss.language,'offset':ss.offset} for ss in ref.sessions.values()],contract=cfg,executors={'proposal':[Worker('p',clock)],'authority':[Worker('a',clock)]},clock=clock,sleep=clock.sleep,emit=lambda e:None,durable_journal_path=path,trusted_render=r)
@pytest.mark.parametrize('field,value',[('text','WRONG'),('state_tokens',[1,2]),('token_ids',[97]),('token_ids',[97,0,98]),('token_ids',[97,0,0])])
def test_text_projection_and_termination_fail_before_commit(field,value):
 s=build(tamper=lambda r:r.update({field:value}))
 with pytest.raises(ValueError):s.run()
 assert not any(e['kind'] in ['commit','canonical-display'] for e in s.events);s.close()
@pytest.mark.parametrize('text',['你好🙂','e\u0301é','ＡＢＣ','\ufffd','<|special|>','\n  x\t'])
def test_unicode_byte_exact_render(text):
 r=render();j={'prompt_tokens':[],'chunk_id':0,'language':'English'};Z=[ord(c) for c in text]+[0];P,t=r(j,Z)
 assert t.encode()==text.encode();validate_bound_text(r,j,{'token_ids':Z,'state_tokens':P,'text':text})
def test_exact_budget_without_eos_is_legal_not_complete():
 assert render(4)({'prompt_tokens':[],'chunk_id':0,'language':'English'},[97]*4)[1]=='aaaa'
def test_restart_reconstructs_and_republishes_selected_text(tmp_path):
 p=tmp_path/'d.wal';s=build(p);s.run();expected=[(ss.sid,ss.text) for ss in s.sessions.values()];s.close()
 t=build(p);assert expected==[(ss.sid,ss.text) for ss in t.sessions.values()];assert all(e['recovered'] for e in t.events if e['kind']=='canonical-display');t.close()
def test_wal_failure_never_produces_certified_publication(tmp_path):
 s=build(tmp_path/'bad.wal')
 def fail(_):raise OSError('injected sync error')
 s._journal._write_frame=fail
 with pytest.raises(OSError):s.run()
 assert not any(e['kind']=='canonical-display' for e in s.events);s.close()
def test_repeated_legal_cpu_oracle():
 histories=[]
 for _ in range(2):
  s=build();s.run();histories.append([(e['session_id'],e['version'],e['next_prompt_tokens']) for e in s.events if e['kind']=='commit']);s.close()
 assert histories[0]==histories[1]
def test_actual_thread_observes_after_emit_and_rejects_uninstalled(tmp_path):
 c=RealtimeConsumer(tmp_path/'consumer.jsonl');start=time.perf_counter();c.put({'kind':'run-start','t0_perf':start});c.put({'kind':'display','job_id':'fixture','session_id':0,'time':0.,'displayed':0.,'text':'x','audio_end_sample':32000,'display_revision':1,'version':0});out=c.close()
 assert out['records']==1 and c.rows[0]['observed']>=0
 with pytest.raises(ValueError):ContinuityView().consume({'kind':'canonical-display','session_id':0,'time':0,'version':1,'display_revision':1,'transaction_id':'x','audio_end_sample':1,'text':'x'})
def test_whole_provisional_compatibility_requires_exact_boundary_state():
 v=ContinuityView('two_lane');P=digest_tokens([1]);v.consume({'kind':'run-start','t0_perf':1})
 first={'kind':'display','session_id':0,'time':0,'displayed':0,'version':0,'canonical_version':0,'display_revision':1,'job_id':'a','text':'one','audio_end_sample':32000,'end_window':1,'chunk_id':0,'input_projection_sha256':digest_tokens([]),'output_projection_sha256':P,'branch_generation':0}
 v.consume(first);later=dict(first,job_id='b',display_revision=2,text='one two',audio_end_sample=64000,end_window=2,chunk_id=1,input_projection_sha256=P,output_projection_sha256=digest_tokens([1,2]));v.consume(later)
 v.consume({'kind':'commit','session_id':0,'version':1,'segment_id':'t','audio_end_sample':32000,'next_prompt_tokens':[1]})
 row=v.consume({'kind':'canonical-display','session_id':0,'time':1,'displayed':1,'version':1,'display_revision':3,'transaction_id':'t','audio_end_sample':32000,'text':'one','canonical_projection_sha256':P,'text_sha256':text_sha('one')})
 assert row['compatible_provisional_retained'] and row['valid_visible_frontier']==64000 and row['certified_text']=='one' and not row['joined_suffix']
 # Old version cannot replace certified state; a different parent isn't spliced.
 old=dict(later,display_revision=4,canonical_version=0,text='BAD');assert v.consume(old) is None
 bad=dict(later,job_id='c',display_revision=5,canonical_version=1,chunk_id=1,input_projection_sha256=digest_tokens([9]),text='BAD')
 row=v.consume(bad);assert row['tentative_invalidated'] and row['visible_text']=='one'
