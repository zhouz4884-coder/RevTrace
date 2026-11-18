"""Post-idle only: original de0936 parsers and actual per-trial profiles."""
from collections import Counter,defaultdict
import hashlib,json,re,math
from pathlib import Path
from definitions import sha_state
from trace_profiles import profile_owner
from consumer_audit import audit_consumer,provisional_registry
from job_accounting import audit_trial

NN='de0936b2e30179d63aeef6e235cd1af685578c58'
def read(path):return json.loads(Path(path).read_bytes())
def lines(path):return [json.loads(x) for x in Path(path).read_bytes().splitlines() if x.strip()] if Path(path).exists() else []
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def ownership(energy_rows,worker_identities,window):
    if not energy_rows or not window:return dict(verifiable=False,reason='missing external power/declared physical-drain interval',foreign_samples=[])
    times=[r.get('time') for r in energy_rows]
    if not all(isinstance(t,(int,float)) and math.isfinite(t) for t in times) or times!=sorted(times):return dict(verifiable=False,reason='missing/nonmonotonic external sample clocks',foreign_samples=[])
    begin,end=window['begin_perf'],window['end_perf']
    inside=[r for r in energy_rows if begin<=r['time']<=end]
    if len(energy_rows)<2 or times[0]>begin or times[-1]<end or not inside:return dict(verifiable=False,reason='no actual in-window samples or missing interval boundary coverage',foreign_samples=[])
    coverage=inside+[max((r for r in energy_rows if r['time']<=begin),key=lambda r:r['time']),min((r for r in energy_rows if r['time']>=end),key=lambda r:r['time'])]
    unique={}
    for row in coverage:
        if row['time'] in unique and unique[row['time']]!=row:return dict(verifiable=False,reason='inconsistent duplicate external sample timestamp',foreign_samples=[])
        unique[row['time']]=row
    coverage=list(unique.values())
    for row in coverage:
        if not isinstance(row.get('compute_processes'),list) or not all(str(g) in row.get('boards',{}) and isinstance(row['boards'][str(g)].get('watts'),(int,float)) and math.isfinite(row['boards'][str(g)]['watts']) for g in (0,1)) or row.get('observation_begin_perf') is None or row.get('observation_end_perf') is None:
            return dict(verifiable=False,reason='external sample ownership/power/query-interval schema missing',foreign_samples=[])
    if not worker_identities or any(w.get('start_ticks') is None or w.get('begin') is None or w.get('end') is None for w in worker_identities):return dict(verifiable=False,reason='worker PID/starttick/termination interval missing',foreign_samples=[])
    foreign=[]
    for row in coverage:
        for process in row.get('compute_processes',[]):
            if 'pid' not in process:return dict(verifiable=False,reason='external owner PID absent',foreign_samples=[])
            matched=any(w['pid']==process['pid'] and w['begin']<=row['observation_end_perf'] and w['end']>=row['observation_begin_perf'] for w in worker_identities)
            if not matched:foreign.append(dict(time=row['time'],pid=process['pid'],gpu_uuid=process.get('gpu_uuid'),sample_scope='in_or_overlapping_service_window' if row['observation_begin_perf']<=end and row['observation_end_perf']>=begin else 'outside_window_power_interpolation_bracket'))
    return dict(verifiable=not foreign,foreign_samples=foreign,
        worker_identity_intervals=worker_identities,samples_in_window=len(inside),
        scope='Recorded NVML PID/query-interval matches generation-bound launch/exit records; no per-sample starttick attestation or proof of unobserved sub-sampling interference')

def audit_cell(cell,config,out):
    from feedback_contract import FeedbackCut
    from resilience_storage import scan
    from resilience_metrics import fact_audit,reference_audit,posterior_support
    from original_primary_quantiles import cell_metrics
    from content_endpoints import analyze_cell
    root=Path(cell['out']);cfg=read(root/'CONFIG.json')
    if cfg!=config or cfg['settings']['source_commit']!=NN or cfg.get('source_commit')!=NN:
        raise ValueError('actual/frozen cell configuration or NN source differs')
    sources={s['source_id']:s for s in cfg['settings']['sources']}
    if set(sources)!={cell['source_id']} or cfg['arm']!=cell['strategy'] or cfg['repeat']!=cell['repeat']:
        raise ValueError('PILOT24 source/arm/repeat scope changed')
    header,_=next(scan(root/'facts.wal',repair_tail=False))
    metadata=header['body']['metadata']
    if header['kind']!='genesis' or metadata['actual_source_commit']!=NN or metadata['config_sha256']!=sha_state(cfg):raise ValueError('WAL genesis source/config role mismatch')
    roots,facts,processed=fact_audit(root/'facts.wal',sources)
    reference=reference_audit(cfg,facts,NN)
    if reference['status']!='PASS_COMPLETE_ORIGINAL_REFERENCE' or reference['reference_kind']!='strict':raise ValueError('strict original full-task reference failed')
    rows=lines(root/'consumer.jsonl');pubs=lines(root/'publications.jsonl');initials=read(root/'GENESIS.json')
    if header['body']['initials']!=initials:raise ValueError('actual GENESIS export differs from durable full genesis')
    owner_data=[];all_dispatch=[];all_workers=[]
    for folder in sorted(root.glob('owner_e*')):
        if not folder.is_dir():continue
        match=re.fullmatch(r'owner_e(\d+)',folder.name)
        if match is None:continue
        data=dict(epoch=int(match[1]),dispatch=lines(folder/'dispatch.jsonl'),events=lines(folder/'owner_events.jsonl'),workers=lines(folder/'worker_results.jsonl'),audits=lines(folder/'policy_audit.jsonl'))
        owner_data.append(data);all_dispatch.extend(data['dispatch']);all_workers.extend(data['workers'])
    consumer=audit_consumer(rows,pubs,facts,initials,provisional_registry(all_dispatch,all_workers))
    by_fact_seq={f['sequence']:f for f in facts}
    consumer_applied_jobs={by_fact_seq[r['journal_sequence']]['body']['job']['job_id'] for r in rows if r['kind']=='canonical'}
    primary=cell_metrics(dict(out=str(root),cell_id=cfg['cell_id'],stage=cfg['stage'],cohort=cfg['cohort'],arm=cfg['arm'],repeat=cfg['repeat']))
    summary=read(root/'SUMMARY.json')
    for key,value in primary.items():
        if key!='raw_inputs' and summary['primary'].get(key)!=value:raise ValueError('original primary endpoint changed: '+key)
    origin=read(root/'ORIGIN.json')['origin_perf']
    content,_,_,frontiers=analyze_cell(dict(cell_id=cfg['cell_id']),rows,sources,origin)
    if abs(content['original_dual_credit_audio_seconds']-primary['dual_deadline_audio_credit_seconds'])>1e-8:raise ValueError('original credit not conserved')
    support=posterior_support(rows,frontiers,facts)
    accounting=audit_trial(root,scan,closed=True)
    if accounting['status']!='PASS_DISJOINT_JOB_ACCOUNTING':raise ValueError('actual job/lifecycle accounting failed')
    old_accounting=read(root/'JOB_ACCOUNTING.json')
    for key in ('dispatches','counts','partition_count','Owner_admitted_ready_reuse','unique_promoted_jobs'):
        if old_accounting.get(key)!=accounting.get(key):raise ValueError('driver accounting changed: '+key)
    fact_cuts={sid:{0:initials[sid]} for sid in sources}
    for f in facts:fact_cuts[f['body']['source_id']][f['body']['next_state']['frontier']]=f['body']['next_state']
    starts={};supervisor=lines(root/'supervisor.jsonl')
    for row in supervisor:
        event=row.get('event',{})
        if event.get('kind')=='owner_ready':
            epoch=event['owner_epoch'];starts[epoch]={sid:fact_cuts[sid][F] for sid,F in event['recovered_frontiers'].items()}
    counts=Counter();decisions=[];job_profiles=[];before_c=[];late=[];work=[];redispatch=[];worker_identities={}
    for data in owner_data:
        epoch=data['epoch'];events=data['events'];dispatch=data['dispatch']
        if epoch not in starts:raise ValueError('Owner initial/recovered roots not observed')
        for r in events:
            if r['kind']=='worker_started':worker_identities[r['pid'],r['start_ticks']]=dict(pid=r['pid'],start_ticks=r['start_ticks'],owner_epoch=epoch,begin=r['observed'],end=None)
            elif r['kind'] in ('worker_final_exit','worker_death_confirmed'):
                proof=r['proof'];key=proof['pid'],proof['start_ticks']
                if key in worker_identities:worker_identities[key]['end']=max(r['observed'],proof['confirmed_perf'],proof.get('cuda_release',{}).get('observed_perf',0))
        value=profile_owner(epoch,dispatch,events,data['workers'],data['audits'],starts[epoch],facts,consumer_applied_jobs,{sid:s['frames'] for sid,s in sources.items()})
        counts.update(value['counts'])
        for target,key in ((decisions,'decisions'),(job_profiles,'job_summaries'),(before_c,'before_C_exits'),(late,'late_refusals'),(work,'work'),(redispatch,'redispatch')):
            target.extend(dict(owner_epoch=epoch,**r) if 'owner_epoch' not in r else r for r in value[key])
    if counts['actual_owner_ready_reuse']!=accounting['Owner_admitted_ready_reuse']:raise ValueError('Owner ready reuse does not match raw job accounting')
    global_inputs=defaultdict(list)
    for w in work:global_inputs[w['source_id'],w['start_sha'],w['target']].append(w)
    global_redispatch=[dict(source_id=k[0],start_sha=k[1],target=k[2],jobs=[r['job_id'] for r in sorted(v,key=lambda x:x['dispatch_perf'])],
        owner_epochs=sorted({r['owner_epoch'] for r in v}),actual_reissues=len(v)-1) for k,v in global_inputs.items() if len(v)>1]
    counts['same_complete_input_target_redispatches_all_owner_epochs']=sum(r['actual_reissues'] for r in global_redispatch)
    external=read(root/'EXTERNAL_NEW_TEST_AUDIT.json');window=external.get('common_external_energy',{}).get('origin_to_confirmed_physical_model_drain')
    for identity in worker_identities.values():
        if identity['end'] is None:
            death=next((r for r in supervisor if r['kind']=='owner_group_death_confirmed' and r['owner_epoch']==identity['owner_epoch']),None)
            if death is not None:identity['end']=death['observed'];identity['end_scope']='Owner group death confirmation bound'
    energy=ownership(lines(cell['external_power']),list(worker_identities.values()),window)
    expected_offered=sum(s['frames']/16000 for s in sources.values())
    if abs(expected_offered-primary['offered_audio_seconds'])>1e-8:raise ValueError('configured all-offered/EOS denominator differs')
    handovers=counts['actual_canonical_install_events']
    normalized={key:dict(per_offered_audio_second=counts[key]/expected_offered,per_actual_install=counts[key]/handovers if handovers else None)
        for key in ('unique_model_active_compatible_confirmation_jobs','unique_ancestor_disagreement_jobs','unique_ordinary_direct_both_retain_jobs','known_invalid_or_covered_before_C_exits')}
    target=out/'cells'/cell['cell_id'];target.mkdir(parents=True)
    for name,value in [('DECISION_PROFILES',decisions),('JOB_PROFILES',job_profiles),('BEFORE_C_EXITS',before_c),('LATE_REFUSALS',late),('ACTUAL_PAID_WORK',work),('REDISPATCH_WITHIN_OWNER',redispatch),('REDISPATCH_ALL_OWNER_EPOCHS',global_redispatch),('CONSUMER_SUPPORT_EVENTS',consumer['events'])]:dump(target/(name+'.json'),value)
    return dict(cell_id=cell['cell_id'],source_id=cell['source_id'],speaker_id=cell['speaker_id'],strategy=cell['strategy'],repeat=cell['repeat'],
        estimand_role=cell['estimand_role'],status='PASS_ACTUAL_INPUT_FACT_CONSUMER_ACCOUNTING_BINDINGS',configured_offered_audio_seconds=expected_offered,
        primary=primary,posterior_whole_text_support=support,opportunities=dict(counts),normalized_opportunities=normalized,
        consumer_support=consumer['counts'],job_accounting=accounting,energy_ownership=energy,
        observed_both_board_energy_J=window.get('total_joules') if window else None,
        verified_both_board_energy_J=window.get('total_joules') if window and energy['verifiable'] else None,
        missing_fields=dict(exact_before_C_checkpoint_times='not logged; terminal facts or ASR produced upper bound only',
            aborted_infer_timers=counts['infer_interval_missing_jobs'],fullcall_ancestor_losses='reconstructed actual-prefix shadow predicate, not a native emitted policy decision',
            shadow_predicate_counterfactual_audio_seconds='not identifiable; deliberately absent'),
        SUP_independent_increment_identified=False,shadow_schedule_executed=False)
