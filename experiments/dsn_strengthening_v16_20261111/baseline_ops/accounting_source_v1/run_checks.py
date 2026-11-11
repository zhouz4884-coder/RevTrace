"""Pre-recorded CPU-only analysis-helper controls, no model/framework imports."""
import argparse,datetime,hashlib,importlib.abc,json,os,pathlib,platform,subprocess,sys,time,unittest
R=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
    assert not p.exists(),p
    p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def git(*args):return subprocess.check_output(['git','-C',str(R),*args],text=True).strip()
class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):
            raise ImportError('CPU accounting control prohibits neural import')
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    m=json.loads(a.manifest.read_bytes());assert git('rev-parse','HEAD')==m['source_commit'];assert not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert (R/r['path']).stat().st_size==r['bytes'] and sha(R/r['path'])==r['sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')=='' and os.environ.get('PYTHONPATH')==str(R)
    assert sys.version_info[:2]==(3,12)
    out=a.out.resolve();assert str(out).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/')
    out.mkdir(parents=True,exist_ok=False)
    cfg=dict(experiment_id='DSN_V16_DISJOINT_JOB_ACCOUNTING_CPU_V1',source_commit=m['source_commit'],source_root=str(R),source_manifest=str(a.manifest.resolve()),source_manifest_sha256=sha(a.manifest),runtime_under_audit='14ae77ee2f1f0c324be3f40b89fb6011972c35b9',scope='synthetic CPU analysis controls only; no actual service result')
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',PYTHONPATH=os.environ['PYTHONPATH'],model_imports='prohibited')
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    sys.meta_path.insert(0,NoNeural());start=time.perf_counter()
    with (out/'unittest.log').open('x',encoding='utf8') as f:
        suite=unittest.defaultTestLoader.loadTestsFromName('test_job_accounting')
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
    clean=not git('status','--porcelain','--untracked-files=all')
    ok=result.wasSuccessful() and not result.skipped and clean
    summary=dict(status='PASS_FROZEN_JOB_ACCOUNTING_CPU_ONLY' if ok else 'FAIL_JOB_ACCOUNTING_CPU_ONLY',experiment_id=cfg['experiment_id'],source_commit=m['source_commit'],tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),source_clean=clean,wall_seconds=time.perf_counter()-start,model_calls=0,GPU_calls=0)
    put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json')));print(json.dumps(summary,indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
