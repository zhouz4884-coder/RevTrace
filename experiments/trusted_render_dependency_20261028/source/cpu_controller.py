"""Frozen CPU-only native/light conformance orchestration; no model invocation."""
from pathlib import Path
import argparse,hashlib,importlib.metadata,importlib.util,json,os,platform,re,subprocess,sys,time,traceback


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def environment_record():
    return dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']})


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,text=True).strip()


def validate(root,manifest):
    m=json.loads(Path(manifest).read_text());assert re.fullmatch('[0-9a-f]{40}',m['code_commit'])
    assert git(root,'rev-parse','HEAD')==m['code_commit'] and not git(root,'status','--porcelain')
    assert {r['path'] for r in m['files']}==set(git(root,'ls-files').splitlines())
    for r in m['files']:
        p=Path(root)/r['path'];assert not p.is_symlink() and p.resolve().is_relative_to(Path(root).resolve())
        assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
    return m


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-manifest',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--runtime-manifest',type=Path,required=True);p.add_argument('--cpu-gate',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--native-descriptor',type=Path,required=True);p.add_argument('--native-descriptor-sha256',required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--recovery',type=Path,required=True);p.add_argument('--operators',type=Path,required=True);a=p.parse_args()
    own=validate(Path(__file__).parent,a.source_manifest);rt=validate(a.runtime,a.runtime_manifest)
    cpu=json.loads(a.cpu_gate.read_text());assert cpu['source_commit']==rt['code_commit'] and cpu['gate']=='PASS'
    base=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');assert a.out.resolve().is_relative_to(base/'results/revtrace/trusted_render_dependency_20261028')
    assert a.bundle.resolve().is_relative_to(base/'projects/revtrace_freeze_boundary_20261027/packages')
    assert not a.out.exists() and not a.bundle.exists();a.out.mkdir(parents=True)
    def put(n,x):
        with (a.out/n).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
    env=environment_record()
    put('ENVIRONMENT.json',env)
    inputs=[a.recovery/'SUMMARY.json',a.operators/'SUMMARY.json']
    for path in a.recovery.rglob('*'):
        if path.is_file() and (path.name.endswith('.submissions') or path.name.endswith('receipts.jsonl') or path.name=='canonical.wal'):inputs.append(path)
    inputs+=sorted(a.operators.glob('[01][01]-*-r[01].json'))
    put('INPUTS.json',[dict(path=str(v),sha256=sha(v)) for v in sorted(set(inputs))])
    put('FREEZE.json',dict(experiment_id='REVTRACE-TRUSTED-RENDER-DEPENDENCY-CPU-V1-20261028',orchestration_commit=own['code_commit'],orchestration_manifest_sha256=sha(a.source_manifest),runtime_commit=rt['code_commit'],runtime_manifest_sha256=sha(a.runtime_manifest),environment_sha256=sha(a.out/'ENVIRONMENT.json'),input_manifest_sha256=sha(a.out/'INPUTS.json'),config={k:str(v) for k,v in vars(a).items()},expected=dict(observed_rows=184,durable_bindings=56,paid_rows=28,random_controls=4096,negative_loader_controls=7),GPU_inference_calls=0,raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'RESULT.json'),gate_decision_location=str(a.out/'GATE.json')))
    completed=[];envvars=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TOKENIZERS_PARALLELISM='false')
    def run(name,cmd):
        put(name+'_COMMAND.json',dict(argv=cmd,source_commit=rt['code_commit']))
        with (a.out/(name+'.log')).open('x') as f:r=subprocess.run(cmd,cwd=a.runtime,env=envvars,stdout=f,stderr=subprocess.STDOUT,timeout=600)
        if r.returncode:raise RuntimeError(name+' failed rc='+str(r.returncode))
        completed.append(name);put('PROGRESS_'+str(len(completed))+'.json',dict(completed=completed,expected=6));print(json.dumps(dict(stage=name,status='complete')),flush=True)
    try:
        scripts=a.runtime/'runtime/scripts';M=a.model;native=a.native_descriptor
        run('prepare',[sys.executable,'-B',str(scripts/'prepare_light_render.py'),'--model',str(M),'--native-descriptor',str(native),'--native-descriptor-sha256',a.native_descriptor_sha256,'--bundle',str(a.bundle),'--result',str(a.out/'preparation'),'--source-root',str(a.runtime),'--source-manifest',str(a.runtime_manifest)])
        descriptor_sha=sha(a.bundle/'descriptor.json');bank=a.out/'cases.json'
        run('bank',[sys.executable,'-B',str(scripts/'check_light_render.py'),'--out',str(bank),'--build-bank-recovery',str(a.recovery),'--build-bank-operators',str(a.operators)])
        pkg=Path(importlib.util.find_spec('qwen_asr').origin).resolve().parent
        for mode in ['native','light','negative']:
            run(mode,[sys.executable,'-B',str(scripts/'check_light_render.py'),'--worker',mode,'--out',str(a.out/mode),'--model',str(M),'--bundle',str(a.bundle),'--descriptor-sha256',descriptor_sha,'--package-root',str(pkg),'--bank',str(bank),'--bank-sha256',sha(bank),'--source-root',str(a.runtime),'--source-manifest',str(a.runtime_manifest)])
        run('compare',[sys.executable,'-B',str(scripts/'check_light_render.py'),'--out',str(a.out/'comparison'),'--source-root',str(a.runtime),'--source-manifest',str(a.runtime_manifest),'--compare-native',str(a.out/'native/RESULT.json'),'--compare-light',str(a.out/'light/RESULT.json'),'--compare-negative',str(a.out/'negative/RESULT.json')])
        result=json.loads((a.out/'comparison/RESULT.json').read_text());put('RESULT.json',result);put('GATE.json',result)
    except BaseException:
        put('STOP.json',dict(completed=completed,error=traceback.format_exc(),GPU_inference_calls=0));raise


if __name__=='__main__':main()
