"""Frozen-source/environment/import-only CPU gate; no torch/model construction."""
import argparse,datetime,hashlib,importlib,importlib.metadata,json,os,pathlib,platform,subprocess,sys,unittest
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();cfg=read(a.config)
    os.environ['CUDA_VISIBLE_DEVICES']='';src=pathlib.Path(__file__).resolve().parent
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=src,text=True).strip()==cfg['profile_source_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=src,text=True).strip()
    for name,h in cfg['profile_source_files'].items():assert sha(src/name)==h
    for p,h in cfg['frozen_input_files'].items():assert sha(p)==h
    runtime=pathlib.Path(cfg['imported_runtime_root']);m=read(cfg['imported_runtime_manifest']);assert sha(cfg['imported_runtime_manifest'])==cfg['imported_runtime_manifest_sha256']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()==cfg['imported_runtime_commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=runtime,text=True).strip()
    for f in m['files']:assert sha(runtime/f['path'])==f['sha256']
    sys.path.insert(0,str(runtime))
    for name in ('candidate_bridge','feedback_contract','native_bridge','native_tail'):
        module=importlib.import_module(name);assert pathlib.Path(module.__file__).resolve().parent==runtime.resolve()
    assert 'torch' not in sys.modules,'CPU import must not construct/import neural runtime'
    if platform.system()=='Linux':assert {k:importlib.metadata.version(k) for k in cfg['expected_packages']}==cfg['expected_packages']
    suite=unittest.defaultTestLoader.discover(str(src),pattern='test_*.py');r=unittest.TextTestRunner(verbosity=2).run(suite)
    assert r.wasSuccessful() and not r.skipped and r.testsRun==17
    a.out.mkdir(exist_ok=False)
    status=dict(status='PASS_17_CPU_CONTROLS_AND_COMPLETE_SOURCE_ENVIRONMENT_IMPORT_GATE',tests=r.testsRun,skips=0,model_calls=0,gpu_calls=0,source_commit=cfg['profile_source_commit'],runtime_commit=cfg['imported_runtime_commit'])
    for name,x in [('GATE.json',status),('CONFIG.json',cfg),('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),cuda_visible_devices='',torch_imported=False)),('RUN_RECORD.json',dict(experiment_id=cfg['experiment_id']+'_CPU_GATE',source_commit=cfg['profile_source_commit'],config_sha256=sha(a.config),utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw=str(a.out),gate=str(a.out/'GATE.json')))]:
        (a.out/name).write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(status))
if __name__=='__main__':main()
