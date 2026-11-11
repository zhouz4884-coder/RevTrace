"""Full frozen pilot/reference CPU control gate; no neural imports or GPU work."""
import argparse,ast,datetime,importlib.abc,json,os,pathlib,platform,sys,time,unittest
from confirmation_common import verify_source,RUNTIME,SUPPORT,sha,put
R=pathlib.Path(__file__).resolve().parent
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):
            raise ImportError('CPU pilot/reference control forbids neural import')
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    own=verify_source(R,a.manifest)
    runtime_source=B/'projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v2/source'
    runtime_manifest=runtime_source.parent/'SOURCE.json'
    base=verify_source(runtime_source,runtime_manifest,RUNTIME)
    support_source=B/'projects/revtrace_dsn_strengthening_20261031/paired_resident_source_v2'
    support_manifest=support_source.parent/'PAIRED_RESIDENT_SOURCE_v2.json'
    support=verify_source(support_source,support_manifest,SUPPORT)
    need_env=os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.environ.get('PYTHONPATH')==str(R)
    assert need_env and sys.version_info[:2]==(3,12)
    out=pathlib.Path(a.out).resolve();assert out.is_relative_to(B);out.mkdir(parents=True,exist_ok=False);(out/'tmp').mkdir()
    os.environ['TMPDIR']=str(out/'tmp');sys.path.append(str(runtime_source))
    modules=['test_confirmation_controls','test_reference_controls','test_job_accounting','test_pilot_bindings']
    cfg=dict(experiment_id='DSN_V16_PILOT_REFERENCE_DRIVER_CPU_V1',driver=own,actual_NN=base,support=support,test_modules=modules,scope='metadata, matrix, reference rejection, raw synthetic Owner/accounting and prelaunch controls only',model_calls=0,GPU_calls=0)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.environ['PYTHONPATH'],runtime_python_path=str(runtime_source),neural_imports='forbidden')
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=own['source_commit'],actual_NN_source_commit=RUNTIME,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    sys.meta_path.insert(0,NoNeural());start=time.perf_counter()
    parsed=[]
    for path in sorted(R.glob('*.py')):ast.parse(path.read_text(encoding='utf8'),filename=str(path));parsed.append(path.name)
    with (out/'unittest.log').open('x',encoding='utf8') as f:
        tests=unittest.defaultTestLoader.loadTestsFromNames(modules);result=unittest.TextTestRunner(stream=f,verbosity=2).run(tests)
    verify_source(R,a.manifest,own['source_commit']);verify_source(runtime_source,runtime_manifest,RUNTIME);verify_source(support_source,support_manifest,SUPPORT)
    loaded=sorted(k for k in sys.modules if k.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'))
    ok=result.wasSuccessful() and not result.skipped and not loaded
    summary=dict(status='PASS_FROZEN_PILOT_REFERENCE_DRIVER_CPU_ONLY' if ok else 'FAIL_PILOT_REFERENCE_DRIVER_CPU_ONLY',driver_source_commit=own['source_commit'],actual_NN_source_commit=RUNTIME,tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),all_source_identities_clean=True,ast_parsed=parsed,neural_packages_loaded=loaded,wall_seconds=time.perf_counter()-start,model_calls=0,GPU_calls=0,scope=cfg['scope'])
    put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json')));print(json.dumps(summary,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
