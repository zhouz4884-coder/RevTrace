"""Thirteen fixed original-infer calls; all claims are component/oracle evidence."""
import argparse,datetime,hashlib,json,multiprocessing as mp,pathlib,statistics,subprocess,sys,time,traceback
from encoder_wire import decode
from profile_worker import worker_main

def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def audit(result,expected):
    return dict(full_infer_completed=result.get('full_infer_completed') is True,
        complete_closed_cut_equal=result.get('end')==expected['end'],
        returned_ids_equal=result.get('record',{}).get('token_ids')==expected['token_ids'],
        selected_C_equal=result.get('record',{}).get('selected_correction')==expected['selected_correction'])
def all_true(x):return bool(x) and all(v is True for v in x.values())
def check_provenance(header,receipt,command,gpu):
    p=header['execution_provenance']
    if receipt['physical_channel_gpu']!=gpu or receipt['gpu']!=gpu:raise ValueError('physical channel ownership')
    if p['worker_gpu']!=gpu or p['job_id']!=command['job_id']:raise ValueError('owned producer job')
    if p['source_id']!=command['source_id'] or p['target']!=command['end']:raise ValueError('owned source/target')
    if p['full_birth_start_sha']!=receipt['frozen_start_sha']:raise ValueError('original execution birth')
def economics(pairs):
    # Four measured payloads estimate costs of retaining all14 predeclared jobs.
    production=[p['wrong']['encoder']['actual_capture_export_seconds']+p['wrong']['encoder']['mel_hash_seconds']+
        p['producer_to_parent_receipt_seconds']+p['parent_wire_decode_seconds'] for p in pairs]
    consumed=[p['received']['command_received_perf']-p['received']['parent_dispatch_perf']+
        p['received']['encoder']['actual_import_verify_finite_seconds']+p['received']['encoder']['mel_hash_seconds'] for p in pairs]
    e=[p['baseline']['encoder']['encoder_seconds'] for p in pairs]
    production14=statistics.mean(production)*14;consumption4=sum(consumed);saved4=sum(e)
    return dict(scope='component-based estimate at fixed observed4/14 use rate, not deployed gain',
        measured_original_E_seconds=e,measured_capture_route_seconds=production,
        measured_consume_route_seconds=consumed,expected_all14_capture_and_export_seconds=production14,
        actual_four_consume_routes_seconds=consumption4,four_original_E_compute_seconds=saved4,
        expected_net_work_margin_seconds=saved4-production14-consumption4,
        plausible_compute_margin_at_least_100ms=saved4-production14-consumption4>=.100,
        limitation='Sums do not model overlap, altered dispatch order, release waits or downstream service. Positive margin requires root review and eventual service test.')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.config)
    src=pathlib.Path(__file__).resolve().parent
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==cfg['profile_source_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    for name,h in cfg['profile_source_files'].items():assert sha(src/name)==h
    runtime=pathlib.Path(cfg['imported_runtime_root']);manifest=read(cfg['imported_runtime_manifest'])
    assert sha(cfg['imported_runtime_manifest'])==cfg['imported_runtime_manifest_sha256']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()==cfg['imported_runtime_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=runtime,text=True).strip()
    for f in manifest['files']:assert sha(runtime/f['path'])==f['sha256']
    for path,h in cfg['frozen_input_files'].items():assert sha(path)==h
    out=pathlib.Path(cfg['out']);out.mkdir(exist_ok=False);(out/'features').mkdir();(out/'calls').mkdir()
    save(out/'CONFIG.json',cfg);save(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],profile_source_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit'],environment_sha256=cfg['environment_sha256'],config_sha256=sha(a.config),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw=str(out),summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json')))
    ctx=mp.get_context('spawn');commands={g:ctx.Queue() for g in (0,1)};results={g:ctx.Queue() for g in (0,1)}
    procs={g:ctx.Process(target=worker_main,args=(g,cfg,commands[g],results[g]),name=f'encoder_profile_gpu{g}') for g in (0,1)}
    calls=[];pairs=[];ready={};completed=False
    def get(g,kind,job=None):
        r=results[g].get(timeout=240);r['parent_received_perf']=time.perf_counter();r['physical_channel_gpu']=g
        assert r['gpu']==g and r['kind']!='failed',r
        assert r['kind']==kind and (job is None or r['job_id']==job)
        return r
    def call(g,cmd):
        cmd=dict(cmd,parent_dispatch_perf=time.perf_counter());commands[g].put(cmd)
        r=get(g,'completed',cmd['job_id']);wire=r.pop('wire',None)
        if wire is not None:
            t=time.perf_counter();header,_=decode(wire,expected_identity=ready[g]['identity']);done=time.perf_counter()
            check_provenance(header,r,cmd,g)
            r['parent_wire_decode_seconds']=done-t
            r['producer_to_parent_receipt_seconds']=r['parent_received_perf']-r['sent_perf']
            fp=out/'features'/f"{cmd['job_id']}.bin";fp.write_bytes(wire);r['feature_file']=str(fp);r['feature_file_sha256']=sha(fp)
        calls.append(r);save(out/'calls'/f"{cmd['job_id']}.json",r)
        save(out/'PROGRESS.json',dict(completed_original_infer_calls=len(calls),expected_calls=13,last_job=cmd['job_id']))
        return r,wire
    try:
        for p in procs.values():p.start()
        for g in (0,1):ready[g]=get(g,'ready')
        assert ready[0]['identity']==ready[1]['identity'];save(out/'READY.json',ready)
        save(out/'ENVIRONMENT.json',dict(frozen_reference_sha256=cfg['environment_sha256'],workers={g:ready[g]['environment'] for g in ready},source_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit']))
        for pair in cfg['pairs']:
            common=dict(source_id=pair['source_id'],end=pair['end'],is_last=pair['is_last'])
            wrong,wire=call(pair['old_gpu'],dict(common,kind='wrong_E_only',job_id=pair['pair_id']+'_wrongE',start=pair['wrong_start']))
            assert wire and wrong['encoder_only'] and not wrong['feedback_cut_emitted']
            baseline,_=call(pair['new_gpu'],dict(common,kind='original_full',job_id=pair['pair_id']+'_originalFull',start=pair['correct_start']))
            consumed,_=call(pair['new_gpu'],dict(common,kind='received_E_full',job_id=pair['pair_id']+'_receivedEFull',start=pair['correct_start'],wire=wire))
            checks=dict(actual_mel_bits_equal=wrong['encoder']['actual_mel_sha256']==baseline['encoder']['actual_mel_sha256']==consumed['encoder']['actual_mel_sha256'],
                actual_E_bits_equal=wrong['encoder']['feature_sha256']==baseline['encoder']['feature_sha256']==consumed['encoder']['feature_sha256'],
                all_actual_tensors_finite=all(x['encoder']['mel_finite'] and x['encoder']['feature_finite'] for x in (wrong,baseline,consumed)),
                baseline_complete_oracle=all_true(audit(baseline,pair['original_reference'])),
                received_complete_oracle=all_true(audit(consumed,pair['original_reference'])))
            p=dict(pair_id=pair['pair_id'],wrong=wrong,baseline=baseline,received=consumed,checks=checks,
                producer_to_parent_receipt_seconds=wrong['producer_to_parent_receipt_seconds'],parent_wire_decode_seconds=wrong['parent_wire_decode_seconds'],
                old_trace_wrong_begin_to_fallback_model_start_seconds=pair['old_fallback_model_start']-pair['old_wrong_worker_begin'],
                current_component_wrong_begin_to_E_complete_seconds=wrong['encoder']['encoder_return_perf']-wrong['worker_job_begin_perf'],
                readiness_scope='Current component timestamps only; overlay on old service timing is hypothetical, not an actual deployed readiness observation')
            pairs.append(p);save(out/'PAIRS_PARTIAL.json',pairs)
        eos=cfg['pairs'][-1]
        repeat,_=call(eos['new_gpu'],dict(kind='original_full',job_id='EOS_fixed_original_full_repeat',source_id=eos['source_id'],start=eos['correct_start'],end=eos['end'],is_last=True))
        repeat_check=audit(repeat,eos['original_reference'])
        for g in (0,1):commands[g].put(None)
        for g in (0,1):get(g,'stopped')
        for p in procs.values():p.join(timeout=30);assert not p.is_alive() and p.exitcode==0
        fidelity=all(all_true(p['checks']) for p in pairs) and all_true(repeat_check)
        cost=economics(pairs)
        summary=dict(status='PASS_COMPLETE_13_COMPONENT_CALLS_AND_NEURAL_ORACLES' if fidelity else 'FAIL_COMPLETE_COMPONENT_NEURAL_FIDELITY',
            actual_original_infer_calls=len(calls),pairs=pairs,EOS_fixed_repeat=repeat_check,economics=cost,
            decision='GO_BOUNDED_IMPLEMENTATION_REVIEW_ONLY' if fidelity and cost['expected_net_work_margin_seconds']>0 and cost['plausible_compute_margin_at_least_100ms'] else 'STOP_NO_NET_PROFILE_OPPORTUNITY_OR_FIDELITY_FAILURE',
            no_live_encoder_cache=True,no_deployed_service_test=True,model_load_and_warmup_separate=True,
            imported_runtime_unchanged=True,source_commit=cfg['profile_source_commit'],imported_runtime_commit=cfg['imported_runtime_commit'])
        save(out/'SUMMARY.json',summary);save(out/'GATE.json',dict(status=summary['status'],decision=summary['decision'],calls=len(calls),all_workers_exited=True,scope='component/oracle; no deployed throughput, latency, SLO or E-readiness claim'));completed=True
        print(json.dumps(dict(status=summary['status'],decision=summary['decision'],expected_net_work_margin_seconds=cost['expected_net_work_margin_seconds']),ensure_ascii=False),flush=True)
    except BaseException as exc:
        save(out/'FAILURE.json',dict(type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),completed_calls=len(calls)))
        save(out/'GATE.json',dict(status='FAIL_TECHNICAL_COMPONENT_EXECUTION',completed_calls=len(calls)))
        raise
    finally:
        if not completed:
            for p in procs.values():
                if p.is_alive():p.terminate()
            for p in procs.values():p.join(timeout=10)
if __name__=='__main__':main()
