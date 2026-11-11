"""Separate frozen CPU proof-audit entry; no imports from primary analysis."""
from pathlib import Path
import argparse,hashlib,io,json,platform,subprocess,sys,traceback,unittest
from independent_verify import check_bank

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def put(p,v):
 with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def source_gate(manifest):
 root=Path(__file__).resolve().parent
 g=lambda *x:subprocess.check_output(['git','-C',str(root),*x],text=True).strip()
 assert Path(g('rev-parse','--show-toplevel')).resolve()==root
 assert g('rev-parse','HEAD')==manifest['code_commit'] and not g('status','--porcelain','--untracked-files=all')
 assert set(g('ls-files').splitlines())=={x['path'] for x in manifest['files']}
 for r in manifest['files']:assert (root/r['path']).stat().st_size==r['bytes'] and sha(root/r['path'])==r['sha256']
def main():
 p=argparse.ArgumentParser()
 for k in ('config','manifest','environment','prelaunch','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();cfg=load(a.config);m=load(a.manifest);pre=load(a.prelaunch);source_gate(m)
 frozen_env=load(a.environment)
 assert frozen_env['python']==sys.version and frozen_env['executable']==sys.executable and frozen_env['platform']==platform.platform()
 before={str(x.resolve()):sha(x) for x in (a.config,a.manifest,a.environment,a.prelaunch)}
 assert pre['code_commit']==m['code_commit'] and pre['frozen_config_sha256']==sha(a.config)
 assert pre['source_manifest_sha256']==sha(a.manifest) and pre['environment_sha256']==sha(a.environment)
 assert str(a.out.resolve())==pre['raw_result_location'] and str(a.out).startswith(cfg['designated_experiment_disk_prefix']+'/')
 assert sha(pre['root_preflight_path'])==pre['root_preflight_sha256']
 assert load(pre['root_preflight_path'])['gate']=='SOURCE_IDENTITY_PASS'
 for x in cfg['bound_files']:assert sha(x['path'])==x['sha256']
 assert load(cfg['primary_results']+'/GATE.json')['status']=='PASS_ALL_INPUT_BYTES_AND_EDIT_CONSERVATION'
 a.out.mkdir(parents=True,exist_ok=False)
 put(a.out/'RUN_RECORD.json',dict(pre,experiment_id=cfg['experiment_id']))
 put(a.out/'ENVIRONMENT_ACTUAL.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),new_model_calls=0))
 try:
  stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent),pattern='test_independent.py')
  r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  (a.out/'CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
  assert r.testsRun==3 and r.wasSuccessful() and not r.skipped
  result=check_bank(cfg['primary_config'],cfg['primary_results']);result['independent_controls']=3
  for x in cfg['bound_files']:assert sha(x['path'])==x['sha256']
  for path,expected in before.items():assert sha(path)==expected
  assert sha(pre['root_preflight_path'])==pre['root_preflight_sha256']
  source_gate(m)
  put(a.out/'SUMMARY.json',result)
  put(a.out/'GATE.json',dict(status=result['status'],cells=result['cells'],checked_events=result['checked_events'],new_model_calls=0))
 except BaseException:
  put(a.out/'GATE.json',dict(status='FAIL_INDEPENDENT_AUDIT_PRESERVED',traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
