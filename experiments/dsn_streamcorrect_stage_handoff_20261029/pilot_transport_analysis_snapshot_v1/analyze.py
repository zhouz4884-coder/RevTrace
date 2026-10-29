"""Bounded offline diagnostic of already completed source0 pilot, no model calls."""
from __future__ import annotations
import argparse,datetime,hashlib,json,pathlib,platform,statistics,subprocess,time

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stats(xs):
    xs=list(xs)
    return dict(n=len(xs),mean=statistics.mean(xs),median=statistics.median(xs),
                minimum=min(xs),maximum=max(xs),sum=sum(xs)) if xs else dict(n=0)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True)
    args=ap.parse_args();cfg=read(args.config);src=pathlib.Path(__file__).resolve().parent
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()
    assert commit==cfg['analysis_source_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    for name,h in cfg['analysis_source_files'].items(): assert digest(src/name)==h
    root=pathlib.Path(cfg['input_root']);out=pathlib.Path(cfg['out']);out.mkdir(exist_ok=False)
    begin=time.perf_counter();inputs=[]
    for name,h in cfg['input_files'].items():
        p=root/name;assert digest(p)==h;inputs.append(dict(path=str(p),sha256=h,bytes=p.stat().st_size))
    data={}
    for arm in ('two_full_spec_early','ready_handoff','two_full_early'):
        d=root/f'SC_STAGE_SERVICE_PILOT_V1_{arm}_source0_r0'
        s=read(d/'SUMMARY.json');f=read(d/'CONTENT_FRONTIERS.json')
        assert len(f)==17 and abs(sum(x['audio_seconds'] for x in f)-8.068)<1e-9
        assert sum(x['audio_seconds'] for x in f if x['original_dual_credit'])==s['primary']['dual_deadline_audio_credit_seconds']
        fidelity=read(d/'COMPLETE_TASK_FIDELITY.json')
        jobs=[json.loads(x) for x in (d/'native_jobs.jsonl').read_text(encoding='utf-8').splitlines()]
        records=[x['record'] for x in jobs if x.get('record')]
        item=dict(primary=s['primary'],fidelity=fidelity,energy=s['energy'],
            content=read(d/'CONTENT.json'),
            endpoints=[dict(frontier=x['frontier'],audio_seconds=x['audio_seconds'],D=x['D'],C=x['C'],
                            original_dual_credit=x['original_dual_credit'],row_class=x['raw']['first_visible_event_class']) for x in f],
            model_evaluated_jobs=sum(bool(x.get('native_model_evaluated')) for x in records),
            original_C_nonNone_jobs=sum(x.get('selected_correction') is not None for x in records),
            job_wall_seconds=stats(x['worker_job_wall_seconds'] for x in records),
            jobs_with_record=len(records),reported_counts={k:s[k] for k in (
                'authority_dispatches','actual_ready_hits','matching_inflight_fallbacks',
                'fullspec_inflight_promotions','fullspec_known_invalid_C_skips',
                'fullspec_discarded_full_results','producer_dispatches','wire_total_bytes')})
        data[arm]=item
    sd=root/'SC_STAGE_SERVICE_PILOT_V1_ready_handoff_source0_r0'
    admissions=read(sd/'STAGE_ADMISSIONS.json');p=[x for x in admissions if x['worker']=='producer']
    jobs=[json.loads(x) for x in (sd/'native_jobs.jsonl').read_text(encoding='utf-8').splitlines()]
    consumed=[x['record'] for x in jobs if x.get('record',{}).get('candidate_handoff')]
    phase={
        'actual_packet_capture':stats(x['packet_capture_seconds'] for x in p),
        'original_identity_tail_projection':stats(x['identity_projection_seconds'] for x in p),
        'json_wire_serialization':stats(x['wire_serialization_seconds'] for x in p),
        'queue_emission_to_parent_get_poll_and_transport':stats(x['received_perf']-x['wire_complete_perf'] for x in p),
        'parent_receipt_to_actual_admission':stats(x['admitted_perf']-x['received_perf'] for x in p),
        'producer_snapshot_to_actual_admission_including_projection':stats(x['admitted_perf']-x['produced_perf']+x['wire_serialization_seconds']+x['identity_projection_seconds']+x['packet_capture_seconds'] for x in p),
        'consumer_decode_verify':stats(x['wire_decode_verify_seconds'] for x in consumed),
        'consumer_input_match_and_open_restore':stats(x['input_match_open_restore_seconds'] for x in consumed),
        'consumer_original_C_U_tail':stats(x['original_C_U_tail_seconds'] for x in consumed),
        'consumer_worker_total_including_export':stats(x['worker_job_wall_seconds'] for x in consumed),
    }
    for v in phase.values(): assert v['n'] and v['minimum']>=0
    consumption=read(sd/'CONSUMPTIONS.json')
    assert len(consumption)==len(consumed)==data['ready_handoff']['reported_counts']['actual_ready_hits']
    for c in consumption:
        assert c['birth_epoch']==c['dispatch_epoch'] and c['birth_start_sha']==c['consume_start_sha']
        assert c['ready_perf']<=c['dispatch_perf'] and c['received_perf']<=c['ready_perf']
    inflight=read(sd/'MATCHING_INFLIGHT_OPPORTUNITIES.json')
    for x in inflight:
        assert x['same_full_input_and_epoch']
        x['producer_ready_lead_over_redundant_authority_ASR_seconds']=x['new_authority_ASR_ready_perf']-x['producer_ready_perf']
    result=dict(status='PASS_OFFLINE_PILOT_TRANSPORT_AND_ENDPOINT_DIAGNOSTICS',
        analysis_kind='offline actual-log diagnostics, not a new deployed experiment',
        arm_results=data,stage_wire_bytes=stats(x['candidate_wire_bytes'] for x in p),
        stage_timing_seconds=phase,ready_consumptions=consumption,matching_inflight=inflight,
        limitations=['one old development source and one fresh run per arm; not significance or independent generalization',
          'queue interval includes parent polling/backlog and serialization internal to multiprocessing; not pure network latency',
          'component medians are not additive; actual_snapshot_to_admission is measured per packet',
          'no counterfactual end-to-end join performance inferred from matching-inflight A-ready leads',
          'joint/fullspec is our assembled implementation and control, not published external baseline',
          'processed-frontier credit and LCP event credit are not word-aligned content correctness'])
    env=dict(python=platform.python_version(),platform=platform.platform(),model_calls=False,gpu_calls=False)
    record=dict(experiment_id=cfg['experiment_id'],config_sha256=digest(args.config),source_commit=commit,
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        elapsed_seconds=time.perf_counter()-begin,input_files=inputs,
        raw_result_location=str(root),summary_location=str(out/'SUMMARY.json'),gate_location=str(out/'GATE.json'))
    for name,obj in [('CONFIG.json',cfg),('ENVIRONMENT.json',env),('RUN_RECORD.json',record),('SUMMARY.json',result),('GATE.json',dict(status=result['status'],actual_service_rerun=False))]:
        (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],summary_sha256=digest(out/'SUMMARY.json'),output=str(out))))
if __name__=='__main__':main()
