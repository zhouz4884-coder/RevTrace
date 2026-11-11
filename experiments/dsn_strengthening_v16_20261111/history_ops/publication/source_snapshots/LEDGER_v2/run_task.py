"""Frozen standard-library CPU entry with complete preregistration and byte gates."""
from pathlib import Path
import argparse,hashlib,importlib,io,json,platform,subprocess,sys,traceback,unittest
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def source_gate(m):
 root=Path(__file__).resolve().parent;g=lambda *x:subprocess.check_output(['git','-C',str(root),*x],text=True).strip()
 assert Path(g('rev-parse','--show-toplevel')).resolve()==root and g('rev-parse','HEAD')==m['code_commit']
 assert not g('status','--porcelain','--untracked-files=all') and set(g('ls-files').splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:assert sha(root/r['path'])==r['sha256'] and (root/r['path']).stat().st_size==r['bytes']
def main():
 p=argparse.ArgumentParser()
 for k in ('config','manifest','environment','prelaunch','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();cfg=load(a.config);m=load(a.manifest);pre=load(a.prelaunch);env=load(a.environment);source_gate(m)
 assert pre['experiment_id']==cfg['experiment_id'] and pre['code_commit']==m['code_commit']
 assert pre['source_manifest_sha256']==sha(a.manifest) and pre['frozen_config_sha256']==sha(a.config) and pre['environment_sha256']==sha(a.environment)
 assert env['python']==sys.version and env['executable']==sys.executable and env['platform']==platform.platform()
 assert str(a.out.resolve())==pre['raw_result_location'] and str(a.out).startswith(cfg['designated_experiment_disk_prefix']+'/')
 assert sha(pre['root_preflight_path'])==pre['root_preflight_sha256'] and load(pre['root_preflight_path'])['gate']=='SOURCE_IDENTITY_PASS'
 before={str(x.resolve()):sha(x) for x in (a.config,a.manifest,a.environment,a.prelaunch,Path(pre['root_preflight_path']))}
 for spec in cfg['bound_files']:assert sha(spec['path'])==spec['sha256']
 a.out.mkdir(parents=True,exist_ok=False);put(a.out/'RUN_RECORD.json',pre);put(a.out/'CONFIG.json',cfg);put(a.out/'ENVIRONMENT.json',env)
 try:
  stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent),pattern='test_*.py')
  controls=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  (a.out/'CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
  assert controls.testsRun==cfg['expected_controls'] and controls.wasSuccessful() and not controls.skipped
  module=importlib.import_module(cfg['analysis_module']);result=module.analyze(cfg,a.out);result['CPU_controls']=controls.testsRun
  for spec in cfg['bound_files']:assert sha(spec['path'])==spec['sha256']
  for path,expected in before.items():assert sha(path)==expected
  source_gate(m);put(a.out/'SUMMARY.json',result);put(a.out/'GATE.json',dict(status=result['status'],source_commit=m['code_commit'],new_model_calls=0))
 except BaseException:
  put(a.out/'GATE.json',dict(status='FAIL_PRESERVED_CPU_TASK',traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
