"""Frozen pure-stdlib analysis helpers; no models or GPU APIs."""
from __future__ import annotations
import csv,hashlib,json,pathlib,subprocess,sys
OBSERVER='3cf7cd10a3ba76958b4173aa20eb6116ac779a39'
DRIVER='b16481983674dec34e798342caf519e566a2b1cd'
NN4F='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
SOURCES=('BAC009S0908W0369','BAC009S0916W0463')
class AnalysisError(RuntimeError):pass
def need(ok,text):
    if not ok:raise AnalysisError(text)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def put(path,obj):
    with pathlib.Path(path).open('x',encoding='utf8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def rows(path):
    with pathlib.Path(path).open(encoding='utf8') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def csvout(path,items):
    items=list(items)
    with pathlib.Path(path).open('x',encoding='utf8',newline='') as f:
        if items:
            w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
def disk(path):
    p=pathlib.Path(path);need(p.is_absolute() and p.resolve().is_relative_to(B.resolve()),'new output must stay on designated8TB disk');return p
def verify_source(root,manifest,expected=None):
    root=pathlib.Path(root).resolve(strict=True);manifest=pathlib.Path(manifest).resolve(strict=True);m=read(manifest)
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
    commit=m.get('source_commit',m.get('code_commit'))
    need(isinstance(commit,str) and len(commit)==40 and (expected is None or commit==expected),'wrong full source commit')
    need(pathlib.Path(git('rev-parse','--show-toplevel')).resolve()==root and git('rev-parse','HEAD')==commit and git('cat-file','-t',commit)=='commit','source identity unresolved')
    need(git('config','--get','core.autocrlf')=='false' and not git('status','--porcelain','--untracked-files=all'),'source dirty or line conversion enabled')
    need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'complete source manifest differs')
    for r in m['files']:
        p=root/r['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root) and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'source byte mismatch')
    return dict(source_commit=commit,manifest_sha256=sha(manifest),complete_files=len(m['files']),source_root=str(root))
def boot(manifest,prelaunch,config):
    identity=verify_source(pathlib.Path(__file__).parent,manifest);pre=read(prelaunch)
    need(pre['config_sha256']==sha(config),'prelaunch config hash differs')
    need(sha(pre['root_noarg_preflight'])==pre['root_noarg_preflight_sha256'],'root gate file changed')
    gate=read(pre['root_noarg_preflight'])
    need(gate['gate']=='SOURCE_IDENTITY_PASS' and gate['code_commit']==identity['source_commit'] and gate['manifest_sha256']==identity['manifest_sha256'],'Root CURRENT did not bind analysis source')
    need(pathlib.Path(gate['setup_pointer'].replace('\\','/')).name=='CURRENT.json' and 'setup_pointer_sha256' in gate,'not a no-argument Root receipt')
    return identity,pre
def inventory(paths):
    return {str(pathlib.Path(p)):dict(bytes=pathlib.Path(p).stat().st_size,sha256=sha(p)) for p in sorted(set(map(str,paths)))}
def verify_inventory(expected):
    need(inventory(expected)==expected,'frozen analysis input bytes changed')
def quantile(values,q):
    v=sorted(values)
    if not v:return None
    p=(len(v)-1)*q;i=int(p);j=min(i+1,len(v)-1);return v[i]+(v[j]-v[i])*(p-i)
def run_record(out,experiment,identity,config,env):
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=experiment,code_commit=identity['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))

