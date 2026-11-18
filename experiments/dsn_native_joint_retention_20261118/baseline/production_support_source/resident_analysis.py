"""Independent resident request-clock ledger and original endpoint analysis."""
from __future__ import annotations
import pathlib
from common import need,read,lines,sha,verified_facts
from audit_results import selected_trace
from endpoints import recount

def audit_request_clocks(config,origins,ledger,ingress,consumer):
    sources={s['source_id']:s for s in config['settings']['sources']};order=config['request_order'];admitted=[r for r in ledger if r['kind']=='request_admitted'];complete=[r for r in ledger if r['kind']=='request_complete']
    need(set(origins)==set(sources) and len(admitted)==len(complete)==len(order),'incomplete/duplicate request ledger')
    need([r['source_id'] for r in admitted]==order and [r['source_id'] for r in complete]==order,'closed-loop request order differs')
    completed={r['source_id']:r for r in complete};seen=set();checks=0
    for index,row in enumerate(admitted):
        sid=row['source_id'];need(row['request_index']==index and row['request_origin_perf']==origins[sid] and row['observed']==origins[sid],'request origin ledger binding')
        if index:
            previous=order[index-1];need(row['previous_source_id']==previous and row['previous_complete_perf']==completed[previous]['observed'] and row['observed']>=completed[previous]['observed'],'next request admitted before actual prior Consumer EOS')
        else:need(row['previous_source_id'] is None,'first request has invented previous source')
        eos=completed[sid];need(eos['EOS_frontier']==eos['certified_frontier']==sources[sid]['frames'] and eos['consumer_observed_perf']==eos['observed'],'request completion is not certified original EOS')
        need(any(r['source_id']==sid and r['observed']==eos['observed'] and r['certified_frontier']==sources[sid]['frames'] for r in consumer),'request completion lacks actual Consumer witness')
        own=[r for r in ingress if r['source_id']==sid];expected=list(range(8000,sources[sid]['frames'],8000))+[sources[sid]['frames']]
        need([r['frontier'] for r in own]==expected,'accepted request obligations missing/duplicated/reordered or EOS dropped')
        for event in own:
            need(abs(event['original_offer']-(origins[sid]+event['frontier']/16000))<1e-6,'request offer rebased incorrectly')
            need(event['observed']>=event['original_offer'] and event['audio_sha256']==sources[sid]['audio_sha256'],'accepted request clock/immutable source differs');checks+=1
    # A future sid may have a genesis, but cannot have actual Consumer work
    # before that request was admitted. It cannot borrow a previous request.
    for row in consumer:need(row['source_id'] in origins and row['observed']>=origins[row['source_id']],'unadmitted request acquired actual Consumer progress')
    return dict(status='PASS_CLOSED_LOOP_ACTUAL_EOS_AND_ALL_ORIGINAL_REQUEST_OFFERS',requests=len(order),accepted_frontiers_checked=checks,EOS_included=True,no_hindsight_gap_or_origin_rewrite=True)

def analyze_resident(out):
    out=pathlib.Path(out);config=read(out/'CONFIG.json');sources={s['source_id']:s for s in config['settings']['sources']};origins=read(out/'REQUEST_ORIGINS.json');rows=lines(out/'consumer.jsonl');ledger=lines(out/'request_ledger.jsonl');ingress=lines(out/'ingress.jsonl')
    need(config.get('require_reference',True),'resident empirical task gate requires legal complete reference')
    need(sha(config['reference_details'])==config['reference_details_sha256'],'resident legal reference bytes differ');reference=read(config['reference_details'])
    need(sha(config['reference_gate'])==config['reference_gate_sha256'] and read(config['reference_gate'])['status'].startswith('PASS'),'resident reference gate missing/changed')
    clocks=audit_request_clocks(config,origins,ledger,ingress,rows);semantic=selected_trace(out,config,reference,config['settings']['source_commit']);primary=recount(rows,sources,origins)
    complete={r['source_id']:r for r in ledger if r['kind']=='request_complete'};per=[]
    for sid in config['request_order']:
        metric=recount([r for r in rows if r['source_id']==sid],{sid:sources[sid]},{sid:origins[sid]})
        per.append(dict(source_id=sid,request_origin_perf=origins[sid],primary=metric,actual_Consumer_EOS_perf=complete[sid]['consumer_observed_perf'],original_reference_status=semantic['status']))
    from resilience_metrics import power_metrics,history_metrics
    origin=read(out/'ORIGIN.json')['origin_perf'];end=read(out/'SERVICE_END.json')['service_end_perf'];energy=power_metrics(out,origin,end)
    return dict(gate='PASS_RESIDENT_COMPLETE_TASK_PER_REQUEST_CLOCK_AND_REFERENCE',experiment_id=config['experiment_id'],cell_id=config['cell_id'],arm=config['arm'],harness_source_commit=config['harness_source']['source_commit'],actual_NN_source_commit=config['settings']['source_commit'],request_contract=config['request_contract'],requests=len(sources),primary=primary,per_request=per,energy=energy,history=history_metrics(out),integrity=dict(original_reference=semantic,all_original_obligations_eventually_processed=True,request_clock=clocks),scope='Finite preregistered closed-loop one-outstanding independent requests, original EOS/500ms/FP32/C_U. No open-arrival capacity, dynamic session registration, unbounded memory, VAD or no-reset long-stream repair claim.')
