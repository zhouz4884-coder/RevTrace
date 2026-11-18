"""Independent original-fact/publication/Consumer binding for one closed trial."""
from pathlib import Path
import hashlib,json,re,sys,traceback
from consumer_audit import audit_consumer,provisional_registry
from job_accounting import audit_trial
from native_view_metrics import continuity_metrics
from trial_audit import read,lines

NEURAL=('torch','transformers','whisper','qwen_asr','vllm')

def _dump(path,value):
    Path(path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())

def _audit_trial_view(root,runtime_source):
    """Audit already completed data. Compatibility-preserving S0 losses are outcomes.

    Required config flag: consumer_retain_views (legacy absence defaults to S1).
    The runtime source supplies pure parsers, never a constructor/inference call.
    """
    root=Path(root).resolve();runtime_source=Path(runtime_source).resolve()
    if not root.is_dir()or not runtime_source.is_dir():raise ValueError('missing trial/runtime parser source')
    before={name for name in sys.modules if name.split('.')[0]in NEURAL}
    sys.path.insert(0,str(runtime_source))
    import feedback_contract,resilience_storage,resilience_metrics
    for module in (feedback_contract,resilience_storage,resilience_metrics):
        if not Path(module.__file__).resolve().is_relative_to(runtime_source):raise ValueError('loaded parser source is outside declared runtime source')
    cfg=read(root/'CONFIG.json');source_commit=cfg.get('source_commit')
    if not isinstance(source_commit,str)or not re.fullmatch('[0-9a-f]{40}',source_commit)or cfg.get('settings',{}).get('source_commit')!=source_commit:raise ValueError('runtime source roles differ in actual configuration')
    retain=cfg.get('consumer_retain_views',True)
    if type(retain)is not bool:raise ValueError('frozen Consumer retention flag must be boolean')
    declared=cfg['settings']['sources'];sources={s['source_id']:s for s in declared}
    if len(sources)!=len(declared):raise ValueError('duplicate declared input source')
    header,_=next(resilience_storage.scan(root/'facts.wal',repair_tail=False))
    metadata=header['body']['metadata']
    config_sha=hashlib.sha256(feedback_contract.canonical_bytes(cfg)).hexdigest()
    if header['kind']!='genesis'or metadata['actual_source_commit']!=source_commit or metadata['config_sha256']!=config_sha:raise ValueError('WAL genesis/source/config binding failed')
    _,facts,_=resilience_metrics.fact_audit(root/'facts.wal',sources)
    reference=resilience_metrics.reference_audit(cfg,facts,source_commit)
    if cfg.get('require_reference',True)and reference['status']!='PASS_COMPLETE_ORIGINAL_REFERENCE':raise ValueError('original full-task reference failed')
    if cfg.get('reference_kind','strict')not in ('strict','continuous_original'):raise ValueError('full-view audit requires an unprojected original reference')
    initials=read(root/'GENESIS.json')
    if initials!=header['body']['initials']:raise ValueError('GENESIS export differs from original WAL genesis')
    rows=lines(root/'consumer.jsonl');publications=lines(root/'publications.jsonl')
    if not rows:raise ValueError('no actual Consumer observations')
    dispatches=[];workers=[]
    for folder in sorted(root.glob('owner_e*')):
        if folder.is_dir():dispatches.extend(lines(folder/'dispatch.jsonl'));workers.extend(lines(folder/'worker_results.jsonl'))
    registry=provisional_registry(dispatches,workers)
    replay=audit_consumer(rows,publications,facts,initials,registry,retain_views=retain,
        require_reconciliation_metadata='consumer_retain_views'in cfg)
    if set(replay['applied_fact_sequences'])!={f['sequence']for f in facts}:raise ValueError('closed trial did not apply every bound original fact')
    end=read(root/'SERVICE_END.json')['service_end_perf']
    metrics=continuity_metrics(rows,replay['canonical_events'],end_perf=end)
    accounting=audit_trial(root,resilience_storage.scan,closed=True)
    if accounting['status']!='PASS_DISJOINT_JOB_ACCOUNTING':raise ValueError('original dispatch/terminal conservation failed')
    imported={name for name in sys.modules if name.split('.')[0]in NEURAL}-before
    if imported:raise ValueError('neural modules imported by view audit: '+','.join(sorted(imported)))
    out=root/'view_audit';out.mkdir(exist_ok=True)
    _dump(out/'CANONICAL_SUPPORT_EVENTS.json',replay['canonical_events'])
    _dump(out/'OBSERVED_LOSS_WINDOWS.json',metrics['loss_windows'])
    input_paths=[root/n for n in ['CONFIG.json','GENESIS.json','facts.wal','consumer.jsonl','publications.jsonl','SERVICE_END.json']]
    input_paths.extend(p for folder in sorted(root.glob('owner_e*'))if folder.is_dir()for n in ['dispatch.jsonl','worker_results.jsonl']if(p:=folder/n).is_file())
    result=dict(status='PASS_NATIVE_VIEW_APPLICATION_AUDIT',cell_id=cfg['cell_id'],condition=cfg.get('condition'),
        runtime_execution_commit=source_commit,consumer_retain_views=retain,continuity=metrics['continuity'],
        consumer_support=replay['counts'],original_reference=reference,
        original_durable_facts_applied=len(facts),job_accounting=accounting,
        input_files=[dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,
            sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in input_paths],
        pure_parser_files=[dict(path=Path(m.__file__).name,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest())for m in (feedback_contract,resilience_storage,resilience_metrics)],
        detail_files=['view_audit/CANONICAL_SUPPORT_EVENTS.json','view_audit/OBSERVED_LOSS_WINDOWS.json'],
        neural_modules_imported=sorted(imported),benefit_or_nonzero_activation_required=False)
    _dump(out/'SUMMARY.json',result)
    _dump(out/'GATE.json',dict(status=result['status'],consumer_retain_views=retain,
        outcome_required='Only binding/integrity and closed accounting; no expected S benefit or nonzero opportunity gate'))
    return result

def audit_trial_view(root,runtime_source):
    try:return _audit_trial_view(root,runtime_source)
    except BaseException:
        out=Path(root)/'view_audit';out.mkdir(parents=True,exist_ok=True)
        _dump(out/'GATE.json',dict(status='FAIL_NATIVE_VIEW_APPLICATION_AUDIT_PRESERVED',failure=traceback.format_exc(),
            note='Integrity/audit failure is preserved; this is not a zero-benefit or zero-opportunity decision.'))
        raise

audit_trialview=audit_trial_view
