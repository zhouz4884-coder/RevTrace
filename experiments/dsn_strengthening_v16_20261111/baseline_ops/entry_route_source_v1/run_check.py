import argparse,datetime,hashlib,json,os,pathlib,platform,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
from entry_route import check_route
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','driver-source','driver-manifest','runtime-source','runtime-manifest','plan','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();m=read(a.manifest)
    def git(*s):return subprocess.check_output(['git','-C',str(R),*s],text=True).strip()
    assert git('rev-parse','HEAD')==m['source_commit'] and not git('status','--porcelain','--untracked-files=all')
    assert set(git('ls-files').splitlines())=={r['path'] for r in m['files']}
    for r in m['files']:assert (R/r['path']).stat().st_size==r['bytes'] and sha(R/r['path'])==r['sha256']
    assert os.environ.get('CUDA_VISIBLE_DEVICES')==''
    sys.path.insert(0,a.driver_source)
    from confirmation_common import verify_source,validate_matrix,RUNTIME,phase_arms
    driver=verify_source(a.driver_source,a.driver_manifest,'f367c4e1068a9391a0e99d8537c94995a3388e13');runtime=verify_source(a.runtime_source,a.runtime_manifest,RUNTIME)
    plan=read(a.plan);validate_matrix(plan['cells'],plan['sources'],plan['include_auxiliary'])
    configs=[]
    for cell in plan['cells']:
        assert sha(cell['config'])==cell['config_sha256'];cfg=read(cell['config']);assert cfg['settings']['source_commit']==RUNTIME;configs.append(cfg)
    out=pathlib.Path(a.out);assert str(out).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/');out.mkdir(parents=True,exist_ok=False)
    config=dict(experiment_id='DSN_V16_ACTUAL_PILOT_ENTRY_ROUTE_CPU_V1',source_commit=m['source_commit'],driver=driver,runtime=runtime,plan=dict(path=a.plan,sha256=sha(a.plan)),models_authorized=0,GPU_authorized=False)
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),CUDA_VISIBLE_DEVICES='')
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=m['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    result=check_route(a.driver_source,a.runtime_source,plan['cells'],configs)
    assert not any(k.split('.')[0] in ('torch','transformers','peft') for k in sys.modules)
    result.update(source_commit=m['source_commit'],model_calls=0,GPU_calls=0,driver_source_commit=driver['source_commit'],runtime_source_commit=runtime['source_commit']);put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=result['status'],summary_sha256=sha(out/'SUMMARY.json'),model_calls=0,GPU_calls=0));print(json.dumps({k:v for k,v in result.items() if k!='actual_argv'},indent=2))
if __name__=='__main__':main()
