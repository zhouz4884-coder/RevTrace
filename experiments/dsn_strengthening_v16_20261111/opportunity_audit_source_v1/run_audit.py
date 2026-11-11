"""Frozen opportunity CPU entry. Never invokes a model or modifies actual raw."""
from pathlib import Path
import argparse,importlib.abc,importlib.metadata,io,json,platform,sys,traceback,unittest
from contracts import NN,PLAN,source,read,put,sha,disk,idle,check_files

class NoNeural(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa'):
            raise ImportError('opportunity audit forbids neural import')

def main():
    p=argparse.ArgumentParser()
    for key in ('config','manifest','environment','prelaunch','out'):p.add_argument('--'+key,required=True)
    a=p.parse_args();cfg=read(a.config);pre=read(a.prelaunch);env=read(a.environment)
    idle(cfg['idle_receipt']);own=source(Path(__file__).resolve().parent,a.manifest,cfg['actual_audit_source']['code_commit'])
    if pre['code_commit']!=own['code_commit'] or pre['source_manifest_sha256']!=sha(a.manifest) or pre['frozen_config_sha256']!=sha(a.config) or pre['environment_sha256']!=sha(a.environment):raise ValueError('prelaunch identity/hash mismatch')
    if pre['experiment_id']!=cfg['experiment_id'] or cfg['pilot_plan_sha256']!=PLAN or sha(cfg['pilot_plan'])!=PLAN:raise ValueError('experiment/plan changed')
    rootgate=Path(pre['root_noarg_preflight']);g=read(rootgate)
    if sha(rootgate)!=pre['root_noarg_preflight_sha256'] or g['gate']!='SOURCE_IDENTITY_PASS' or g['code_commit']!=NN or g['manifest_sha256']!=cfg['runtime']['source_manifest_sha256']:raise ValueError('Root default NN gate differs')
    if Path(g.get('setup_pointer','').replace('\\','/')).name!='CURRENT.json' or 'setup_pointer_sha256' not in g:raise ValueError('Root CURRENT/no-argument receipt required')
    explicit=Path(pre['audit_explicit_preflight']);g=read(explicit)
    if sha(explicit)!=pre['audit_explicit_preflight_sha256'] or g['gate']!='SOURCE_IDENTITY_PASS' or g['code_commit']!=own['code_commit'] or g['manifest_sha256']!=sha(a.manifest):raise ValueError('explicit audit source gate differs')
    runtime=source(cfg['runtime']['source_root'],cfg['runtime']['source_manifest'],NN)
    if runtime!=cfg['runtime']:raise ValueError('actual NN dependency changed')
    if source(cfg['driver']['source_root'],cfg['driver']['source_manifest'])!=cfg['driver']:raise ValueError('actual driver dependency changed')
    if env['python']!=sys.version or Path(env['executable']).resolve()!=Path(sys.executable).resolve() or env['platform']!=platform.platform():raise ValueError('CPU environment changed')
    if importlib.metadata.version('numpy')!=env['numpy']:raise ValueError('CPU numpy package changed')
    if sha(cfg['idle_receipt'])!=cfg['idle_receipt_sha256']:raise ValueError('idle receipt changed')
    out=disk(a.out)
    if str(out)!=pre['raw_result_location'] or str(out)!=cfg['raw_result_location']:raise ValueError('unfrozen actual result path')
    before={str(Path(x).resolve()):sha(x) for x in (a.config,a.manifest,a.environment,a.prelaunch,rootgate,explicit)}
    check_files(cfg['bound_files']);out.mkdir(parents=True,exist_ok=False)
    put(out/'CONFIG.json',cfg);put(out/'ENVIRONMENT.json',env);put(out/'RUN_RECORD.json',dict(pre,execution_roles=dict(audit=own,original_NN=runtime,driver=cfg['driver'])))
    try:
        sys.path.insert(0,cfg['runtime']['source_root']);sys.path.append(cfg['driver']['source_root']);sys.meta_path.insert(0,NoNeural())
        suite=unittest.defaultTestLoader.loadTestsFromName('test_opportunities');stream=io.StringIO()
        controls=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        (out/'CONTROLS.log').write_text(stream.getvalue(),encoding='utf8')
        if controls.testsRun!=cfg['expected_controls'] or controls.skipped or not controls.wasSuccessful():raise ValueError('complete focused CPU controls did not pass')
        from audit_all import analyze
        # Every cell starts only within the same explicitly authorized idle window.
        cfg['idle_guard_callable']=lambda:idle(cfg['idle_receipt'])
        result=analyze(cfg,out);cfg.pop('idle_guard_callable')
        result['CPU_controls']=controls.testsRun
        result['blocked_neural_packages_imported']=[name for name in sys.modules if name.split('.')[0] in ('torch','transformers','peft','whisper','simul_whisper','librosa')]
        if result['blocked_neural_packages_imported']:raise ValueError('neural package unexpectedly imported')
        check_files(cfg['bound_files'])
        for path,expected in before.items():
            if sha(path)!=expected:raise ValueError('frozen record changed after analysis')
        source(Path(__file__).resolve().parent,a.manifest,own['code_commit']);source(runtime['source_root'],runtime['source_manifest'],NN);idle(cfg['idle_receipt'])
        put(out/'SUMMARY.json',result);put(out/'GATE.json',dict(status=result['status'],code_commit=own['code_commit'],new_model_calls=0,
            opportunity_positive_is_technical_gate=False,ready_positive_is_gate=False))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_OPPORTUNITY_AUDIT_PRESERVED',failure=traceback.format_exc(),new_model_calls=0));raise
if __name__=='__main__':main()
