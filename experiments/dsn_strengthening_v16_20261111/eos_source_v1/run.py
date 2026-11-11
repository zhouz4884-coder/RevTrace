import argparse,hashlib,io,json,os,pathlib,platform,subprocess,sys,traceback,unittest
from core import analyze,sha
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();root=pathlib.Path(__file__).resolve().parent
 cfg=json.loads(a.config.read_bytes());m=json.loads(a.manifest.read_bytes());commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip();assert commit==m['code_commit']==cfg['source_commit'];assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip()
 assert set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:assert sha(root/r['path'])==r['sha256'] and (root/r['path']).stat().st_size==r['bytes']
 assert sha(a.manifest)==cfg['source_manifest_sha256'] and os.environ.get('CUDA_VISIBLE_DEVICES')==''
 a.out.mkdir(parents=True,exist_ok=False)
 def put(n,x):(a.out/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
 put('CONFIG.json',cfg);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0))
 put('RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
 try:
  stream=io.StringIO();t=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.discover(str(root),pattern='test_*.py'));(a.out/'CONTROLS.log').write_text(stream.getvalue());assert t.wasSuccessful() and not t.skipped and t.testsRun==4
  result=analyze(cfg)
  for c in cfg['cells']:
   for spec in c['files'].values():assert sha(spec['path'])==spec['sha256']
  assert sha(cfg['reference_config']['path'])==cfg['reference_config']['sha256']
  result.update(analysis_source_commit=commit,source_manifest_sha256=sha(a.manifest),controls=4,skipped=0)
  put('SUMMARY.json',result);put('GATE.json',dict(status=result['status'],source_commit=commit,summary_sha256=sha(a.out/'SUMMARY.json'),new_model_calls=0,GPU_calls=0));print(json.dumps(dict(status=result['status'],cells=len(result['cells']),arms=result['arms']),indent=2))
 except BaseException:
  (a.out/'failure.txt').write_text(traceback.format_exc());put('GATE.json',dict(status='FAIL_EOS_DIAGNOSTIC_PRESERVED',source_commit=commit));raise
if __name__=='__main__':main()
