"""CPU protocol/finite orchestration fixtures, not dynamic GPU results."""
import copy,hashlib
import numpy as np
import pytest
from test_live_qwen import Clock,Fake
from revtrace.elastic_authority import ElasticAuthorityScheduler
from revtrace.durable_journal import JournalError

def make(kind='joint',path=None,emit=None,count=4,deadline=.08):
 c=Clock();table=[{'rho':r,'batch_rows':b,'median_seconds':.004*r*b,'p90_seconds':.005*r*b} for r in [1,2,3] for b in [1,2,4]]
 rule={'kind':kind,'allowed':[1,2,3],'service_cost_table':table,'capacity_target':.95,'backlog_cutoffs':[2,5],'commit_deadline_seconds':deadline,'resume':'reset unsubmitted plans under same rule'}
 cfg={'policy':'coarse','rho':int(kind[-1]) if kind.startswith('fixed') else 3,'fine_seconds':.01,'sample_rate':16000,'authority_runtime':{'dtype':'float32'},'proposal_runtime':{'dtype':'float16'},'microbatch':2,'authority_microbatch':2,'timeout_seconds':5,'proposal_barrier':'decoupled','proposal_reconciliation':'lazy','journal_sync_mode':'group_ready','verification_policy':'canonical_generate','retain_verified_private_prefix':True,'granularity_policy':rule,'display_protocol':'canonical-snapshot-v1','trusted_text_binding':True,'evidence_type':'cpu_elastic_protocol_fixture_not_GPU'}
 ss=[{'session_id':i,'audio':np.zeros(960,dtype='<f4').tobytes(),'source_id':str(i),'language':'English','offset':i*.004} for i in range(count)]
 workers={'proposal':[Fake('p',c,.003)],'authority':[Fake('a',c,.018)]}
 for group in workers.values():
  for w in group:w.same_projection=True
 s=ElasticAuthorityScheduler(sessions=ss,contract=cfg,executors=workers,emit=emit or (lambda e:None),clock=c,sleep=c.sleep,durable_journal_path=path,trusted_render=lambda j,z:(list(z),str(z[0])))
 return s

@pytest.mark.parametrize('kind',['fixed1','fixed2','fixed3','backlog','deadline','joint'])
def test_finite_complete_admission_and_no_future_audio(kind):
 s=make(kind);result=s.run()
 assert result['fine_window_accounting_complete']
 for sid,state in s.sessions.items():
  assert state.state.audio_frontier_window==960
  cursor=0
  for p in [p for p in s.plan_history if p['session_id']==sid]:
   assert p['start_window']==cursor and 0<p['end_window']-cursor<=p['selected_rho']<=3;cursor=p['end_window']
  assert cursor==6
 for j in s.jobs.values():assert j['enqueue_perf']>=j['audio_ready_perf'] and j['audio_end_sample']>j['audio_start_sample']
 assert len(s.plan_history)==result['certified_commits']

@pytest.mark.parametrize('bad',[0,4,-1,True,1.5])
def test_range_guard_before_job_creation(bad):
 s=make();state=s.sessions[0]
 with pytest.raises(ValueError):s._freeze_plan(state,bad,{})
 assert not s.jobs and state.state.checkpoint_id==0

def test_frozen_plan_cannot_be_replaced():
 s=make('fixed1');state=s.sessions[0];before=copy.deepcopy(s.plans[0])
 with pytest.raises(ValueError):s._freeze_plan(state,3,{})
 assert s.plans[0]==before

def test_inflight_parent_plan_cannot_change_before_install():
 s=make('fixed1');original=s._receive
 def corrupt():
  original()
  for state in s.sessions.values():
   if state.auth_result is not None:s.plans[state.sid]['parent']+=1
 s._receive=corrupt
 with pytest.raises(ValueError):s.run()
 assert all(state.state.checkpoint_id==0 for state in s.sessions.values())

@pytest.mark.parametrize('kind',['backlog','deadline','joint'])
def test_nonuniform_WAL_resume_and_contract_change_fail_closed(tmp_path,kind):
 path=tmp_path/'state.wal';stop={'fired':False}
 def emit(e):
  if e['kind']=='commit' and not stop['fired']:stop['fired']=True;raise RuntimeError('CPU owner interruption fixture')
 old=make(kind,path,emit)
 with pytest.raises(RuntimeError):old.run()
 old.close()
 restored=make(kind,path);r=restored.run();assert all(s.state.audio_frontier_window==960 and s.state.contract_epoch==2 for s in restored.sessions.values());restored.close()
 with pytest.raises(JournalError):make(kind,path,deadline=.07)

def test_pending_jobs_immutable_across_new_plans():
 s=make('joint');snapshots={}
 for group in s.executors.values():
  for worker in group:
   submit=worker.submit;poll=worker.poll
   def wrapped_submit(js,submit=submit):
    for j in js:snapshots[j['job_id']]=copy.deepcopy(j)
    submit(js)
   def wrapped_poll(poll=poll):
    for jid,j in snapshots.items():assert s.jobs[jid]==j
    return poll()
   worker.submit=wrapped_submit;worker.poll=wrapped_poll
 s.run()

def test_sample_interval_cannot_diverge_from_selected_window():
 s=make('fixed1');original=s._receive
 def corrupt():
  original()
  for state in s.sessions.values():
   if state.auth_result is not None:s.jobs[state.auth_result['job_id']]['audio_end_sample']+=1
 s._receive=corrupt
 with pytest.raises(ValueError):s.run()
 assert all(state.state.checkpoint_id==0 for state in s.sessions.values())

def test_unreleased_cohorts_not_in_online_observation():
 s=make();s.sessions[3].offset=100.;s.clock.sleep(.011)
 active=s._active(s.clock());assert all(x.sid!=3 for x in active)
 _,obs=s._choose(s.sessions[0]);assert obs['active_released_streams']==len(active) and not obs['future_cohorts_or_text_labels_used']
