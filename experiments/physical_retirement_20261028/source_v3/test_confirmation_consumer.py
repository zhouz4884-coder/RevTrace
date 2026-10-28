"""2x2 CPU confirmation: actual scheduler/WAL/kernel/FIFO Consumer, scripted tokens.

These fixtures test selected behavior and guards, not GPU performance, natural
trace frequency, or model accuracy.
"""
from copy import deepcopy
from pathlib import Path
import json
import sys
import time

import numpy as np
import pytest

W=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'runtime/src'))
from revtrace.certified_display import ContinuityView,RealtimeConsumer,TrustedQwenRender,text_sha
from revtrace.composed_kernel import Kernel,Denied
from revtrace.dgft import digest_tokens
from revtrace.kernel_runtime import KernelView
from revtrace.retirement_runtime import RetirementScheduler
import retirement_service as service

EOS=100000


class Tokens:
    def encode(self,text,**kwargs):return [ord(c) for c in text]
    def decode(self,ids,skip_special_tokens=False,**kwargs):return ''.join(chr(i) for i in ids if i!=EOS)


def parse(raw,user_language=None):return 'English',raw
def desired(window):return 'A'+'abcdefghijklmnopqrstuvwxyz'[:window*2]


class FullScriptWorker:
    """CPU model adapter; complete outputs go through the native trusted render."""
    def __init__(self,name,role,flags,renderer):
        self.name=name;self.role=role;self.flags=flags;self.renderer=renderer
        self.jobs=None;self.ready={'CPU_fixture_only':True}
    def submit(self,jobs):
        assert self.jobs is None
        self.jobs=jobs;self.started=time.perf_counter()
    def poll(self):
        if self.jobs is None:return None
        if self.role=='authority' and self.jobs[0]['end_window']==3 and not self.flags['ahead_published']:
            return None
        jobs,self.jobs=self.jobs,None;rows=[]
        for job in jobs:
            target=desired(job['end_window'])
            prompt=self.renderer.tokenizer.decode(job['prompt_tokens'])
            prefix=prompt[:-5] if job['chunk_id']>=2 and prompt else ''
            assert target.startswith(prefix)
            tokens=self.renderer.tokenizer.encode(target[len(prefix):])+[EOS]
            projection,text=self.renderer(job,tokens)
            assert text==target
            rows.append(dict(job_id=job['job_id'],runtime_digest=job['runtime_digest'],
              prefix_audio_sha256=job['prefix_audio_sha256'],started_perf=self.started,
              completed_perf=time.perf_counter(),token_ids=tokens,state_tokens=projection,
              text=text,language='English',generated_tokens=len(tokens),hit_token_limit=False,
              terminated_by_eos=True))
        return rows


class ControlledConfirmation(RetirementScheduler):
    def __init__(self,*,fixture_flags,**kwargs):self.fixture_flags=fixture_flags;super().__init__(**kwargs)
    def _ready(self,role):
        eligible=super()._ready(role)
        if role=='proposal':
            eligible=[s for s in eligible if s.fine_window<5 or self.fixture_flags['first_installed']]
        return eligible


def full_cell(directory,policy,retain):
    directory.mkdir();origin=time.perf_counter();events=[]
    flags={'ahead_published':False,'first_installed':False}
    render=TrustedQwenRender(Tokens(),parse,[EOS],256)
    consumer=RealtimeConsumer(directory/'consumer.jsonl',policy=policy,strict_bound=True)
    def emit(event):
        events.append(event);consumer.put(event)
        if event['kind']=='display' and event['window']==4:flags['ahead_published']=True
        if event['kind']=='commit' and event['version']==1:flags['first_installed']=True
    config=dict(policy='coarse',rho=3,fine_seconds=.01,sample_rate=16000,microbatch=1,
      timeout_seconds=5.,authority_runtime=dict(dtype='float32',model='CPU_SCRIPTED_NOT_QWEN'),
      proposal_runtime=dict(dtype='float16',model='CPU_SCRIPTED_NOT_QWEN'),
      proposal_barrier='decoupled',proposal_reconciliation='lazy',verification_policy='canonical_generate',
      trusted_text_binding=True,retain_verified_private_prefix=retain,capture_worker_records=True,
      display_protocol='canonical-snapshot-v1',manifest_sha256='a'*64,
      evidence_type='CPU_scripted_full_protocol_fixture_not_neural',episode_origin_perf=origin,
      envelope=dict(method='dgft_original',budget_audio_seconds=2.,warning_age=1.,critical_age=2.,
        clear_age=.5,display_slo=2.,queue_threshold=8,reject_new_after_seconds=3.,tick_seconds=.0005),
      kernel_copy_mode='event-cow',consumer_policy=policy,confirmation_consumer=policy,
      physical_retirement=dict(policy='row_complete',watchdog_seconds=2.))
    workers={role:[FullScriptWorker(role,role,flags,render)] for role in ['proposal','authority']}
    scheduler=ControlledConfirmation(fixture_flags=flags,consumer=consumer,
      input_journal_path=directory/'input.wal',
      sessions=[dict(session_id=0,audio=np.zeros(1440,dtype='<f4').tobytes(),source_id='CPU_FIXTURE',language='English',offset=0.)],
      contract=config,executors=workers,emit=emit,clock=time.perf_counter,sleep=time.sleep,
      trusted_render=render,durable_journal_path=directory/'canonical.wal')
    try:
        assert isinstance(consumer.view,KernelView) and consumer.view.policy==policy
        for group in workers.values():
            for worker in group:scheduler.execution_ready(worker)
        result=scheduler.run();scheduler.close();consumer.close()
    except BaseException:
        scheduler.close()
        try:consumer.close()
        except Exception:pass
        raise
    first=[r for r in consumer.rows if r['source_kind']=='canonical-display' and r['canonical_version']==1]
    assert len(first)==1
    row=first[0]
    assert row['certified_frontier']==480
    assert row['valid_visible_frontier']==(640 if policy=='two_lane' else 480)
    assert row['visible_text']==(desired(4) if policy=='two_lane' else desired(3))
    assert row['compatible_provisional_retained']==(policy=='two_lane')
    assert all(r['policy']==policy for r in consumer.rows)
    # Retention changes the next actual worker input, independently of display.
    following=[j for j in scheduler.jobs.values() if j['role']=='proposal' and j['end_window']==5]
    assert len(following)==1
    assert following[0]['chunk_id']==(4 if retain else 3)
    assert following[0]['prompt_tokens']==render.tokenizer.encode(desired(4 if retain else 3))
    trace={e['kind'] for e in scheduler.kernel.trace}
    assert {'dispatch','row-complete','batch-drained','admission-request','canonical-synced',
      'install','publish','apply-request','view-applied'}<=trace
    assert result['certified_commits']==3 and result['fine_window_accounting_complete']
    assert scheduler.kernel.state.C[0]['F']==1440 and scheduler.book.debt==0
    assert result['final_states'][0]['text']==desired(9)
    assert (directory/'input.wal').stat().st_size>0 and (directory/'canonical.wal').stat().st_size>0
    assert not scheduler.inflight
    return result,consumer.rows,events


@pytest.mark.parametrize('policy',['checked_snapshot','two_lane'])
@pytest.mark.parametrize('retain',[False,True])
def test_complete_2x2_cells_change_consumer_and_actual_next_input(tmp_path,policy,retain):
    full_cell(tmp_path/'cell',policy,retain)


def test_checked_snapshot_checks_private_genesis_root():
    view=ContinuityView('checked_snapshot',strict_bound=True)
    view.consume(dict(kind='run-start',t0_perf=0.,contract_digest='contract'))
    event=dict(kind='display',session_id=0,time=1.,displayed=1.,display_revision=1,
      contract_digest='contract',contract_epoch=1,canonical_version=0,version=0,
      job_id='bad-root',audio_end_sample=32000,chunk_id=0,end_window=1,
      input_projection_sha256='wrong',output_projection_sha256=digest_tokens([5]),
      branch_generation=0,text='wrong root')
    row=view.consume(event,1.)
    assert row['tentative_invalidated'] and row['valid_visible_frontier']==0 and row['visible_text']==''
    event.update(job_id='good-root',display_revision=2,input_projection_sha256=digest_tokens(()),text='valid')
    row=view.consume(event,2.)
    assert row['valid_visible_frontier']==32000 and row['visible_text']=='valid'


@pytest.mark.parametrize('policy',['checked_snapshot','two_lane'])
def test_final_kernel_checks_actual_private_chain_even_if_publication_claims_compatibility(policy):
    kernel=Kernel('contract',1,0.,incremental=True)
    fact=dict(v=1,F=32000,P=digest_tokens([8]),Z=digest_tokens([8]),textsha=text_sha('canonical'),txn='tx')
    kernel.state.C={0:fact};kernel.state.D={0:{1:fact}}
    kernel.state.V={0:dict(v=0,F=0,visible=0,revision=0)}
    kernel.state.I={0:dict(accepted=64000,offered=64000,reserved=64000)}
    kernel.state.restored_input=True
    view=KernelView(kernel,policy=policy)
    view.consume(dict(kind='run-start',t0_perf=0.,contract_digest='contract'))
    view.consume(dict(kind='commit',session_id=0,version=1,segment_id='tx',audio_end_sample=32000,
      next_prompt_tokens=[8],certificate={'contract_digest':'contract','display_sha256':digest_tokens([8])}))
    kernel.event('fixture','publish','canonical',dict(sid=0,key=(0,1),publication=dict(canonical=True,fact=fact)))
    canonical=dict(kind='canonical-display',session_id=0,time=1.,displayed=1.,display_revision=1,
      contract_digest='contract',contract_epoch=1,version=1,audio_end_sample=32000,
      transaction_id='tx',canonical_projection_sha256=fact['P'],canonical_Z_sha256=fact['Z'],
      text_sha256=fact['textsha'],text='canonical')
    view.consume(canonical,1.)
    kernel.state.J['private']=dict(id='private',sid=0,role='proposal',end=64000,
      rootF=0,inputP='actual-wrong-parent',result=dict(P='out',Z='Z',textsha=text_sha('private')))
    kernel.event('fixture','publish','private',dict(sid=0,key=(0,2),
      publication=dict(canonical=False,job='private',end=64000,textsha=text_sha('private'))))
    publication=dict(kind='display',session_id=0,time=2.,displayed=2.,display_revision=2,
      contract_digest='contract',contract_epoch=1,canonical_version=1,version=1,
      job_id='private',audio_end_sample=64000,chunk_id=1,end_window=2,
      input_projection_sha256=fact['P'],output_projection_sha256='out',branch_generation=0,text='private')
    before=deepcopy(view.states)
    with pytest.raises(Denied,match='incompatible'):
        view.consume(publication,2.)
    assert view.states==before and kernel.state.V[0]['visible']==32000


def test_confirmation_cli_freezes_both_factors_and_shared_guards():
    for policy in ['checked_snapshot','two_lane']:
        for retain in ['yes','no']:
            args=service.parser().parse_args(['--out','out','--source-manifest','source.json',
              '--manifest','manifest.json','--model','model','--policy','row_complete',
              '--method','dgft_original','--confirmation-consumer',policy,'--retain',retain])
            command=service.build_command(args,Path('/fixture'),dict(code_commit='b'*40))
            assert command[command.index('--confirmation-consumer')+1]==policy
            assert command[command.index('--consumer-policy')+1]==policy
            assert ('--retain-verified-private-prefix' in command)==(retain=='yes')
            assert ('--disable-private-retention' in command)==(retain=='no')
            assert {'--protocol-kernel','--trusted-text-binding','--capture-model-inputs',
              '--input-journal-path','--durable-journal-path'}<=set(command)
