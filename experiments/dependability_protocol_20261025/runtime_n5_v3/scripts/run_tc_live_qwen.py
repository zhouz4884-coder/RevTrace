"""Run one frozen arrival-driven certified Qwen cell on an allocated GPU set."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts/v100"))
from revtrace.live_qwen import LiveQwenScheduler, fingerprint
from tc_live_worker import GPUExecutor
from run_v100_matrix import PowerSampler


def save(path, value):
    tmp = path.with_suffix(path.suffix+".partial")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n",encoding="utf-8")
    tmp.replace(path)


def file_sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def close_owned_components(consumer,scheduler,workers):
    """A rejected consumer must not leak this run's own GPU processes."""
    try:
        if consumer is not None:consumer.close()
    finally:
        try:
            if scheduler is not None:scheduler.close()
        finally:
            for group in workers.values():
                for worker in group:worker.close()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--code-commit",required=True)
    p.add_argument("--study-id",default="TC-LIVE-20260906")
    p.add_argument("--mode",choices=("coarse","fine_certified","grouped_replay"),default="coarse")
    p.add_argument("--sessions",type=int,default=4)
    p.add_argument("--proposal-gpus",default="0")
    p.add_argument("--authority-gpus",default="1")
    p.add_argument("--microbatch",type=int,default=16)
    p.add_argument("--max-new-tokens",type=int,default=256)
    p.add_argument("--duration-limit",type=float,default=0)
    p.add_argument("--arrival",choices=("sync","staggered"),default="sync")
    p.add_argument("--seed",type=int,default=20260906)
    p.add_argument("--timeout",type=float,default=900)
    p.add_argument("--proposal-barrier",choices=("segment","decoupled"),default="decoupled")
    p.add_argument("--proposal-reconciliation",choices=("legacy","lazy"),default="legacy")
    p.add_argument("--publish-canonical-display",action="store_true")
    p.add_argument("--proposal-result-delay",type=float,default=0.)
    p.add_argument("--authority-result-delay",type=float,default=0.)
    p.add_argument("--trusted-text-binding",action="store_true")
    p.add_argument("--async-implementation",choices=["revtrace","standard"],default="revtrace")
    p.add_argument("--consumer-policy",choices=["snapshot","two_lane","canonical_only","localagreement2","localagreement3"],default="snapshot")
    p.add_argument('--delay-every',type=int,default=1)
    p.add_argument('--delay-offset',type=int,default=0)
    p.add_argument('--phase-n-instrumentation',action='store_true')
    p.add_argument('--capture-model-inputs',action='store_true')
    p.add_argument('--display-protocol',choices=['legacy','canonical-snapshot-v1'],default='legacy')
    p.add_argument('--full-diagnostic-hooks-off',action='store_true')
    p.add_argument("--durable-journal-path",type=Path,default=None,
        help="opt in to single-owner fsync WAL; reuse this path only to resume the same frozen contract")
    p.add_argument("--journal-sync-mode",choices=("single","group_ready"),default="single")
    p.add_argument("--verification-window",type=int,default=64)
    p.add_argument("--verification-rows",type=int,default=0,
        help="grouped authority batch size; zero follows proposer microbatch")
    p.add_argument("--grouped-speculative",action="store_true")
    p.add_argument("--retain-verified-private-prefix",action="store_true")
    p.add_argument('--online-study-method',choices=['fine','unprotected','score','strict','dgft','standard'])
    p.add_argument('--result-delivery',choices=['batch','row'],default='batch')
    p.add_argument('--receipt-trace',action='store_true',help='crash-diagnostic immutable worker receipts; not normal serving runs')
    p.add_argument('--envelope-config',type=Path)
    p.add_argument('--arrival-schedule',type=Path)
    p.add_argument('--episode-context',type=Path)
    p.add_argument('--input-journal-path',type=Path)
    p.add_argument('--post-compute-order',type=Path,help='N1 frozen diagnostic delivery intervention, no model-output edits')
    p.add_argument('--omit-receive-freshness',action='store_true',help='single-guard diagnostic ablation; not full Standard')
    p.add_argument('--online-traffic',choices=['clean','F2'],default='clean')
    p.add_argument('--online-donors',type=Path)
    p.add_argument('--online-oracle-diagnostic',action='store_true')
    p.add_argument('--online-fallback-layout',choices=['full','selective'],default='full')
    p.add_argument('--online-arrival-cohort',type=int,default=0)
    p.add_argument("--crash-after-commits",type=int,default=0,
        help="fault harness only: pause after writing an ACK marker; parent driver must SIGKILL the owned process group")
    a=p.parse_args()
    envelope=json.loads(a.envelope_config.read_text()) if a.envelope_config else None
    if envelope:
        if not all([a.arrival_schedule,a.episode_context,a.input_journal_path,a.durable_journal_path]):raise ValueError('envelope requires frozen schedule, original clock and both journals')
        if a.online_study_method or a.post_compute_order or a.omit_receive_freshness or a.crash_after_commits:raise ValueError('N5 does not mix selector/guard/IPC experiments')
        a.mode='fine_certified' if envelope['method']=='fine_fair' else 'coarse'
        a.async_implementation='standard' if envelope['method'].startswith('standard') else 'revtrace'
        a.trusted_text_binding=True;a.capture_model_inputs=True;a.consumer_policy='two_lane'
        a.proposal_reconciliation='lazy';a.proposal_barrier='decoupled'
        a.display_protocol='canonical-snapshot-v1';a.publish_canonical_display=True;a.retain_verified_private_prefix=True
        if a.result_delivery!='row':raise ValueError('N5 shares row completion across every method')
    post_order=json.loads(a.post_compute_order.read_text()) if a.post_compute_order else None
    if a.omit_receive_freshness and a.async_implementation=='standard':
        raise ValueError('full Standard must retain the freshness predicate')
    if post_order and (a.proposal_result_delay or a.authority_result_delay or a.result_delivery!='batch'):
        raise ValueError('N1 changes only delivery order after physical batch completion')
    online=None
    if a.online_study_method:
        if not a.online_donors or not a.trusted_text_binding:raise ValueError('online study requires pinned donors and D1 renderer')
        online={'schema':'online-admission-study-v1','method':a.online_study_method,'traffic':a.online_traffic,
            'score_threshold':.05,'donors':json.loads(a.online_donors.read_text())['donors'],
            'donor_file_sha256':file_sha(a.online_donors),'injection_rule':'first actual private end>=5/chunk>=2 once per session',
            'oracle_diagnostic':a.online_oracle_diagnostic,'unsafe_negative_contract':a.online_study_method=='unprotected'}
        online['fallback_layout']=a.online_fallback_layout
        online['arrival_cohort']=a.online_arrival_cohort
        a.mode='coarse' if a.online_study_method in ['dgft','standard'] else 'fine_certified'
        a.async_implementation='standard' if a.online_study_method=='standard' else 'revtrace'
        a.proposal_reconciliation='lazy';a.proposal_barrier='decoupled'
        a.display_protocol='canonical-snapshot-v1';a.publish_canonical_display=True
    if a.output.exists():
        raise FileExistsError("unique experiment output required")
    a.output.mkdir(parents=True)
    import numpy as np
    import soundfile as sf
    manifest=json.loads(a.manifest.read_text())
    if a.sessions<1 or not manifest["sessions"]:
        raise ValueError("nonempty session set required")
    gpus={"proposal":[int(x) for x in a.proposal_gpus.split(",")],
          "authority":[int(x) for x in a.authority_gpus.split(",")]}
    flat=gpus["proposal"]+gpus["authority"]
    if len(set(flat))!=len(flat):
        raise ValueError("workers must own disjoint physical GPUs")
    hardware=subprocess.check_output(["nvidia-smi","--query-gpu=index,name,uuid,driver_version,memory.total","--format=csv,noheader"],text=True)
    software={name:importlib.metadata.version(name) for name in ("torch","transformers","qwen-asr")}
    runtime={"model":a.model.name,"model_config_sha256":file_sha(a.model/"config.json"),
             "warmup_policy":"synthetic-zero-audio-not-a-serving-input",
             "hardware_fingerprint":hashlib.sha256(hardware.encode()).hexdigest(),
             "software":software,
             "backend":"transformers-eager", "dtype":"float32",
             "microbatch":a.microbatch,"max_new_tokens":a.max_new_tokens,
             "rollback_tokens":5,"unfixed_chunks":2,"code_commit":a.code_commit}
    if a.trusted_text_binding:
        import inspect
        from transformers import AutoProcessor,GenerationConfig
        from qwen_asr import parse_asr_output
        renderer_processor=AutoProcessor.from_pretrained(a.model,local_files_only=True)
        render_assets={p.name:file_sha(p) for p in sorted(a.model.iterdir()) if p.is_file() and p.suffix in ('.json','.txt','.py','.tiktoken','.model')}
        runtime['render_contract']={'adapter':'qwen-text-rollback5-unfixed2-v1','assets':render_assets,
            'parse_source_sha256':hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest(),
            'processor_source_sha256':file_sha(Path(inspect.getfile(type(renderer_processor)))),
            'tokenizers_version':importlib.metadata.version('tokenizers'),'published_text_encoding':'UTF-8 byte exact'}
    runtime['row_delivery']=a.result_delivery
    if a.result_delivery=='row' and (not a.trusted_text_binding or not a.capture_model_inputs):
        raise ValueError('row delivery requires trusted Render and actual input capture')
    if a.result_delivery=='row' and a.mode=='grouped_replay':
        raise ValueError('legacy grouped replay is outside the five-policy row-completion study')
    proposal={**runtime,"dtype":"float16"}
    if online:
        runtime['online_selection_mode']=a.online_study_method if a.online_study_method in ['unprotected','score','strict'] else None
        runtime['score_threshold']=online['score_threshold'];runtime['online_oracle_diagnostic']=a.online_oracle_diagnostic
        runtime['fallback_layout']=a.online_fallback_layout
        proposal['allow_execution_context_override']=a.online_traffic=='F2'
        proposal['F2_field_normalization']='declared-parent reconstruction of actual GPU-generated Z; no new generation'
    if a.mode == "grouped_replay":
        runtime["verification_policy"] = "grouped_replay"
        runtime["verification_rows"] = a.verification_rows or a.microbatch
        runtime["verification_tokens"] = a.verification_window
        a.proposal_barrier = "decoupled" if a.grouped_speculative else "segment"
    config={"study":a.study_id, "policy":a.mode,"rho":3 if a.mode=="coarse" else 1,
        "fine_seconds":2,"sample_rate":16000,"authority_runtime":runtime,
        "proposal_runtime":proposal,"microbatch":a.microbatch,"seed":a.seed,
        "arrival":a.arrival,"duration_limit":a.duration_limit,"replicas":gpus,
        "proposal_barrier":a.proposal_barrier,
        "proposal_reconciliation":a.proposal_reconciliation,
        "publish_canonical_display":a.publish_canonical_display,
        "proposal_result_delay_seconds":a.proposal_result_delay,
        "authority_result_delay_seconds":a.authority_result_delay,
        "trusted_text_binding":a.trusted_text_binding,
        "async_implementation":a.async_implementation,
        "arrival_stagger_step_seconds":0.25,
        "consumer_policy":a.consumer_policy,
        "delay_every":a.delay_every,"delay_offset":a.delay_offset,
        "display_protocol":a.display_protocol,
        "blocking_instrumentation":a.phase_n_instrumentation,
        "capture_worker_records":a.capture_model_inputs,
        "diagnostic_lifecycle":not a.full_diagnostic_hooks_off,
        "verification_policy":"grouped_replay" if a.mode=="grouped_replay" else "canonical_generate",
        "grouped_speculative":a.grouped_speculative,
        "retain_verified_private_prefix":a.retain_verified_private_prefix,
        "authority_microbatch":(a.verification_rows or a.microbatch) if a.mode=="grouped_replay" else a.microbatch,
        "durability_mode":"wal" if a.durable_journal_path else "volatile",
        "journal_mode":"durable" if a.durable_journal_path else "volatile",
        "journal_sync_mode":a.journal_sync_mode,
        "manifest_sha256":file_sha(a.manifest),"timeout_seconds":a.timeout,
        "evidence_type":"real_gpu_wall_clock_arrival_certified_runtime",
        "result_delivery":a.result_delivery}
    config['diagnostic_receipt_trace']=a.receipt_trace
    config['post_compute_order']=post_order
    config['diagnostic_omit_receive_freshness']=a.omit_receive_freshness
    if envelope:
        config['envelope']=envelope
        config['arrival_schedule_sha256']=file_sha(a.arrival_schedule)
    if online:
        config['online_study']=online
        if a.online_study_method in ['unprotected','score','strict']:
            config['verification_policy']='online_'+a.online_study_method
    save(a.output/"config.json",config)
    measured_sources=[Path(__file__),ROOT/"scripts/tc_live_worker.py",ROOT/"src/revtrace/live_qwen.py",ROOT/"src/revtrace/dgft.py",ROOT/"src/revtrace/durable_journal.py",
           ROOT/'scripts/row_delivery_worker.py',ROOT/'scripts/row_delivery_executor.py',ROOT/'src/revtrace/row_lifecycle.py',ROOT/'src/revtrace/row_stream.py']
    if envelope:measured_sources += [ROOT/'src/revtrace'/n for n in ['certified_envelope.py','degradation_state.py','input_debt_journal.py','envelope_display.py','certified_display.py']]
    save(a.output/"provenance.json",{"code_commit":a.code_commit,
        "source_sha256":{str(path.relative_to(ROOT)):file_sha(path) for path in measured_sources},
        "hostname":platform.node(),"python":sys.version,"platform":platform.platform(),
        "pbs_jobid":os.environ.get("PBS_JOBID"),"manifest_sha256":file_sha(a.manifest),
        "gpus":hardware,"software":software,
        "durability_mode":config["durability_mode"],
        "journal_mode":config["journal_mode"],
        "journal_sync_mode":config["journal_sync_mode"],
        "durable_journal_path":str(a.durable_journal_path.resolve()) if a.durable_journal_path else None})
    sessions=[]
    rng=random.Random(a.seed)
    for sid in range(a.sessions):
        row=manifest["sessions"][sid%len(manifest["sessions"])]
        source=Path(row["path"])
        if not source.is_file():
            source=a.manifest.parent/source.name
        audio,rate=sf.read(source,dtype="float32")
        if rate!=16000 or audio.ndim!=1:
            raise ValueError("manifest requires prepared mono 16k audio")
        audio=np.asarray(audio,dtype="<f4")
        if hashlib.sha256(audio.tobytes()).hexdigest()!=row["audio_sha256"]:
            raise ValueError("prepared audio checksum mismatch")
        if a.duration_limit:
            audio=audio[:int(a.duration_limit*rate)]
        sessions.append({"session_id":sid,"audio":audio.tobytes(),"source_id":row["source_id"],
            "language":row["language"],"offset":0.0 if a.arrival=="sync" else sid*0.25})
        if online and a.online_arrival_cohort:
            from revtrace.online_admission import cohort_offset
            sessions[-1]['offset']=cohort_offset(sid,a.online_arrival_cohort)
    save(a.output/"sessions.json",[{k:v for k,v in s.items() if k!="audio"}|
        {"audio_sha256":hashlib.sha256(s["audio"]).hexdigest(),"duration":len(s["audio"])/64000}
        for s in sessions])
    workers={"proposal":[],"authority":[]}
    class ExternalEpisodePower:
        rows=[]
        def start(self):pass
        def stop(self):return dict(samples=0,energy_joules=None,scope='outer episode sampler; no child estimate')
    sampler=ExternalEpisodePower() if envelope else PowerSampler(flat,interval=.2)
    scheduler=None
    consumer=None
    trusted_render=None
    if a.trusted_text_binding:
        from transformers import AutoProcessor,GenerationConfig
        from qwen_asr import parse_asr_output
        from revtrace.certified_display import TrustedQwenRender
        processor=AutoProcessor.from_pretrained(a.model,local_files_only=True)
        eos=GenerationConfig.from_pretrained(a.model,local_files_only=True).eos_token_id
        trusted_render=TrustedQwenRender(processor.tokenizer,parse_asr_output,[eos] if isinstance(eos,int) else eos,a.max_new_tokens)
    result=None
    deferred_worker_records=[]
    deferred_batch_accounting=[]
    deferred_ipc_payloads=[]
    try:
        initialization_started=time.perf_counter()
        for role,indices in gpus.items():
            rt=runtime if role=="authority" else proposal
            for gpu in indices:
                executor_type=GPUExecutor
                if a.result_delivery=='row':
                    from row_delivery_executor import RowGPUExecutor
                    executor_type=RowGPUExecutor
                worker=executor_type(f"{role}-{gpu}",{**rt,"runtime_digest":fingerprint(rt),
                    "lifecycle_instrumentation":not a.full_diagnostic_hooks_off,
                    "capture_model_inputs":a.capture_model_inputs,
                    "delay_every":a.delay_every,"delay_offset":a.delay_offset,
                    "gpu":gpu,"model":str(a.model),"manifest":str(a.manifest),
                    "receipt_trace_path":str(a.output/f'worker-{role}-{gpu}-receipts.jsonl') if a.receipt_trace else None,
                    "result_delay_seconds":a.proposal_result_delay if role=='proposal' else a.authority_result_delay})
                workers[role].append(worker)
        for group in workers.values():
            for worker in group:
                worker.wait_ready()
                print(json.dumps({"worker_ready":worker.name,**worker.ready}),flush=True)
        handles=[]
        for group in workers.values():
            for w in group:
                proc=Path('/proc')/str(w.process.pid)
                handles.append({'pid':w.process.pid,'name':w.name,'parent_pid':os.getpid(),
                  'worker_incarnation':getattr(w,'incarnation',None),
                  'linux_start_ticks':proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19] if proc.exists() else None,
                  'command_sha256':file_sha(proc/'cmdline') if proc.exists() else None})
        save(a.output/'OWNED_WORKER_HANDLES.json',handles)
        save(a.output/"workers.json",[w.ready for group in workers.values() for w in group])
        worker_initialization_seconds=time.perf_counter()-initialization_started
        if envelope:
            schedule=json.loads(a.arrival_schedule.read_text())
            offsets=schedule['offsets']
            if len(offsets)!=len(sessions) or any(float(x)<0 for x in offsets):raise ValueError('frozen nonnegative arrival offsets')
            for sid,s in enumerate(sessions):s['offset']=float(offsets[sid])
            save(a.output/'sessions.json',[{k:v for k,v in s.items() if k!='audio'}|{'audio_sha256':hashlib.sha256(s['audio']).hexdigest(),'duration':len(s['audio'])/64000} for s in sessions])
            context_identity=dict(source_commit=a.code_commit,manifest_sha256=file_sha(a.manifest),
                schedule_sha256=file_sha(a.arrival_schedule),envelope_sha256=file_sha(a.envelope_config))
            if a.episode_context.exists():
                context=json.loads(a.episode_context.read_text())
                if context['identity']!=context_identity:raise ValueError('restart changed frozen episode identity')
            else:
                context=dict(identity=context_identity,origin_perf=time.perf_counter())
                a.episode_context.parent.mkdir(parents=True,exist_ok=True)
                with a.episode_context.open('x',encoding='utf8') as f:
                    json.dump(context,f);f.flush();os.fsync(f.fileno())
            config['episode_origin_perf']=context['origin_perf']
            save(a.output/'config.json',config)
            save(a.output/'episode_context.json',context)
        sampler.start()
        if online:time.sleep(.25)  # Sampling padding, outside serving clock.
        with (a.output/"events.jsonl").open("w",encoding="utf-8") as trace:
            from revtrace.certified_display import RealtimeConsumer
            if envelope:
                from revtrace.envelope_display import EnvelopeView
                consumer=RealtimeConsumer(a.output/'consumer.jsonl',a.consumer_policy,strict_bound=True,
                    view=EnvelopeView(policy='two_lane',strict_bound=True,fine_samples=32000),
                    crash_trace_path=a.output/'consumer-live.jsonl' if a.receipt_trace else None)
            else:consumer=RealtimeConsumer(a.output/'consumer.jsonl',a.consumer_policy,strict_bound=a.trusted_text_binding)
            emitted_commits=0
            def emit(row):
                nonlocal emitted_commits
                if row['kind']=='ipc-complete-payload':
                    deferred_ipc_payloads.append(row)
                    return
                if row['kind']=='worker-record':
                    deferred_worker_records.append(row)
                    return
                if row['kind']=='worker-status' and row.get('status')=='batch-accounting':
                    deferred_batch_accounting.append(row)
                    return # Same deferred-rich-log convention as worker-records.
                trace.write(json.dumps(row,allow_nan=False)+"\n")
                trace.flush()
                consumer.put(row)
                if row["kind"]=="commit":
                    emitted_commits+=1
                    if a.crash_after_commits and emitted_commits==a.crash_after_commits:
                        os.fsync(trace.fileno())
                        marker=a.output/"ACK_FOR_KILL.json"
                        with marker.open("w",encoding="utf-8") as stream:
                            json.dump(row,stream);stream.flush();os.fsync(stream.fileno())
                        print("ACK_FOR_KILL_READY",flush=True)
                        while True:
                            time.sleep(.1)  # Injection harness kills, no clean close.
            scheduler_type=LiveQwenScheduler
            if post_order or a.omit_receive_freshness:
                from revtrace.late_delivery import LateDeliveryScheduler
                scheduler_type=LateDeliveryScheduler
            if online:
                from revtrace.online_admission import OnlineAdmissionScheduler
                scheduler_type=OnlineAdmissionScheduler
            scheduler_arguments=dict(sessions=sessions,contract=config,executors=workers,emit=emit,
                durable_journal_path=a.durable_journal_path,trusted_render=trusted_render)
            if envelope:
                from revtrace.certified_envelope import CertifiedEnvelopeScheduler
                scheduler_type=CertifiedEnvelopeScheduler
                scheduler_arguments.update(consumer=consumer,input_journal_path=a.input_journal_path)
            scheduler=scheduler_type(**scheduler_arguments)
            save(a.output/"initial_states.json",[{"session_id":s.sid,"state":__import__('dataclasses').asdict(s.state)} for s in scheduler.sessions.values()])
            result=scheduler.run()
        result["consumer"]=consumer.close()
        result['actual_consumer_last_application_seconds']=max((r['observed'] for r in consumer.rows),default=0.)
        result['wall_seconds_including_arrival_and_drain']=max(result['wall_seconds_including_arrival_and_drain'],result['actual_consumer_last_application_seconds'])
        consumer=None
        result["worker_initialization_seconds"]=worker_initialization_seconds
        result["journal_recovery_seconds"]=scheduler.journal_recovery_seconds
        if online:time.sleep(.25)  # Enclose strict serving window for integration.
        result["power"]=sampler.stop()
        save(a.output/"power_samples.json",{"measurement_start_perf":scheduler.t0,
            "measurement_end_perf":scheduler.t0+result["wall_seconds_including_arrival_and_drain"],
            "gpu_indices":flat,"samples":sampler.rows,
            "scope":"GPU power only; host CPU power is not measured"})
        if not envelope and (result["power"]["samples"] < 2*len(flat) or result["power"]["energy_joules"] <= 0):
            raise RuntimeError("missing usable power samples")
        result["energy_joules_per_audio_second"]=None if envelope else result["power"]["energy_joules"]/result["audio_seconds"]
        result["journal_mode"]=config["journal_mode"]
        result["decision"]="PASS_PROTOCOL_COMPLETENESS" if result["token_limit_events"]==0 else "TOKEN_LIMIT_BOUNDARY"
        result["display_p99_2s_pass"]=result["display_p99_seconds"]<=2
        save(a.output/"result.json",result)
        print(json.dumps({k:v for k,v in result.items() if k not in ("final_states","power")}),flush=True)
        return 0
    except BaseException as exc:
        sampler.stop()
        save(a.output/"failure.json",{"error":repr(exc),"type":type(exc).__name__})
        raise
    finally:
        if deferred_ipc_payloads:
            with (a.output/'ipc_completed_payloads.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_ipc_payloads:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if deferred_worker_records:
            # Captured immutable rows retain their original receipt timestamps.
            # Rich JSON serialization is outside the serving/power interval.
            with (a.output/'worker_records.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_worker_records:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if deferred_batch_accounting:
            with (a.output/'worker_batch_accounting.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_batch_accounting:stream.write(json.dumps(row,allow_nan=False)+'\n')
        close_owned_components(consumer,scheduler,workers)

if __name__=="__main__":
    raise SystemExit(main())
