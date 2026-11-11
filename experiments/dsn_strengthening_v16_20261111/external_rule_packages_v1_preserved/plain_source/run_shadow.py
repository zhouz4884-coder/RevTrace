"""Formal CPU entry; requires new root noarg and explicit-source receipts."""
from pathlib import Path
import argparse,importlib.metadata,io,platform,sys,traceback,unittest
from provenance import *

def main():
    p=argparse.ArgumentParser()
    for k in ('config','manifest','environment','prelaunch','out'):p.add_argument('--'+k,required=True)
    a=p.parse_args();cfg=read(a.config);pre=read(a.prelaunch);env=read(a.environment);idle(cfg['idle_receipt'])
    own=source(Path(__file__).resolve().parent,a.manifest,cfg['actual_analysis_source']['code_commit'])
    if cfg['experiment_id']!=EXPERIMENT or pre['experiment_id']!=EXPERIMENT:raise ValueError('experiment ID changed')
    for key,value in (('code_commit',own['code_commit']),('source_manifest_sha256',sha(a.manifest)),('frozen_config_sha256',sha(a.config)),('environment_sha256',sha(a.environment))):
        if pre[key]!=value:raise ValueError('prelaunch binding changed: '+key)
    for tag,commit,manifest_sha in (('root_noarg_preflight',NN,cfg['runtime']['source_manifest_sha256']),('analysis_explicit_preflight',own['code_commit'],sha(a.manifest))):
        gate=read(pre[tag])
        if sha(pre[tag])!=pre[tag+'_sha256'] or gate['gate']!='SOURCE_IDENTITY_PASS' or gate['code_commit']!=commit or gate['manifest_sha256']!=manifest_sha:raise ValueError('source preflight differs: '+tag)
        if tag=='root_noarg_preflight' and (Path(gate.get('setup_pointer','').replace('\\','/')).name!='CURRENT.json' or not gate.get('setup_pointer_sha256')):raise ValueError('root noargument CURRENT receipt missing')
    for key in ('runtime','driver','actual_binding_auditor'):
        role=cfg[key]
        if source(role['source_root'],role['source_manifest'],role['code_commit'])!=role:raise ValueError('complete source role drift: '+key)
    if sys.version!=env['python'] or Path(sys.executable).resolve()!=Path(env['executable']).resolve() or platform.platform()!=env['platform'] or importlib.metadata.version('numpy')!=env['numpy']:raise ValueError('environment changed')
    if sha(cfg['idle_receipt'])!=cfg['idle_receipt_sha256']:raise ValueError('idle receipt drift')
    out=disk(a.out)
    if str(out)!=cfg['raw_result_location'] or str(out)!=pre['raw_result_location']:raise ValueError('unfrozen output path')
    check_files(cfg['bound_files']);out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',pre)
    try:
        sys.dont_write_bytecode=True
        sys.meta_path.insert(0,NoNeural())
        sys.path.insert(1,cfg['runtime']['source_root']);sys.path.insert(2,cfg['actual_binding_auditor']['source_root']);sys.path.append(cfg['driver']['source_root'])
        suite=unittest.defaultTestLoader.loadTestsFromName('test_external_rules');stream=io.StringIO()
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        (out/'CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
        if result.testsRun!=cfg['expected_controls'] or result.skipped or not result.wasSuccessful():raise ValueError('focused controls failed; raw replay not started')
        from analyze import analyze
        summary=analyze(cfg,out,lambda:idle(cfg['idle_receipt']))
        summary['focused_CPU_controls']=result.testsRun
        summary['neural_imports']=[n for n in sys.modules if n.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa')]
        if summary['neural_imports']:raise ValueError('neural import escaped guard')
        if sum(p.stat().st_size for p in out.iterdir() if p.is_file())>cfg['max_bounded_output_bytes']:raise ValueError('bounded output cap exceeded')
        check_files(cfg['bound_files']);source(Path(__file__).resolve().parent,a.manifest,own['code_commit']);idle(cfg['idle_receipt'])
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],code_commit=own['code_commit'],new_model_calls=0,positive_effect_is_gate=False))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_EXTERNAL_RULE_SHADOW_PRESERVED',failure=traceback.format_exc(),new_model_calls=0));raise
if __name__=='__main__':main()
