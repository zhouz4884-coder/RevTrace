"""Run frozen structural checks against complete actual native trace files."""
import argparse,datetime,hashlib,json,pathlib,platform,subprocess,sys,unittest,io,traceback
from refinement_trace import audit,read_frames,lines,check_original_ingress,wire,audit_local_rejections,audit_worker_replacements,check_dispatch_arrivals

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True)
    p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
    a=p.parse_args();source=pathlib.Path(__file__).resolve().parent;cfg=json.loads(a.config.read_bytes());m=json.loads(a.manifest.read_bytes())
    commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    assert commit==m['source_commit']==cfg['checker_source_commit']
    assert sha(a.manifest)==cfg['checker_manifest_sha256']
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=all'],text=True).strip()
    assert set(subprocess.check_output(['git','-C',str(source),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert (source/r['path']).stat().st_size==r['bytes'] and sha(source/r['path'])==r['sha256']
    a.out.mkdir(parents=True,exist_ok=False)
    def put(n,x):(a.out/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    put('CONFIG.json',cfg);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,scope='CPU structural trace validation, no model replay'))
    put('RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.out/'CONFIG.json'),
        frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),
        environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=cfg.get('case_root',str(a.out/'CPU_CONTROLS.log')),
        aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),
        started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_model_calls=0))
    try:
        stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(source),pattern='test_*.py'))
        (a.out/'CPU_CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
        assert result.wasSuccessful() and not result.skipped,'trace checker source controls failed'
        if cfg['mode']=='controls':
            summary=dict(status='PASS_SYNTHETIC_TRACE_CHECKER_CONTROLS_ONLY',tests=result.testsRun,skips=0,
                checker_source_commit=commit,model_calls=0,actual_serving_trace_checked=False)
        else:
            assert cfg['mode']=='actual_complete_trace'
            root=pathlib.Path(cfg['case_root']);inputs=cfg['inputs']
            def load(p):
                p=pathlib.Path(p).resolve();k=str(p);r=inputs[k]
                assert not p.is_symlink() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
                return p
            run_config=json.loads(load(cfg['runtime_config']).read_bytes());expected=cfg['actual_runtime_source_commit']
            assert run_config['settings']['source_commit']==expected
            frames,frame_meta=read_frames(load(cfg['fact_journal']),cfg.get('allow_incomplete_uncommitted_tail',False))
            need_hash=hashlib.sha256(wire(run_config)).hexdigest()
            assert frames[0][0]['body']['metadata']['config_sha256']==need_hash,'journal config differs from original frozen trial'
            dirs=sorted(root.glob('owner_e*'),key=lambda p:int(p.name.removeprefix('owner_e')))
            assert [str(p.resolve()) for p in dirs]==cfg['owner_directories'],'actual attempt set changed or omitted'
            dispatch=[];completions=[];owner_events={};policy_audits={}
            for directory in dirs:
                epoch=int(directory.name.removeprefix('owner_e'))
                for row in lines(load(directory/'dispatch.jsonl')):
                    assert row['owner_epoch']==epoch
                    dispatch.append(row)
                for row in lines(load(directory/'worker_results.jsonl')):
                    assert 'owner_epoch' not in row or row['owner_epoch']==epoch
                    completions.append(dict(row,owner_epoch=epoch))
                owner_events[epoch]=list(lines(load(directory/'owner_events.jsonl')))
                policy_audits[epoch]=list(lines(load(directory/'policy_audit.jsonl')))
            pubs=list(lines(load(cfg['publication_journal'])));consumer=list(lines(load(cfg['consumer_journal'])))
            sources=run_config['settings']['sources']
            summary=audit(frames=frames,dispatch_rows=dispatch,completion_rows=completions,publication_rows=pubs,
                consumer_rows=consumer,expected_runtime_commit=expected,
                expected_final_frontiers={s['source_id']:s['frames'] for s in sources})
            origin_obj=json.loads(load(cfg['origin_record']).read_bytes())
            origin=origin_obj['origin'] if 'origin' in origin_obj else origin_obj['origin_perf']
            ingress=check_original_ingress(origin=origin,sources=sources,ingress_rows=list(lines(load(cfg['ingress_journal']))))
            arrivals=check_dispatch_arrivals(origin,dispatch)
            rejections=audit_local_rejections(dispatch_rows=dispatch,owner_event_groups=owner_events,policy_audit_groups=policy_audits)
            physical=audit_worker_replacements(owner_event_groups=owner_events,dispatch_rows=dispatch)
            summary.update(checker_source_commit=commit,actual_runtime_source_commit=expected,CPU_controls=result.testsRun,
                independent_frame_scan=frame_meta,original_ingress=ingress,dispatch_original_arrivals=arrivals,
                legal_progress_wrong_rejections=rejections['legal_progress_wrong_rejections'],local_rejection_audit=rejections,
                worker_only_physical_replacement_audit=physical)
            for path,row in inputs.items():assert pathlib.Path(path).stat().st_size==row['bytes'] and sha(path)==row['sha256'],'immutable trace input changed'
            put('INPUT_MANIFEST.json',inputs)
        put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(summary,indent=2))
    except BaseException:
        (a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
        put('GATE.json',dict(status='FAIL_TRACE_REFINEMENT_OR_CONTROL_PRESERVED',checker_source_commit=commit,new_model_calls=0));raise

if __name__=='__main__':main()

