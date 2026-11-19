"""Explicit-source CPU-only workload gate; complete records, no neural imports."""
from __future__ import annotations
import argparse,ast,datetime,importlib.abc,json,os,pathlib,platform,sys,tempfile,time,traceback,unittest
from confirmation_common import RUNTIME,SUPPORT,verify_source,need,sha,put,disk
from workload_interop_controls import PREP_COMMIT,run_fixture

class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):
            raise ImportError('CPU workload controls forbid neural imports')

def main():
    p=argparse.ArgumentParser()
    for name in ('manifest','base-source','base-manifest','support-source','support-manifest','prep-source','prep-manifest','out'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();root=pathlib.Path(__file__).resolve().parent
    own=verify_source(root,a.manifest);base=verify_source(a.base_source,a.base_manifest,RUNTIME)
    support=verify_source(a.support_source,a.support_manifest,SUPPORT)
    prep=verify_source(a.prep_source,a.prep_manifest,PREP_COMMIT)
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU-only CUDA visibility must be explicit')
    out=disk(a.out);out.mkdir(parents=True,exist_ok=False);(out/'tmp').mkdir()
    tempfile.tempdir=str(out/'tmp')
    modules=['test_confirmation_controls','test_reference_controls','test_job_accounting',
        'test_pilot_bindings','test_reference_subset','test_native_factorial','test_workload_controls']
    config=dict(experiment_id='DSN_MD68_WORKLOAD_DRIVER_CPU_V1',driver=own,actual_NN=base,
        production_support=support,metadata_preparer=prep,test_modules=modules,
        cross_source_fixture=True,model_calls=0,GPU_calls=0,
        scope='Metadata/corpus/reference/controller/raw synthetic Owner controls only; no dataset service or neural reference')
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
        CUDA_VISIBLE_DEVICES='',neural_imports='forbidden',temporary_fixture_root=tempfile.tempdir)
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=own['source_commit'],
        actual_NN_source_commit=RUNTIME,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),
        environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),
        raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),
        prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    start=time.perf_counter();sys.path.append(base['source_root']);sys.meta_path.insert(0,NoNeural())
    try:
        parsed=[]
        for path in sorted(root.glob('*.py')):
            ast.parse(path.read_text(encoding='utf8'),filename=str(path));parsed.append(path.name)
        with (out/'unittest.log').open('x',encoding='utf8') as stream:
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
        need(result.wasSuccessful() and not result.skipped,'CPU controls failed; preserve complete log')
        interop=run_fixture(prep['source_root']);put(out/'CROSS_SOURCE_FIXTURE.json',interop)
        for identity in (own,base,support,prep):
            need(verify_source(identity['source_root'],identity['source_manifest'],identity['source_commit'])==identity,
                 'source changed during CPU controls')
        loaded=sorted(k for k in sys.modules if k.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'))
        need(not loaded,'neural package loaded during CPU controls')
        summary=dict(status='PASS_FROZEN_ORIGINAL_MD68_WORKLOAD_DRIVER_CPU_ONLY',
            driver_source_commit=own['source_commit'],actual_NN_source_commit=RUNTIME,
            unit_tests=result.testsRun,cross_source_fixture=interop['status'],errors=0,failures=0,skipped=0,
            all_sources_clean=True,ast_parsed=parsed,neural_packages_loaded=loaded,
            wall_seconds=time.perf_counter()-start,model_calls=0,GPU_calls=0,scope=config['scope'])
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json')))
        print(json.dumps(summary,indent=2));return 0
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_WORKLOAD_CPU_CONTROLS_PRESERVED',failure=traceback.format_exc(),model_calls=0,GPU_calls=0))
        raise

if __name__=='__main__':raise SystemExit(main())
