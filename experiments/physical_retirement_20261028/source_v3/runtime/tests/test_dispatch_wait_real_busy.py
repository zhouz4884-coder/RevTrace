"""Real LiveQwenScheduler CPU interleaving; requires production tick hook."""
from test_live_qwen import build
from revtrace.live_qwen import LiveQwenScheduler


def make_waiting_scheduler():
    old=build(rho=1,delay=.025,barrier='decoupled',count=2)
    config=dict(old.contract,proposal_reconciliation='lazy',dispatch_wait={
        'policy':'pending_eta','max_wait_seconds':.04,'fixed_wait_seconds':.006,
        'private_cost_default_seconds':.001,'authority_cost_default_seconds':.025,
        'install_cost_default_seconds':.001,  # zero-WAL CPU fixture scale
        'display_slo_seconds':.1,'poll_floor_seconds':.001,
        'initial_recent_wait_seconds':.006,'recent_step_seconds':.001})
    specs=[dict(session_id=s.sid,audio=s.audio,source_id=s.source_id,
        language=s.language,offset=s.offset) for s in old.sessions.values()]
    q=LiveQwenScheduler(sessions=specs,contract=config,executors=old.executors,
        clock=old.clock,sleep=old.sleep,emit=lambda row:None)
    q.clock.now=q.t0+.010001;q._dispatch()  # session0 P/A; session1 not released
    q.clock.now=q.t0+.012;q._receive()      # session0 P done, A pending
    q.executors['proposal'][0].delay=.1
    q.clock.now=q.t0+.020001;q._dispatch()  # wait session0; serve session1
    assert q._dispatch_wait_controller.waits[0,2].active
    assert q.inflight['p'][1] and q.jobs[q.inflight['p'][1][0]]['session_id']==1
    return q


def test_real_scheduler_releases_logical_wait_before_other_session_gpu_drains():
    q=make_waiting_scheduler();prior_ids=list(q.inflight['p'][1])
    q.clock.now=q.t0+.04;q._receive();q._commit_ready();q._dispatch()
    release=[e for e in q.events if e['kind']=='dispatch-wait-release'
             and e['session_id']==0 and e['window']==2]
    assert release and release[0]['reason']=='canonical-advanced'
    assert not release[0]['proposal_worker_available']
    assert q.inflight['p'][1]==prior_ids
    assert q._dispatch_wait_controller.waits[0,2].closed


def test_pure_pre_wait_description_matches_actual_make_job_after_rebase():
    q=make_waiting_scheduler()
    q.clock.now=q.t0+.04;q._receive();q._commit_ready()
    s=q.sessions[0];assert s.state.checkpoint_id>s.branch_parent
    before=q._dispatch_wait_controller.describe_private_input(q,s,s.fine_window)
    assert before['would_rebase']
    j=q._make_job(s,'proposal')
    assert before['prompt_tokens']==j['prompt_tokens']
    assert before['chunk_id']==j['chunk_id']
    assert before['root_frontier']==j['audio_start_sample']
    assert before['target_frontier']==j['audio_end_sample']
    assert before['parent']==j['parent']
