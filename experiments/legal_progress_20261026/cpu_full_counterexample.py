"""Actual scheduler/journal/Render/Consumer path with a SCRIPTED CPU adapter.

The completion order is a controlled fixture. Alphabet outputs are NOT GPU
measurements. They pass the native rollback5 renderer rather than assigning
P hashes by hand. Private results never become Canonical authorities.
"""
from pathlib import Path
import sys,time,json,hashlib,argparse
import numpy as np
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.historical_display import HistoricalKernelScheduler
from revtrace.certified_display import RealtimeConsumer,TrustedQwenRender

EOS=100000
class Tokens:
    def encode(self,text,**kwargs):return [ord(c) for c in text]
    def decode(self,ids,skip_special_tokens=False,**kwargs):return ''.join(chr(i) for i in ids if i!=EOS)

def parse(raw,user_language=None):return 'English',raw
def target_A(window):return 'A'+'abcdefghijklmnopqrstuvwxyz'[:window*2]

class ScriptWorker:
    def __init__(self,name,role,flags,render,clock):
        self.name=name;self.role=role;self.flags=flags;self.render=render;self.clock=clock;self.jobs=None;self.ready={}
    def submit(self,jobs):
        assert self.jobs is None;self.jobs=jobs;self.started=self.clock()
    def poll(self):
        if self.jobs is None:return None
        if self.role=='authority':
            end=self.jobs[0]['end_window']
            if end==3 and not self.flags['old_A14_published']:return None
            if end==6 and not self.flags['new_B16_published']:return None
        jobs,self.jobs=self.jobs,None;out=[]
        for j in jobs:
            w=j['end_window']
            if self.role=='authority':desired='AaXXXXX' if w==3 else target_A(w)
            else:desired=target_A(w) if j['parent']==0 else 'AaB_BRANCH_16'
            prompt=self.render.tokenizer.decode(j['prompt_tokens']);prefix=prompt[:-5] if j['chunk_id']>=2 and prompt else ''
            assert desired.startswith(prefix),(j,desired,prefix)
            z=self.render.tokenizer.encode(desired[len(prefix):])+[EOS]
            P,text=self.render(j,z);assert text==desired
            out.append(dict(job_id=j['job_id'],runtime_digest=j['runtime_digest'],prefix_audio_sha256=j['prefix_audio_sha256'],
                started_perf=self.started,completed_perf=self.clock(),token_ids=z,state_tokens=P,text=text,language='English',
                generated_tokens=len(z),hit_token_limit=False,terminated_by_eos=True))
        return out

class ControlledScheduler(HistoricalKernelScheduler):
    def __init__(self,*,fixture_flags,**kwargs):self.fixture_flags=fixture_flags;super().__init__(**kwargs)
    def _ready(self,role):
        eligible=super()._ready(role)
        if role=='proposal':eligible=[s for s in eligible if s.fine_window<8 or self.fixture_flags['C1_installed']]
        return eligible

def run(root,strategy):
    D=root/strategy;D.mkdir();clock=time.perf_counter;origin=clock();flags=dict(old_A14_published=False,C1_installed=False,new_B16_published=False)
    render=TrustedQwenRender(Tokens(),parse,[EOS],256);events=[]
    consumer=RealtimeConsumer(D/'consumer.jsonl',policy='two_lane',strict_bound=True)
    def emit(e):
        events.append(e);consumer.put(e)
        if e['kind']=='display' and e.get('window')==7:flags['old_A14_published']=True
        if e['kind']=='commit' and e['version']==1:flags['C1_installed']=True
        if e['kind']=='display' and e.get('window')==8 and e['parent']==1:flags['new_B16_published']=True
    cfg=dict(policy='coarse',rho=3,fine_seconds=.01,sample_rate=16000,microbatch=1,timeout_seconds=5,
        authority_runtime=dict(dtype='float32',model='SCRIPTED_CPU_ORACLE_NOT_QWEN'),proposal_runtime=dict(dtype='float16',model='SCRIPTED_CPU_ORACLE_NOT_QWEN'),
        proposal_barrier='decoupled',proposal_reconciliation='lazy',verification_policy='canonical_generate',trusted_text_binding=True,
        retain_verified_private_prefix=True,capture_worker_records=True,display_protocol='canonical-snapshot-v1',manifest_sha256='a'*64,
        evidence_type='cpu_scripted_adapter_full_protocol_not_neural',episode_origin_perf=origin,
        envelope=dict(method='dgft_original',budget_audio_seconds=2.,warning_age=1.,critical_age=2.,clear_age=.5,
            display_slo=2.,queue_threshold=8,reject_new_after_seconds=3.,tick_seconds=.0005),
        history_strategy=strategy,history_sealed_branches=True,history_revocation_contract='owner-mode',kernel_copy_mode='event-cow')
    workers={r:[ScriptWorker(r,r,flags,render,clock)] for r in ['proposal','authority']}
    s=ControlledScheduler(fixture_flags=flags,history_strategy=strategy,sealed_branches=True,revocation_contract='owner-mode',
        consumer=consumer,input_journal_path=D/'input.wal',sessions=[dict(session_id=0,audio=np.zeros(1280,dtype='<f4').tobytes(),source_id='SCRIPTED_CPU_0',language='English',offset=0.)],
        contract=cfg,executors=workers,emit=emit,clock=clock,sleep=time.sleep,trusted_render=render,durable_journal_path=D/'canonical.wal')
    try:
        for group in workers.values():
            for worker in group:s.execution_ready(worker)
        result=s.run();s.close();csummary=consumer.close()
    except BaseException:
        s.close()
        try:consumer.close()
        except Exception:pass
        raise
    (D/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    (D/'kernel_trace.json').write_text(json.dumps(s.kernel.trace,indent=2)+'\n')
    (D/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    (D/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    actual=[r for r in consumer.rows if r['source_kind']=='canonical-display' and r['canonical_version']==2]
    assert len(actual)==1;row=actual[0]
    expected=960 if strategy in ['latest','two-register'] else 1120
    assert row['certified_frontier']==960 and row['valid_visible_frontier']==expected
    if strategy not in ['latest','two-register']:assert row['selected_private_job_id'] in [e['job_id'] for e in events if e['kind']=='display' and e.get('window')==7]
    assert s.kernel.state.C[0]['F']==1280 and flags['new_B16_published']
    return dict(strategy=strategy,canonical_at_C2=960,actual_visible_at_C2=row['valid_visible_frontier'],
        selected_job=row.get('selected_private_job_id'),canonical_commits=result['certified_commits'],
        actual_consumer_records=csummary['records'],flags=flags,evidence='CPU scripted model; real native dispatch/Render/fsync/install/publication/kernel-gated actual FIFO Consumer; abstract6/12/14/16 are NOT measured seconds')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
    results=[]
    try:
        for strategy in ['latest','two-register','scan','mv-index','mv-index-envelope','dominance']:results.append(run(a.output,strategy))
        (a.output/'SUMMARY.json').write_text(json.dumps(dict(status='PASS_FULL_CPU_NATIVE_PROTOCOL_COUNTEREXAMPLE',results=results),indent=2)+'\n')
        print(json.dumps(results))
    except BaseException:
        import traceback
        (a.output/'STOP.json').write_text(json.dumps(dict(error=traceback.format_exc(),completed=results),indent=2)+'\n');raise
if __name__=='__main__':main()
