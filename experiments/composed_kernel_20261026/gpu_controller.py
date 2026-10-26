"""Bounded CK5 same-resource full service controller; failed cells stop stage."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,sys,time,os
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=Path(__file__).resolve().parent
O=B/'results/revtrace/dependability_20261025'/P.name
spec=importlib.util.spec_from_file_location('n5_control',P/'run_n5_validation_v2.py')
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.P=P;n.O=O
old_command=n.command
def command(E,c,m,manifest,attempt,fault):
    cmd=old_command(E,c,m,manifest,attempt,fault)
    cmd[cmd.index('--model')+1]=str(B/'models'/('whisper-small.en' if c['adapter']=='whisper' else 'Qwen3-ASR-1.7B'))
    cmd+=['--model-adapter',c['adapter'],'--recovery-readiness',c['readiness']]
    if c['kernel']:cmd+=['--protocol-kernel']
    if c.get('probe'):cmd+=['--boundary-probe',c['probe'],'--receipt-trace']
    if c.get('fault_point')=='post_sync' and attempt==0:cmd+=['--pause-post-sync-at','14']
    return cmd
n.command=command

def post_sync_episode(E,c,m,manifest,PowerSampler):
    """Same owned process-group fault, after real sync and before install."""
    E.mkdir();cfg=dict(method=c['method'],budget_audio_seconds=96,warning_age=4,critical_age=8,clear_age=2,
        display_slo=2,commit_slo=8,queue_threshold=8,reject_new_after_seconds=8,tick_seconds=.005,model_weight_sha256=n.WEIGHTS)
    n.save(E/'POLICY.json',cfg);n.save(E/'ARRIVAL.json',dict(offsets=c['offsets']))
    sampler=PowerSampler([0,1],interval=.2);sampler.start();began=time.perf_counter();proc=h=log=C=None
    try:
        cmd=command(E,c,m,manifest,0,True);n.save(E/'COMMAND_0.json',dict(cell=c,argv=cmd))
        proc,h,log,C=n.launch(cmd,E,0);deadline=time.perf_counter()+150
        while not (C/'POST_SYNC_KILL_READY.json').exists():
            if proc.poll() is not None:raise RuntimeError('owner failed before post-sync point')
            if time.perf_counter()>deadline:raise TimeoutError('post-sync point unavailable')
            time.sleep(.02)
        trigger=n.read(C/'POST_SYNC_KILL_READY.json');origin=n.read(E/'CONTEXT.json')['origin_perf']
        before=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)
        killed=n.kill_group(proc,h,C);log.close();proc=None;es=n.rows(C/'events.jsonl')
        killed.update(trigger=trigger,episode_origin_perf=origin,prekill_GPU_processes=before,
            server_input_ACKs=[e for e in es if e['kind']=='input-ack'],published_commits=[e for e in es if e['kind']=='commit'],
            clock_scope='process-group SIGKILL after durable group, before install/publication; original deadlines')
        for name in ['input.wal','canonical.wal']:
            raw=(E/name).read_bytes();(E/(name+'.pre-recovery')).write_bytes(raw)
        n.save(E/'KILL.json',killed);n.wait_own_driver_release(killed['owned_workers'])
        cmd=command(E,c,m,manifest,1,True);n.save(E/'COMMAND_1.json',dict(cell=c,argv=cmd))
        proc,h,log,C=n.launch(cmd,E,1);rc=proc.wait(timeout=390);log.close();assert rc==0
        handles=n.read(C/'OWNED_WORKER_HANDLES.json');assert not any(n.alive(w) for w in handles)
        n.wait_own_driver_release(handles);end=time.perf_counter();power=sampler.stop();sampler_old=sampler;sampler=None
        n.save(E/'EPISODE_POWER.json',dict(samples=sampler_old.rows,power_summary=power,outer_launch_perf=began,outer_end_perf=end))
        n.save(E/'RUN_COMPLETE_PENDING_AUDIT.json',dict(cell=c,source=m['code_commit'],actual_episode_end_perf=end,final_attempt=1,owned_workers=handles))
    except BaseException:
        if proc is not None and proc.poll() is None:
            if (C/'OWNED_WORKER_HANDLES.json').exists():n.kill_group(proc,h,C)
            elif n.alive(h):os.killpg(proc.pid,9);proc.wait(timeout=20)
        if log is not None:log.close()
        if sampler is not None:
            power=sampler.stop();n.save(E/'FAILED_POWER.json',dict(samples=sampler.rows,power_summary=power))
        raise

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['pilot','recovery_pilot','boundary_pilot','post_sync_pilot','normal','fault','boundary','post_sync'],required=True)
    a=ap.parse_args();assert n.idle(),'GPU belongs to another task; do not launch'
    m=n.source();sys.path.insert(0,str(P/'runtime/scripts/v100'));from run_v100_matrix import PowerSampler
    manifest=P/'INDEPENDENT_MANIFEST_v1.json'
    if a.stage=='pilot':
        cells=[dict(adapter=model,readiness=ready,kernel=ready=='early',method='standard_fair',repeat=0,
            workload='clean',load=2,offsets=[0.,.25],independent=False)
            for model in ['qwen','whisper'] for ready in ['legacy','early']]
    elif a.stage in ['boundary_pilot','boundary']:
        cells=[dict(adapter=model,readiness='early',kernel=True,method=method,repeat=rep,
            workload='controlled_interleaving',load=4,offsets=[.25*i for i in range(4)],independent=a.stage=='boundary',probe=traffic)
            for rep in range(1 if a.stage=='boundary_pilot' else 2) for model in ['qwen','whisper']
            for method in (['fine_fair'] if a.stage=='boundary_pilot' else ['fine_fair','standard_fair'])
            for traffic in ['clean','coherent']]
        # Full Standard uses the identical fine grid in this controlled probe;
        # startup/kernel/causal constraints and physical resources are shared.
        for c in cells:c['method']='fine_fair' if c['method']=='fine_fair' else 'standard_fair'
    elif a.stage in ['post_sync','post_sync_pilot']:
        cells=[dict(adapter=model,readiness='early',kernel=True,method=method,repeat=rep,
            workload='fault_recovery',fault_point='post_sync',load=4,offsets=[.25*i for i in range(4)],independent=True)
            for rep in range(1 if a.stage=='post_sync_pilot' else 2) for model in ['qwen','whisper']
            for method in (['standard_fair'] if a.stage=='post_sync_pilot' else ['dgft_original','standard_fair'])]
    elif a.stage=='recovery_pilot':
        cells=[dict(adapter=model,readiness='early',kernel=True,method='standard_fair',repeat=0,
            workload='fault_recovery',load=8,offsets=[.25*i for i in range(8)],independent=False)
            for model in ['qwen','whisper']]
    elif a.stage=='normal':
        cells=[dict(adapter=model,readiness=ready,kernel=kernel,method=method,repeat=rep,
            workload='clean',load=4,offsets=[0.,.25,.5,.75],independent=True)
            for rep in range(2) for model in ['qwen','whisper']
            for method in ['dgft_original','standard_fair'] for ready,kernel in [('legacy',False),('early',False),('early',True)]]
    else:
        cells=[dict(adapter=model,readiness=ready,kernel=kernel,method=method,repeat=rep,
            workload='fault_recovery',load=8,offsets=[.25*i for i in range(8)],independent=True)
            for rep in range(3) for model in ['qwen','whisper']
            for method in ['dgft_original','standard_fair'] for ready,kernel in [('legacy',False),('early',False),('early',True)]]
    dest=O/a.stage;dest.mkdir(parents=True,exist_ok=False)
    n.save(dest/'FREEZE.json',dict(cells=cells,expected=len(cells),source=m,
        manifest_sha256=n.sha(manifest),clock='original N5 perf origin, D=2 C=8, no restart deadline reset',
        scope='same complete N5 service; baseline wait-ready versus early fact restoration plus kernel',
        no_manuscript_edits=True))
    completed=[]
    try:
        for i,c in enumerate(cells):
            assert n.idle()
            name=f"{i:03d}-{c['adapter']}-{c['method']}-{c['readiness']}-k{int(c['kernel'])}-r{c['repeat']}"
            n.save(dest/'PROGRESS.json',dict(status='RUNNING',current=name,completed=completed,expected=len(cells)))
            model_dir=B/'models'/('whisper-small.en' if c['adapter']=='whisper' else 'Qwen3-ASR-1.7B')
            n.WEIGHTS={p.name:n.sha(p) for p in sorted(model_dir.iterdir()) if p.suffix in ['.safetensors','.bin']}
            assert n.WEIGHTS,'actual weight identity required'
            if c.get('fault_point')=='post_sync':post_sync_episode(dest/name,c,m,manifest,PowerSampler)
            else:n.episode(dest/name,c,m,manifest,PowerSampler)
            completed.append(name)
        n.save(dest/'SUMMARY.json',dict(status='COMPLETE',completed=completed,expected=len(cells)))
    except BaseException as ex:
        n.save(dest/'STOP.json',dict(error=repr(ex),completed=completed,failed=c));raise
if __name__=='__main__':main()
