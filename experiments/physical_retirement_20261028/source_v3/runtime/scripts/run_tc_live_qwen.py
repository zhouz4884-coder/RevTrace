"""Run one frozen arrival-driven certified Qwen cell on an allocated GPU set."""
from __future__ import annotations
import time
_PROCESS_ENTRY_PERF=time.perf_counter()
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts/v100"))
_RUNTIME_IMPORT_START=time.perf_counter()
from revtrace.live_qwen import LiveQwenScheduler, fingerprint
from tc_live_worker import GPUExecutor
from run_v100_matrix import PowerSampler
from revtrace.recovery_profile import RecoveryProfile,recovery_processor
from revtrace.recovery_fault import parse_post_sync_target,target_in_synced_group
from revtrace.startup_overlap import (verify_prefrozen_renderer,load_native_qwen_context,
    require_loaded_renderer_match,bootstrap_renderer_and_workers)
_RUNTIME_IMPORT_END=time.perf_counter()


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
    p.add_argument("--consumer-policy",choices=["snapshot","checked_snapshot","two_lane","canonical_only","localagreement2","localagreement3"],default="snapshot")
    p.add_argument('--confirmation-consumer',choices=['checked_snapshot','two_lane'],default='two_lane')
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
    p.add_argument('--recovery-readiness',choices=['legacy','early'],default='early')
    p.add_argument('--startup-processor-mode',choices=['legacy_double','reuse'],default='reuse')
    p.add_argument('--startup-order',choices=['full_first','descriptor_workers_first'],default='full_first')
    p.add_argument('--render-descriptor',type=Path)
    p.add_argument('--render-descriptor-sha256')
    p.add_argument('--render-program-bundle',type=Path)
    p.add_argument('--render-program-sha256')
    p.add_argument('--render-use-manifest',type=Path)
    p.add_argument('--render-use-sha256')
    p.add_argument('--owner-render-backend',choices=['native','light'],default='native')
    p.add_argument('--protocol-kernel',action='store_true')
    p.add_argument('--physical-retirement',choices=['row_complete','no_cancel','watchdog','parent','covered','causal'])
    p.add_argument('--retirement-watchdog-seconds',type=float,default=2.)
    p.add_argument('--retirement-fault-fixture',type=Path)
    p.add_argument('--disable-private-retention',action='store_true')
    p.add_argument('--study-authority-rho',type=int,choices=[1,3])
    p.add_argument('--prefix-executor-mode',choices=['fresh','strict-full','prefix','revtrace-prefix'])
    p.add_argument('--authority-rho',type=int,choices=[1,3])
    p.add_argument('--dispatch-wait-config',type=Path)
    p.add_argument('--dispatch-wait-prior',type=Path)
    p.add_argument('--dispatch-wait-prior-sha256')
    p.add_argument('--wait-study-rho',type=int,choices=[1,3])
    p.add_argument('--history-selector',choices=['latest','scan','mv-index','mv-index-envelope','dominance'],default='latest')
    p.add_argument('--kernel-copy-mode',choices=['deep','event-cow'],default='deep')
    p.add_argument('--model-adapter',choices=['qwen','whisper'],default='qwen')
    p.add_argument('--whisper-context-policy',choices=['unbounded-native-v1','reserve-generation-tail-v1'],default='unbounded-native-v1')
    p.add_argument('--boundary-probe',choices=['clean','coherent'])
    p.add_argument('--pause-post-sync-at',type=float,default=0.)
    p.add_argument('--pause-post-sync-target',help='fault-harness session:sample_frontier, after real WAL sync before owner install')
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
    if a.model_adapter!='whisper' and a.whisper_context_policy!='unbounded-native-v1':
        raise ValueError('Whisper conditioning policy cannot change the Qwen contract')
    logical_fault_target=parse_post_sync_target(a.pause_post_sync_target)
    if logical_fault_target is not None and a.pause_post_sync_at:
        raise ValueError('select exactly one logical or time-based post-sync fault')
    if logical_fault_target is not None and (not a.envelope_config or not a.protocol_kernel):
        raise ValueError('logical post-sync fault requires the complete kernel/envelope run')
    early_recovery=(a.recovery_readiness=='early' and a.episode_context is not None
        and a.episode_context.exists())
    envelope=json.loads(a.envelope_config.read_text()) if a.envelope_config else None
    retirement_fixture=json.loads(a.retirement_fault_fixture.read_text()) if a.retirement_fault_fixture else None
    if a.confirmation_consumer=='checked_snapshot' and not (a.physical_retirement and envelope and a.protocol_kernel and a.result_delivery=='row'):
        raise ValueError('checked snapshot confirmation requires complete row/kernel/input-WAL carrier')
    if a.physical_retirement:
        if not envelope or not a.protocol_kernel or a.result_delivery!='row' or not a.trusted_text_binding or not a.capture_model_inputs:
            raise ValueError('physical retirement requires complete row/kernel/D1/input-Consumer carrier')
        if a.dispatch_wait_config or a.prefix_executor_mode or a.history_selector!='latest' or a.boundary_probe:
            raise ValueError('retirement does not mix waiting, prefix reuse or historical-selector branches')
        if a.retirement_watchdog_seconds<=0:raise ValueError('positive frozen watchdog threshold required')
        if a.model_adapter!='qwen' and a.physical_retirement!='row_complete':
            raise ValueError('physical exit prototype is Qwen only; ordinary Whisper is a confirmation control')
    if retirement_fixture and (not a.physical_retirement or a.model_adapter!='qwen'):
        raise ValueError('input fault fixture requires Qwen retirement study')
    if envelope:
        if not all([a.arrival_schedule,a.episode_context,a.input_journal_path,a.durable_journal_path]):raise ValueError('envelope requires frozen schedule, original clock and both journals')
        if a.online_study_method or a.post_compute_order or a.omit_receive_freshness or a.crash_after_commits:raise ValueError('N5 does not mix selector/guard/IPC experiments')
        a.mode='fine_certified' if envelope['method']=='fine_fair' else 'coarse'
        if a.boundary_probe:
            if not a.protocol_kernel:raise ValueError('controlled probe requires the real common kernel')
            a.mode='fine_certified'  # identical fine grid for complete Standard
        a.async_implementation='standard' if envelope['method'].startswith('standard') else 'revtrace'
        a.trusted_text_binding=True;a.capture_model_inputs=True;a.consumer_policy=a.confirmation_consumer
        a.proposal_reconciliation='lazy';a.proposal_barrier='decoupled'
        a.display_protocol='canonical-snapshot-v1';a.publish_canonical_display=True;a.retain_verified_private_prefix=True
        if a.result_delivery!='row':raise ValueError('N5 shares row completion across every method')
    if a.study_authority_rho is not None:
        if not a.physical_retirement:raise ValueError('study rho requires the explicit retirement/confirmation contract')
        a.mode='fine_certified' if a.study_authority_rho==1 else 'coarse'
    if a.authority_rho is not None:
        if not a.prefix_executor_mode:raise ValueError('LP1 fixed rho override requires shared prefix study')
        a.mode='fine_certified' if a.authority_rho==1 else 'coarse'
    dispatch_wait=json.loads(a.dispatch_wait_config.read_text()) if a.dispatch_wait_config else None
    if dispatch_wait is not None:
        if not a.envelope_config or not a.protocol_kernel or a.result_delivery!='row' or a.online_study_method or a.post_compute_order or a.omit_receive_freshness:
            raise ValueError('dispatch waiting requires complete shared row/kernel/input-WAL service')
        from revtrace.dispatch_wait import DispatchWaitController
        dispatch_wait=dict(DispatchWaitController(dispatch_wait).config)
    if a.wait_study_rho is not None:
        if dispatch_wait is None or a.prefix_executor_mode:raise ValueError('wait study fixed rho uses original full-row backend; prefix remains batch1-only')
        a.mode='fine_certified' if a.wait_study_rho==1 else 'coarse'
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
    if a.disable_private_retention:a.retain_verified_private_prefix=False
    if bool(a.render_descriptor)!=bool(a.render_descriptor_sha256):
        raise ValueError('renderer descriptor path and pre-frozen SHA256 must be supplied together')
    render_program=all([a.render_program_bundle,a.render_program_sha256,a.render_use_manifest,a.render_use_sha256])
    if any([a.render_program_bundle,a.render_program_sha256,a.render_use_manifest,a.render_use_sha256]) and not render_program:
        raise ValueError('complete declared render program/use identities required')
    if (render_program or a.owner_render_backend!='native') and (not a.render_descriptor or not a.trusted_text_binding or a.model_adapter!='qwen'):
        raise ValueError('equivalent owner renderer requires pinned Qwen reference and D1')
    if a.owner_render_backend=='light' and not render_program:raise ValueError('light renderer is not allowed by this contract')
    if a.owner_render_backend=='light' and a.startup_processor_mode!='reuse':raise ValueError('light owner renderer has no legacy double-processor loading path')
    if a.render_descriptor and (not a.trusted_text_binding or a.model_adapter!='qwen'):
        raise ValueError('prefrozen descriptor is scoped to trusted Qwen renderer')
    if a.startup_order=='descriptor_workers_first' and not a.render_descriptor:
        raise ValueError('workers-first startup requires externally frozen renderer descriptor')
    if a.output.exists():
        raise FileExistsError("unique experiment output required")
    a.output.mkdir(parents=True)
    startup_profile=RecoveryProfile(a.output/"startup_profile.jsonl",process_entry_perf=_PROCESS_ENTRY_PERF,processor_mode=a.startup_processor_mode)
    startup_profile.mark("owner-runtime-imports",started_perf=_RUNTIME_IMPORT_START,observed_perf=_RUNTIME_IMPORT_END,elapsed_seconds=_RUNTIME_IMPORT_END-_RUNTIME_IMPORT_START)
    save(a.output/"initialization.json",dict(startup_processor_mode=a.startup_processor_mode,
        startup_order=a.startup_order,render_descriptor_sha256=a.render_descriptor_sha256,
        owner_render_backend=a.owner_render_backend,render_program_sha256=a.render_program_sha256,render_use_sha256=a.render_use_sha256,
        render_descriptor=str(a.render_descriptor) if a.render_descriptor else None,
        code_commit=a.code_commit,scope="initialization implementation; unchanged render/selection contract"))
    _phase=startup_profile.begin("audio-library-imports")
    import numpy as np
    import soundfile as sf
    startup_profile.end(_phase)
    manifest=json.loads(a.manifest.read_text())
    if a.sessions<1 or not manifest["sessions"]:
        raise ValueError("nonempty session set required")
    gpus={"proposal":[int(x) for x in a.proposal_gpus.split(",")],
          "authority":[int(x) for x in a.authority_gpus.split(",")]}
    flat=gpus["proposal"]+gpus["authority"]
    if len(set(flat))!=len(flat):
        raise ValueError("workers must own disjoint physical GPUs")
    _phase=startup_profile.begin("hardware-software-identity")
    hardware=subprocess.check_output(["nvidia-smi","--query-gpu=index,name,uuid,driver_version,memory.total","--format=csv,noheader"],text=True)
    software={name:importlib.metadata.version(name) for name in ("torch","transformers","qwen-asr")}
    startup_profile.end(_phase)
    _phase=startup_profile.begin("model-config-identity")
    runtime={"model":a.model.name,"model_config_sha256":file_sha(a.model/"config.json"),
             "warmup_policy":"synthetic-zero-audio-not-a-serving-input",
             "hardware_fingerprint":hashlib.sha256(hardware.encode()).hexdigest(),
             "software":software,
             "backend":"transformers-eager", "dtype":"float32",
             "microbatch":a.microbatch,"max_new_tokens":a.max_new_tokens,
             "rollback_tokens":5,"unfixed_chunks":2,"code_commit":a.code_commit}
    startup_profile.end(_phase)
    runtime['model_adapter']=a.model_adapter
    if a.model_adapter=='whisper':
        from revtrace.whisper_adapter import whisper_conditioning_config
        conditioning=whisper_conditioning_config(a.model,a.whisper_context_policy)
        runtime.update(rollback_tokens=0,unfixed_chunks=0,
            feedback_route='cumulative text -> declared conditioning view -> get_prompt_ids; actual next contiguous interval',
            whisper_context_policy=a.whisper_context_policy,whisper_conditioning=conditioning)
        runtime['render_contract']={'adapter':'whisper-get_prompt_ids-v1',
            'conditioning':conditioning,
            'assets':{p.name:file_sha(p) for p in sorted(a.model.iterdir()) if p.is_file() and p.suffix in ('.json','.txt')}}
    render_context=None
    declared_renderer=None
    if a.render_descriptor:
        with startup_profile.span('prefrozen-render-identity-validation'):
            declared_renderer=verify_prefrozen_renderer(a.model,a.render_descriptor,
                expected_descriptor_sha256=a.render_descriptor_sha256)
        startup_profile.mark('render-descriptor-validated',descriptor_sha256=a.render_descriptor_sha256)
    if a.trusted_text_binding and a.model_adapter=='qwen':
        if render_program:
            from revtrace.render_program_use import verify_use
            with startup_profile.span('render-program-declaration-validation'):
                spec=verify_use(a.render_program_bundle,a.render_program_sha256,a.render_use_manifest,a.render_use_sha256,declared_renderer,a.model)
                runtime['render_contract']={**declared_renderer,'owner_render_program':spec}
        elif a.startup_order=='descriptor_workers_first':
            runtime['render_contract']=declared_renderer
        else:
            render_context=load_native_qwen_context(a.model,startup_profile)
            if declared_renderer is not None:
                require_loaded_renderer_match(declared_renderer,render_context.contract)
            runtime['render_contract']=render_context.contract
    runtime['row_delivery']=a.result_delivery
    if a.result_delivery=='row' and (not a.trusted_text_binding or not a.capture_model_inputs):
        raise ValueError('row delivery requires trusted Render and actual input capture')
    if a.result_delivery=='row' and a.mode=='grouped_replay':
        raise ValueError('legacy grouped replay is outside the five-policy row-completion study')
    proposal={**runtime,"dtype":"float16"}
    if a.prefix_executor_mode:
        if a.microbatch!=1 or not a.envelope_config or not a.protocol_kernel:raise ValueError('LP1 requires batch1 complete kernel/envelope')
        runtime['current_prefix_mode']=a.prefix_executor_mode
        runtime['selection_contract']='new-current-target-input-prefix-KV-v1; complete greedy token/Stop and native Phi; no old cache'
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
    config['kernel_copy_mode']=a.kernel_copy_mode
    if dispatch_wait is not None:config['dispatch_wait']=dispatch_wait
    if a.dispatch_wait_prior is not None:
        if dispatch_wait is None or not a.dispatch_wait_prior_sha256:raise ValueError('prior bank requires frozen wait configuration and hash')
        config['dispatch_wait_prior']={'path':str(a.dispatch_wait_prior),'sha256':a.dispatch_wait_prior_sha256}
    elif a.dispatch_wait_prior_sha256:raise ValueError('prior hash without bank')
    config['prefix_executor_mode']=a.prefix_executor_mode
    config['history_selector']=a.history_selector
    config['post_compute_order']=post_order
    if a.physical_retirement:
        config['confirmation_consumer']=a.consumer_policy
        config['physical_retirement']=dict(policy=a.physical_retirement,watchdog_seconds=a.retirement_watchdog_seconds,
            scope='shared fixed-layout safe-point actuator; physical reuse only after actual BatchDrained')
    if retirement_fixture:
        if retirement_fixture.get('schema')!='physical-retirement-f2-input-fixture-v1':raise ValueError('unfrozen retirement input fixture')
        config['retirement_fault_fixture']=retirement_fixture
        config['retirement_fault_fixture_sha256']=file_sha(a.retirement_fault_fixture)
    config['diagnostic_omit_receive_freshness']=a.omit_receive_freshness
    if envelope:
        config['envelope']=envelope
        config['arrival_schedule_sha256']=file_sha(a.arrival_schedule)
    if a.boundary_probe:config['controlled_boundary_probe']=a.boundary_probe
    if online:
        config['online_study']=online
        if a.online_study_method in ['unprotected','score','strict']:
            config['verification_policy']='online_'+a.online_study_method
    save(a.output/"config.json",config)
    measured_sources=[ROOT/"src/revtrace/startup_overlap.py",Path(__file__),ROOT/"scripts/tc_live_worker.py",ROOT/"src/revtrace/live_qwen.py",ROOT/"src/revtrace/dgft.py",ROOT/"src/revtrace/durable_journal.py",
           ROOT/'scripts/row_delivery_worker.py',ROOT/'scripts/row_delivery_executor.py',ROOT/'src/revtrace/row_lifecycle.py',ROOT/'src/revtrace/row_stream.py']
    if envelope:measured_sources += [ROOT/'src/revtrace'/n for n in ['certified_envelope.py','degradation_state.py','input_debt_journal.py','envelope_display.py','certified_display.py']]
    measured_sources.append(ROOT/'src/revtrace/recovery_profile.py')
    if dispatch_wait is not None:measured_sources.append(ROOT/'src/revtrace/dispatch_wait.py')
    if a.physical_retirement:measured_sources.append(ROOT/'src/revtrace/retirement_runtime.py')
    save(a.output/"provenance.json",{"code_commit":a.code_commit,
        "source_sha256":{str(path.relative_to(ROOT)):file_sha(path) for path in measured_sources},
        "hostname":platform.node(),"python":sys.version,"platform":platform.platform(),
        "pbs_jobid":os.environ.get("PBS_JOBID"),"manifest_sha256":file_sha(a.manifest),
        "gpus":hardware,"software":software,
        "durability_mode":config["durability_mode"],
        "journal_mode":config["journal_mode"],
        "journal_sync_mode":config["journal_sync_mode"],
        "durable_journal_path":str(a.durable_journal_path.resolve()) if a.durable_journal_path else None})
    _phase=startup_profile.begin("audio-assets-load-and-validate")
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
    startup_profile.end(_phase)
    workers={"proposal":[],"authority":[]}
    class ExternalEpisodePower:
        rows=[]
        def start(self):pass
        def stop(self):return dict(samples=0,energy_joules=None,scope='outer episode sampler; no child estimate')
    sampler=ExternalEpisodePower() if envelope else PowerSampler(flat,interval=.2)
    scheduler=None
    consumer=None
    trusted_render=None
    def make_trusted_renderer():
        nonlocal render_context
        with startup_profile.span('trusted-render-construction'):
            if not a.trusted_text_binding:return None
            if a.model_adapter=='whisper':
                from transformers import WhisperProcessor
                from revtrace.whisper_adapter import TrustedWhisperRender
                processor=WhisperProcessor.from_pretrained(a.model,local_files_only=True)
                return TrustedWhisperRender(processor,a.max_new_tokens,runtime['whisper_conditioning'])
            if a.owner_render_backend=='light':
                from revtrace.light_render import load_light_context
                from revtrace.startup_overlap import package_root
                from revtrace.render_program_use import eos_from_assets
                from revtrace.certified_display import TrustedQwenRender
                light=load_light_context(a.render_program_bundle,expected_descriptor_sha256=a.render_program_sha256,
                    model=a.model,package_root=package_root())
                require_loaded_renderer_match(declared_renderer,light.reference_contract)
                startup_profile.mark('equivalent-owner-renderer-loaded',backend='light',implementation=light.implementation_identity)
                startup_profile.mark('owner-render-library-state',backend='light',modules={n:any(k==n or k.startswith(n+'.') for k in sys.modules) for n in ['torch','transformers','qwen_asr','librosa']})
                return TrustedQwenRender(light.tokenizer,light.parse,eos_from_assets(a.model),a.max_new_tokens)
            if render_context is None:
                render_context=load_native_qwen_context(a.model,startup_profile)
            if render_program:
                from revtrace.render_program_use import check_native_program_context
                check_native_program_context(runtime['render_contract'],render_context)
            else:require_loaded_renderer_match(runtime['render_contract'],render_context.contract)
            startup_profile.mark('actual-renderer-contract-matched')
            startup_profile.mark('owner-render-library-state',backend='native',modules={n:any(k==n or k.startswith(n+'.') for k in sys.modules) for n in ['torch','transformers','qwen_asr','librosa']})
            from transformers import AutoProcessor,GenerationConfig
            from revtrace.certified_display import TrustedQwenRender
            processor=recovery_processor(render_context.processor,mode=a.startup_processor_mode,
                load_processor=lambda:AutoProcessor.from_pretrained(a.model,local_files_only=True),profile=startup_profile)
            eos=GenerationConfig.from_pretrained(a.model,local_files_only=True).eos_token_id
            return TrustedQwenRender(processor.tokenizer,render_context.parse,[eos] if isinstance(eos,int) else eos,a.max_new_tokens)
    def abort_bootstrap_workers():
        errors=[]
        for group in workers.values():
            for worker in list(group):
                try:
                    worker.close()
                    group.remove(worker)
                except BaseException as exc:errors.append((worker.name,type(exc).__name__))
        startup_profile.mark('startup-abort-workers',failed_closes=errors)
        if errors:raise RuntimeError('startup worker cleanup failed; retained handles: '+str(errors))
    result=None
    deferred_worker_records=[]
    deferred_cancelled_records=[]
    deferred_batch_accounting=[]
    deferred_ipc_payloads=[]
    try:
        initialization_started=time.perf_counter()
        def spawn_workers():
            for role,indices in gpus.items():
                rt=runtime if role=="authority" else proposal
                for gpu in indices:
                    executor_type=GPUExecutor
                    if a.result_delivery=='row':
                        from row_delivery_executor import RowGPUExecutor
                        executor_type=RowGPUExecutor
                    _phase=startup_profile.begin("worker-spawn",worker=f"{role}-{gpu}")
                    worker=executor_type(f"{role}-{gpu}",{**rt,"runtime_digest":fingerprint(rt),
                        "physical_retirement":bool(a.physical_retirement and a.physical_retirement!='row_complete' and role=='proposal'),
                        "allow_execution_context_override":bool(retirement_fixture and role=='proposal') or rt.get('allow_execution_context_override',False),
                        "lifecycle_instrumentation":not a.full_diagnostic_hooks_off,
                        "capture_model_inputs":a.capture_model_inputs,
                        "delay_every":a.delay_every,"delay_offset":a.delay_offset,
                        "gpu":gpu,"model":str(a.model),"manifest":str(a.manifest),
                        "receipt_trace_path":str(a.output/f'worker-{role}-{gpu}-receipts.jsonl') if a.receipt_trace else None,
                        "result_delay_seconds":a.proposal_result_delay if role=='proposal' else a.authority_result_delay})
                    workers[role].append(worker)
                    startup_profile.end(_phase,worker=f"{role}-{gpu}",pid=worker.process.pid)
        trusted_render=bootstrap_renderer_and_workers(a.startup_order,
            load_renderer=make_trusted_renderer,spawn_workers=spawn_workers,abort_workers=abort_bootstrap_workers)
        startup_profile.mark('trusted-runtime-bootstrap-complete',startup_order=a.startup_order)
        def await_execution_readiness():
            for group in workers.values():
                for worker in group:
                    _wait=startup_profile.begin("worker-ready-wait",worker=worker.name)
                    worker.wait_ready()
                    startup_profile.end(_wait,worker=worker.name)
                    startup_profile.mark("worker-ready-received",worker=worker.name,worker_startup=worker.ready.get("startup_profile"))
                    if scheduler is not None and hasattr(scheduler,'execution_ready'):
                        scheduler.execution_ready(worker)
                    print(json.dumps({"worker_ready":worker.name,**worker.ready}),flush=True)
            save(a.output/"workers.json",[w.ready for group in workers.values() for w in group])
            save(a.output/'EXECUTORS_READY.json',dict(observed_perf=time.perf_counter()))
        if not early_recovery:await_execution_readiness()
        handles=[]
        for group in workers.values():
            for w in group:
                proc=Path('/proc')/str(w.process.pid)
                handles.append({'pid':w.process.pid,'name':w.name,'parent_pid':os.getpid(),
                  'worker_incarnation':getattr(w,'incarnation',None),
                  'linux_start_ticks':proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19] if proc.exists() else None,
                  'command_sha256':file_sha(proc/'cmdline') if proc.exists() else None})
        save(a.output/'OWNED_WORKER_HANDLES.json',handles)
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
                    view=EnvelopeView(policy=a.consumer_policy,strict_bound=True,fine_samples=32000),
                    crash_trace_path=a.output/'consumer-live.jsonl' if a.receipt_trace else None,startup_profile=startup_profile)
            else:consumer=RealtimeConsumer(a.output/'consumer.jsonl',a.consumer_policy,strict_bound=a.trusted_text_binding,startup_profile=startup_profile)
            emitted_commits=0
            def emit(row):
                nonlocal emitted_commits
                if row['kind']=='ipc-complete-payload':
                    deferred_ipc_payloads.append(row)
                    return
                if row['kind']=='worker-record':
                    deferred_worker_records.append(row)
                    return
                if row['kind']=='worker-cancelled-record':
                    deferred_cancelled_records.append(row)
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
                durable_journal_path=a.durable_journal_path,trusted_render=trusted_render,startup_profile=startup_profile)
            if envelope:
                from revtrace.certified_envelope import CertifiedEnvelopeScheduler
                scheduler_type=CertifiedEnvelopeScheduler
                scheduler_arguments.update(consumer=consumer,input_journal_path=a.input_journal_path)
                if a.protocol_kernel:
                    from revtrace.kernel_runtime import KernelEnvelopeScheduler
                    scheduler_type=KernelEnvelopeScheduler
                    if a.history_selector!='latest':
                        from revtrace.historical_display import HistoricalKernelScheduler
                        scheduler_type=HistoricalKernelScheduler
                        scheduler_arguments['history_strategy']=a.history_selector
                    if a.prefix_executor_mode:
                        from revtrace.prefix_runtime import PrefixSeedMixin
                        scheduler_type=type('CurrentInputSeedScheduler',(PrefixSeedMixin,scheduler_type),{})
                    if a.boundary_probe:
                        from revtrace.kernel_probe import ProbeKernelScheduler
                        scheduler_type=ProbeKernelScheduler
                    if a.physical_retirement:
                        from revtrace.retirement_runtime import RetirementScheduler
                        scheduler_type=RetirementScheduler
            _phase=startup_profile.begin("scheduler-and-input-debt-restoration")
            scheduler=scheduler_type(**scheduler_arguments)
            startup_profile.end(_phase)
            _recovered={sid:s.state.audio_frontier_window for sid,s in scheduler.sessions.items()}
            _accepted={sid:scheduler.book.session(sid).accepted for sid in scheduler.sessions} if envelope else dict(_recovered)
            startup_profile.configure_recovery(recovered_frontiers=_recovered,accepted_frontiers=_accepted,owner_incarnation=scheduler.t0,original_origin_perf=scheduler.origin if envelope else scheduler.t0)
            if (a.pause_post_sync_at or logical_fault_target is not None) and not early_recovery and scheduler.owner_epoch==1:
                actual_sync=scheduler._journal.commit_transitions
                def sync_then_pause(transitions):
                    receipts=actual_sync(transitions)
                    should_pause=(target_in_synced_group(transitions,logical_fault_target) if logical_fault_target is not None
                        else time.perf_counter()>=scheduler.origin+a.pause_post_sync_at)
                    if should_pause:
                        save(a.output/'POST_SYNC_KILL_READY.json',dict(observed_perf=time.perf_counter(),
                            logical_target=a.pause_post_sync_target,
                            durable_sequences=[int(r[0]) for r in receipts],
                            transactions=[t['transaction_id'] for t in transitions],
                            durable_frontiers={str(s.session_id):s.audio_frontier_window for s in scheduler._journal.states()},
                            point='actual fsync complete, owner installation/publication not yet executed'))
                        while True:time.sleep(.01)
                    return receipts
                scheduler._journal.commit_transitions=sync_then_pause
                scheduler._journal.commit_transition=lambda **t:sync_then_pause([t])[0]
            save(a.output/'FACTS_AND_DEBT_RESTORED.json',dict(observed_perf=time.perf_counter(),
                recovered_frontiers={str(sid):s.state.audio_frontier_window for sid,s in scheduler.sessions.items()},
                input_snapshot=scheduler.book.snapshot(scheduler.origin) if envelope else None))
            if early_recovery:await_execution_readiness()
            elif hasattr(scheduler,'execution_ready'):
                for group in workers.values():
                    for worker in group:scheduler.execution_ready(worker)
            worker_initialization_seconds=time.perf_counter()-initialization_started
            save(a.output/"initial_states.json",[{"session_id":s.sid,"state":__import__('dataclasses').asdict(s.state)} for s in scheduler.sessions.values()])
            result=scheduler.run()
        result["consumer"]=consumer.close()
        wait_controller=getattr(scheduler,'_dispatch_wait_controller',None)
        if wait_controller is not None:
            result['dispatch_wait_profile']=wait_controller.profile()
            save(a.output/'dispatch_wait_profile.json',wait_controller.profile())
        result['actual_consumer_last_application_seconds']=max((r['observed'] for r in consumer.rows),default=0.)
        result['wall_seconds_including_arrival_and_drain']=max(result['wall_seconds_including_arrival_and_drain'],result['actual_consumer_last_application_seconds'])
        consumer=None
        result["worker_initialization_seconds"]=worker_initialization_seconds
        result["journal_recovery_seconds"]=scheduler.journal_recovery_seconds
        result["startup_profile"]=startup_profile.summary()
        save(a.output/"startup_summary.json",startup_profile.summary())
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
        save(a.output/"startup_summary.json",startup_profile.summary())
        if scheduler is not None and hasattr(scheduler,'kernel') and scheduler.kernel is not None:
            save(a.output/'kernel_trace.json',dict(events=scheduler.kernel.trace,
                cpu_seconds=scheduler.kernel.cpu_seconds,scope='operation-bound trusted-host receipts; not hardware attestation'))
        if scheduler is not None and hasattr(scheduler,'probe_report'):
            save(a.output/'BOUNDARY_PROBE.json',scheduler.probe_report())
        if deferred_ipc_payloads:
            with (a.output/'ipc_completed_payloads.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_ipc_payloads:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if deferred_worker_records:
            # Captured immutable rows retain their original receipt timestamps.
            # Rich JSON serialization is outside the serving/power interval.
            with (a.output/'worker_records.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_worker_records:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if deferred_cancelled_records:
            with (a.output/'worker_cancelled_records.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_cancelled_records:stream.write(json.dumps(row,allow_nan=False)+'\n')
        if deferred_batch_accounting:
            with (a.output/'worker_batch_accounting.jsonl').open('w',encoding='utf-8') as stream:
                for row in deferred_batch_accounting:stream.write(json.dumps(row,allow_nan=False)+'\n')
        close_owned_components(consumer,scheduler,workers)

if __name__=="__main__":
    raise SystemExit(main())
