"""Frozen-runtime CPU protocol gate. Importing neural frameworks is forbidden."""
import argparse,datetime,hashlib,importlib.abc,importlib.metadata,json,os,pathlib,platform,re,subprocess,sys,time,traceback,unittest

BLOCKED=frozenset(('torch','transformers','peft','whisper','simul_whisper','qwen_asr','librosa'))
class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise ImportError('formal CPU-only gate forbids neural-framework import: '+fullname)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,obj):
    assert not p.exists(),p
    p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);a=ap.parse_args()
    cfg=json.loads(a.config.read_bytes());out=pathlib.Path(cfg['raw_result_location']);source=pathlib.Path(cfg['source_root']);manifest=pathlib.Path(cfg['source_manifest'])
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    assert os.environ.get('PYTHONPATH')==str(source)
    assert sys.version_info[:2]==(3,12)
    assert sha(manifest)==cfg['source_manifest_sha256']
    assert sha(pathlib.Path(__file__))==cfg['cpu_gate_sha256']
    assert not any(k.split('.')[0] in BLOCKED for k in sys.modules)
    sys.meta_path.insert(0,NoNeuralImports())
    sys.path.insert(0,str(source))
    from native_service import verify_source
    identity=verify_source(manifest);put(out/'SOURCE_GATE_BEFORE.json',identity)
    assert identity['source_commit']==cfg['source_commit']
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.perf_counter()
    result=None;failure=None
    with (out/'unittest.log').open('x',encoding='utf8') as stream:
        try:
            suite=unittest.defaultTestLoader.loadTestsFromNames(cfg['test_modules'])
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        except BaseException:
            failure=traceback.format_exc();stream.write(failure)
    imported=sorted(k for k in sys.modules if k.split('.')[0] in BLOCKED)
    after=verify_source(manifest);put(out/'SOURCE_GATE_AFTER.json',after)
    passed=result is not None and result.wasSuccessful() and not result.skipped and not imported
    summary=dict(status='PASS_FROZEN_NATIVE_POLICY_PROTOCOL_CPU_ONLY' if passed else 'FAIL_FROZEN_NATIVE_POLICY_PROTOCOL_CPU_ONLY',
        experiment_id=cfg['experiment_id'],actual_source_commit=cfg['source_commit'],
        source_manifest_sha256=cfg['source_manifest_sha256'],started_utc=started,
        ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.perf_counter()-begin,
        tests=None if result is None else result.testsRun,errors=None if result is None else len(result.errors),
        failures=None if result is None else len(result.failures),skipped=None if result is None else len(result.skipped),
        blocked_neural_packages_imported=imported,model_calls=0,GPU_calls=0,CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),
        source_clean_before_and_after=identity==after,test_modules=cfg['test_modules'],failure=failure,
        scope='CPU synthetic protocol, real CPU process/Pipe, Owner/FactStore/Consumer controls only; not neural equivalence or GPU/service performance')
    put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json'),actual_source_commit=cfg['source_commit'],model_calls=0,GPU_calls=0))
    print(json.dumps(summary,indent=2));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
