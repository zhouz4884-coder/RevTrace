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
    p.add_argument("--crash-after-commits",type=int,default=0,
        help="fault harness only: pause after writing an ACK marker; parent driver must SIGKILL the owned process group")
    a=p.parse_args()
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
    proposal={**runtime,"dtype":"float16"}
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
        "evidence_type":"real_gpu_wall_clock_arrival_certified_runtime"}
    save(a.output/"config.json",config)
    save(a.output/"provenance.json",{"code_commit":a.code_commit,
        "source_sha256":{str(path.relative_to(ROOT)):file_sha(path) for path in
          [Path(__file__),ROOT/"scripts/tc_live_worker.py",ROOT/"src/revtrace/live_qwen.py",ROOT/"src/revtrace/dgft.py",ROOT/"src/revtrace/durable_journal.py"]},
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
    save(a.output/"sessions.json",[{k:v for k,v in s.items() if k!="audio"}|
        {"audio_sha256":hashlib.sha256(s["audio"]).hexdigest(),"duration":len(s["audio"])/64000}
        for s in sessions])
    workers={"proposal":[],"authority":[]}
    sampler=PowerSampler(flat,interval=.2)
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
    try:
        initialization_started=time.perf_counter()
        for role,indices in gpus.items():
            rt=runtime if role=="authority" else proposal
            for gpu in indices:
                worker=GPUExecutor(f"{role}-{gpu}",{**rt,"runtime_digest":fingerprint(rt),
                    "lifecycle_instrumentation":not a.full_diagnostic_hooks_off,
                    "capture_model_inputs":a.capture_model_inputs,
                    "delay_every":a.delay_every,"delay_offset":a.delay_offset,
                    "gpu":gpu,"model":str(a.model),"manifest":str(a.manifest),
                    "result_delay_seconds":a.proposal_result_delay if role=='proposal' else a.authority_result_delay})
                workers[role].append(worker)
        for group in workers.values():
            for worker in group:
                worker.wait_ready()
                print(json.dumps({"worker_ready":worker.name,**worker.ready}),flush=True)
        save(a.output/"workers.json",[w.ready for group in workers.values() for w in group])
        worker_initialization_seconds=time.perf_counter()-initialization_started
        sampler.start()
        with (a.output/"events.jsonl").open("w",encoding="utf-8") as trace:
            from revtrace.certified_display import RealtimeConsumer
            consumer=RealtimeConsumer(a.output/'consumer.jsonl',a.consumer_policy,strict_bound=a.trusted_text_binding)
            emitted_commits=0
            def emit(row):
                nonlocal emitted_commits
                if row['kind']=='worker-record':
                    deferred_worker_records.append(row)
                    return
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
            scheduler=LiveQwenScheduler(sessions=sessions,contract=config,executors=workers,emit=emit,
                durable_journal_path=a.durable_journal_path,trusted_render=trusted_render)
            save(a.output/"initial_states.json",[{"session_id":s.sid,"state":__import__('dataclasses').asdict(s.state)} for s in scheduler.sessions.values()])
            result=scheduler.run()
        result["consumer"]=consumer.close();consumer=None
        result["worker_initialization_seconds"]=worker_initialization_seconds
        result["journal_recovery_seconds"]=scheduler.journal_recovery_seconds
        result["power"]=sampler.stop()
        save(a.output/"power_samples.json",{"measurement_start_perf":scheduler.t0,
            "measurement_end_perf":scheduler.t0+result["wall_seconds_including_arrival_and_drain"],
            "gpu_indices":flat,"samples":sampler.rows,
            "scope":"GPU power only; host CPU power is not measured"})
        if result["power"]["samples"] < 2*len(flat) or result["power"]["energy_joules"] <= 0:
            raise RuntimeError("missing usable power samples")
        result["energy_joules_per_audio_second"]=result["power"]["energy_joules"]/result["audio_seconds"]
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
        if deferred_worker_records:
            # Captured immutable rows retain their original receipt timestamps.
            # Rich JSON serialization is outside the serving/power interval.
            with (a.output/'worker_records.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_worker_records:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if consumer is not None:consumer.close()
        if scheduler is not None:
            scheduler.close()
        for group in workers.values():
            for worker in group:
                worker.close()

if __name__=="__main__":
    raise SystemExit(main())
