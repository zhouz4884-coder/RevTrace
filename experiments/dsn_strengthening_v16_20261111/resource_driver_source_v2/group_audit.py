"""All-source original-offer endpoints, full selected G and resource accounting."""
import pathlib
from confirmation_common import need,read
from job_accounting import audit_trial

def audit_group(cell,config,reference,observer,*,audit_results,endpoints,scan):
    # The immutable a13 audit already checks every source in config, not just
    # cell.source_id. Its scalar source_id is a legacy result label only.
    result=audit_results.audit_cell(dict(cell,source_id=cell['group_id'],version='final'),config,reference,observer)
    result.pop('source_id',None);root=pathlib.Path(cell['out']);origin=read(root/'ORIGIN.json')['origin_perf']
    rows=endpoints.lines(root/'consumer.jsonl') if hasattr(endpoints,'lines') else [__import__('json').loads(r) for r in (root/'consumer.jsonl').read_text(encoding='utf8').splitlines() if r]
    sources={s['source_id']:s for s in config['settings']['sources']}
    per_source={sid:endpoints.recount([r for r in rows if r['source_id']==sid],{sid:s},{sid:origin}) for sid,s in sources.items()}
    need(abs(sum(p['offered_audio_seconds'] for p in per_source.values())-result['primary']['offered_audio_seconds'])<1e-8,'group/source offered denominator does not close')
    need(abs(sum(p['dual_deadline_audio_credit_seconds'] for p in per_source.values())-result['primary']['dual_deadline_audio_credit_seconds'])<1e-8,'group/source credit does not close')
    accounting=audit_trial(root,scan,closed=True);need(accounting['status']=='PASS_DISJOINT_JOB_ACCOUNTING','group jobs do not close')
    import json
    dispatch=[];worker_intervals=[]
    for attempt in sorted(root.glob('owner_e*')):
        for line in (attempt/'owner_events.jsonl').read_text(encoding='utf8').splitlines():
            r=json.loads(line)
            if r['kind']=='shared_dispatcher_successful_dispatch':dispatch.append(dict(job_id=r['job_id'],**r['dispatch']))
        for line in (attempt/'worker_results.jsonl').read_text(encoding='utf8').splitlines():
            e=json.loads(line)['event']
            if e.get('kind')=='completed':
                record=e['record'];worker_intervals.append(dict(job_id=e['job_id'],source_id=e['source_id'],physical_gpu=e.get('gpu'),model_start=record.get('model_start'),model_end=record.get('model_end'),worker_begin=record.get('worker_job_begin_perf'),worker_end=record.get('worker_job_end_perf')))
    need(len(dispatch)==accounting['dispatches'],'successful dispatch diagnostic/owned job ledger differs')
    need(all(not r['eligible_canonical_sources'] or r['chosen_layer']=='canonical' for r in dispatch),'conditional work bypassed observed canonical demand')
    waits={sid:[] for sid in sources}
    for attempt in root.glob('owner_e*'):
        for line in (attempt/'dispatch.jsonl').read_text(encoding='utf8').splitlines():
            job=json.loads(line)['job'];waits[job['source_id']].append(dict(job_id=job['job_id'],dispatch_delay_from_original_offer_seconds=job['dispatched_perf']-(origin+job['end']/16000),started_on_canonical=job['started_on_canonical']))
    result.update(source_group_id=cell['group_id'],source_count=len(sources),source_ids=list(sources),speaker_ids=[s['speaker_id'] for s in sources.values()],per_source_primary=per_source,
        job_accounting=accounting,dispatches=dispatch,canonical_dispatches=sum(r['chosen_layer']=='canonical' for r in dispatch),conditional_dispatches=sum(r['chosen_layer']=='conditional' for r in dispatch),worker_model_intervals=worker_intervals,
        per_source_dispatch_delays=waits,dispatch_delay_scope='original-offer to dispatch includes dependency and physical queue/Owner delay; not isolated scheduler wait',
        original_synchronous_origin=origin,all_waiting_chains_kept_in_denominator=True,new_independent_speakers=0,
        CUDA_active_time='UNMEASURED; host model/worker intervals are not CUDA active-time profiling')
    return result
