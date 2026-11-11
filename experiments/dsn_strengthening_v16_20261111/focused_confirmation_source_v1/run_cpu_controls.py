import argparse,ast,datetime,importlib.abc,os,pathlib,platform,sys,time,unittest,json
from confirmation_common import verify_source,RUNTIME,SUPPORT,sha,put
from focused_common import REFERENCE_GENERATOR
R=pathlib.Path(__file__).resolve().parent;B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):raise ImportError('focused CPU control forbids neural imports')
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();own=verify_source(R,a.manifest)
    rt=B/'projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3/source';support=B/'projects/revtrace_dsn_strengthening_20261031/paired_resident_source_v2';generator=B/'projects/revtrace_dsn_strengthening_v16_20261111/pilot_driver_v2/source'
    base=verify_source(rt,rt.parent/'SOURCE.json',RUNTIME);sp=verify_source(support,support.parent/'PAIRED_RESIDENT_SOURCE_v2.json',SUPPORT);gen=verify_source(generator,generator.parent/'SOURCE.json',REFERENCE_GENERATOR)
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.environ.get('PYTHONPATH')==str(R) and sys.version_info[:2]==(3,12)
    out=pathlib.Path(a.out);assert out.resolve().is_relative_to(B);out.mkdir(parents=True,exist_ok=False);(out/'tmp').mkdir();os.environ['TMPDIR']=str(out/'tmp')
    cfg=dict(experiment_id='DSN_V16_FOCUSED_FULL_READY_CONFIRMATION_CPU_V1',driver=own,actual_NN=base,support=sp,reference_generator=gen,scope='declared bank-slice/reference negatives, two-arm matrix and actual CPU Owner/publication-Pipe/Consumer/WAL fixture only')
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.environ['PYTHONPATH']);put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=own['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    sys.path.extend([str(support),str(rt)]);sys.meta_path.insert(0,NoNeural());start=time.perf_counter()
    for f in R.glob('*.py'):ast.parse(f.read_text(encoding='utf8'),filename=str(f))
    with (out/'unittest.log').open('x',encoding='utf8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['test_focused_controls','test_reference_subset']))
    verify_source(R,a.manifest,own['source_commit']);ok=result.wasSuccessful() and not result.skipped
    summary=dict(status='PASS_FOCUSED_CONFIRMATION_CPU_ONLY' if ok else 'FAIL_FOCUSED_CONFIRMATION_CPU_PRESERVED',source_commit=own['source_commit'],actual_NN_source_commit=RUNTIME,reference_generator_source_commit=REFERENCE_GENERATOR,tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),wall_seconds=time.perf_counter()-start,model_calls=0,GPU_calls=0);put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json')));print(json.dumps(summary,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
