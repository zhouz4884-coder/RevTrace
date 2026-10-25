"""CPU real-code data-flow/role gate; deliberately NOT a GPU attack result."""
from pathlib import Path
from dataclasses import replace
import hashlib,importlib.util,json,sys
W=Path(__file__).resolve().parents[1];R=W/'runtime'
sys.path.insert(0,str(R/'src'))
from revtrace.live_qwen import LiveQwenScheduler
from revtrace.row_lifecycle import RowBinding,RowComplete,BatchDrained,RowInbox,digest
sp=importlib.util.spec_from_file_location('route_fixture',R/'tests/test_live_qwen.py')
f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f)
MARKER=[9001,9002,9003]

def run(mode):
    clock=f.Clock();client=[];transforms=[]
    class BoundWorker(f.Fake):
        def __init__(self,name,*args):
            super().__init__(name,*args);self.counter=0;self.inbox=RowInbox(name,'cpu-role-'+name)
        def submit(self,jobs):
            self.counter+=1;self.current={j['job_id']:j for j in jobs};self.bindings=[]
            for j in jobs:
                self.bindings.append(RowBinding(self.name,'cpu-role-'+self.name,str(self.counter),j['job_id'],j['session_id'],j['role'],j['parent'],
                    j['contract_epoch'],j['contract_digest'],j['runtime_digest'],j['audio_start_sample'],j['audio_end_sample'],
                    j['interval_audio_sha256'],digest({k:j.get(k) for k in ['session_id','source_id','role','parent','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','fault_actual_prompt_tokens']})))
            self.inbox.begin(str(self.counter),self.bindings);super().submit(jobs)
        def poll(self):
            rows=super().poll()
            if rows is None:return None
            seen={};out=[]
            for binding,r in zip(self.bindings,rows):
                j=self.current[r['job_id']];r['token_ids']=list(r['state_tokens']);r['text']=' '.join(map(str,r['token_ids']))
                if self.name=='p' and j['end_window']==5:
                    original=dict(r)
                    if mode=='worker_text_only':r['text']='CPU LOW TRUST MARKER'
                    if mode=='coherent_proposer':
                        r.update(token_ids=list(MARKER),state_tokens=list(MARKER),text=' '.join(map(str,MARKER)),generated_tokens=len(MARKER))
                    if mode=='role_spoof':binding=replace(binding,role='authority')
                    transforms.append(dict(job_id=j['job_id'],mode=mode,original=original,received=dict(r)))
                msg=RowComplete.seal(binding,r,terminal=clock(),rendered=clock(),emitted=clock())
                kind,decoded=self.inbox.receive(msg);assert kind=='new-complete'
                seen[j['job_id']]=msg.payload_digest;out.append(decoded)
            self.inbox.drain(BatchDrained(self.name,'cpu-role-'+self.name,str(self.counter),tuple(seen.items()),clock()))
            return out
    cfg=dict(policy='coarse',rho=3,fine_seconds=.01,sample_rate=16000,
        authority_runtime={'dtype':'float32'},proposal_runtime={'dtype':'float16'},
        microbatch=1,timeout_seconds=3,proposal_barrier='decoupled',proposal_reconciliation='lazy',
        trusted_text_binding=True,capture_worker_records=True,display_protocol='canonical-snapshot-v1',
        retain_verified_private_prefix=True,evidence_type='cpu_simulated_orchestration_only')
    def emit(e):
        if e['kind']=='display':
            copied=json.loads(json.dumps(e))
            if mode=='client_y':copied['text']='CPU CLIENT DISPLAY MARKER'
            client.append(copied)
    s=LiveQwenScheduler(sessions=[dict(session_id=0,audio=bytes(1920*4),source_id='CPU_ONLY',language='English',offset=0)],
        contract=cfg,executors={'proposal':[BoundWorker('p',clock,.001)],'authority':[BoundWorker('a',clock,.04)]},
        clock=clock,sleep=clock.sleep,emit=emit,trusted_render=lambda j,Z:(list(Z),' '.join(map(str,Z))))
    error=None
    try:s.run()
    except ValueError as e:error=str(e)
    finally:s.close()
    jobs=list(s.jobs.values());future=[j for j in jobs if j['role']=='proposal' and j['end_window']>5 and j['prompt_tokens']==MARKER]
    authority=[j for j in jobs if j['role']=='authority' and j['prompt_tokens']==MARKER]
    return dict(mode=mode,error=error,transforms=transforms,
        future_private_marker_inputs=[j['job_id'] for j in future],future_authority_marker_inputs=[j['job_id'] for j in authority],
        history=[{k:e[k] for k in ['session_id','parent','audio_start_sample','audio_end_sample','segment_tokens','next_prompt_tokens']} for e in s.events if e['kind']=='commit'],
        client_marker_shown=any('CPU CLIENT' in r['text'] for r in client),
        actor_generated_marker_claim=False,neural_GPU_calls=0)

if __name__=='__main__':
    all_runs=[]
    for repeat in range(3):
        batch={mode:run(mode) for mode in ['clean','client_y','worker_text_only','coherent_proposer','role_spoof']}
        assert batch['client_y']['client_marker_shown'] and not batch['client_y']['future_private_marker_inputs']
        assert batch['worker_text_only']['error']=='trusted render text mismatch'
        assert batch['role_spoof']['error'] and 'binding' in batch['role_spoof']['error']
        assert batch['coherent_proposer']['future_private_marker_inputs']
        assert not batch['coherent_proposer']['future_authority_marker_inputs']
        assert batch['clean']['history']==batch['client_y']['history']==batch['coherent_proposer']['history']
        all_runs.extend([dict(repeat=repeat,**r) for r in batch.values()])
    out=dict(status='GO_ROLE_RESTRICTED_PRIVATE_FEEDBACK_PATH_CPU_ONLY',runs=all_runs,
        scope='actual frozen f0e5864 owner/RowInbox/renderer data flow with symbolic CPU executors; no neural emission/ASR/remote attack or OS isolation claim',
        capability='only own Proposer result before sealing; original frozen job/role/context binding and trusted Authority remain unchanged',
        client_display_only='NO_GO_NO_SERVER_PROMPT_ROUTE',
        protected_canonical_write='NO_GO_UNDER_THIS_CAPABILITY_AND_INDEPENDENT_AUTHORITY',
        next_gate='frozen benign entity and existing fine candidate controls, actual GPU future processed-input consumption; separate private and canonical outcomes')
    (W/'adversarial/ROUTE_PROBE_v1.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='runs'}))
