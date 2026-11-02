"""Pure-stdlib campaign identity, frozen inputs and bounded output helpers."""
from __future__ import annotations
import hashlib, importlib.metadata, json, os, pathlib, subprocess, sys

NN4F='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
OBSERVER='3cf7cd10a3ba76958b4173aa20eb6116ac779a39'
SUPPORT='a13fa0a335529dc188f7e738877a3acd027ce4a7'
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
SOURCES=('BAC009S0908W0369','BAC009S0916W0463')
class GateError(RuntimeError):pass
def need(ok,message):
    if not ok:raise GateError(message)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def put(path,obj,replace=False):
    with pathlib.Path(path).open('w' if replace else 'x',encoding='utf8',newline='\n') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def lines(path):
    with pathlib.Path(path).open(encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]
def disk(path,base=B):
    p=pathlib.Path(path)
    need(p.is_absolute() and p.resolve().is_relative_to(pathlib.Path(base).resolve()),'output escaped designated disk')
    return p
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,stderr=subprocess.PIPE).strip()
def verify_source(root,manifest,commit=None):
    root=pathlib.Path(root).resolve(strict=True);manifest=pathlib.Path(manifest).resolve(strict=True);m=read(manifest)
    actual=m.get('source_commit',m.get('code_commit'))
    need(isinstance(actual,str) and len(actual)==40,'full execution source commit required')
    need(commit is None or actual==commit,'wrong actual execution source commit')
    need(pathlib.Path(git(root,'rev-parse','--show-toplevel')).resolve()==root,'not independent execution checkout')
    need(git(root,'rev-parse','HEAD')==actual and git(root,'cat-file','-t',actual)=='commit','unresolvable execution HEAD')
    need(git(root,'config','--get','core.autocrlf')=='false','byte-exact execution checkout requires autocrlf=false')
    need(not git(root,'status','--porcelain','--untracked-files=all'),'dirty execution source')
    tracked=set(git(root,'ls-files','-z').split('\0'))-{''};rows=m['files']
    need(len(rows)==len({r['path'] for r in rows}) and tracked=={r['path'] for r in rows},'incomplete source manifest')
    for row in rows:
        p=root/row['path'];need(not p.is_symlink() and p.resolve().is_relative_to(root),'source manifest path escape')
        need(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'source bytes changed: '+row['path'])
    return dict(source_commit=actual,source_root=str(root),source_manifest=str(manifest),manifest_sha256=sha(manifest),complete_files=len(rows),clean=True)
def matrix_shape(plan):
    need(tuple(plan['fixed_sources'])==SOURCES,'cost sources changed after freeze')
    need(plan['observer_source_commit']==OBSERVER and plan['actual_nn_source_commit']==NN4F,'cost execution roles changed')
    cpu=plan['cpu_cases'];nn=plan['cells']
    expected_cpu={(s,a,r) for s in SOURCES for a in ('conservative','fullcall') for r in range(3)}
    expected_nn={(s,a,r,on) for s in SOURCES for a in ('conservative','fullcall') for r in range(2) for on in (False,True)}
    need(len(cpu)==12 and {(x['source_id'],x['arm'],x['repeat']) for x in cpu}==expected_cpu,'CPU12 matrix incomplete/duplicated')
    need(len(nn)==16 and {(x['source_id'],x['arm'],x['repeat'],x['observation']) for x in nn}==expected_nn,'NN16 matrix incomplete/duplicated')
    need(len({x['cell_id'] for x in cpu+nn})==28,'cell IDs not globally unique')
    for x in nn:need(type(x['observation']) is bool and x['primary_gpu']==x['repeat'],'off/on/GPU rotation differs')
def input_inventory(raw):
    names=('CONFIG.json','GENESIS.json','facts.wal','publications.jsonl','consumer.jsonl','consumer_rejections.jsonl','owner_e0/dispatch.jsonl','owner_e0/worker_results.jsonl')
    raw=pathlib.Path(raw)
    return {n:dict(bytes=(raw/n).stat().st_size,sha256=sha(raw/n)) for n in names}
def runtime_environment(plan,cpu=False):
    need(plan['runtime_environment']=={'PYTORCH_CUDA_ALLOC_CONF':'expandable_segments:True'},'allocator condition changed')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1')
    env.pop('PYTORCH_ALLOC_CONF',None);env.pop('CUDA_VISIBLE_DEVICES',None);env.update(plan['runtime_environment'])
    if cpu:env['CUDA_VISIBLE_DEVICES']=''
    return env
def check_environment(plan):
    need(sha(plan['environment_record'])==plan['environment_sha256'],'frozen environment record changed')
    env=read(plan['environment_record'])
    need(pathlib.Path(sys.executable).resolve()==pathlib.Path(plan['environment_python']).resolve(),'wrong actual interpreter')
    for name,version in env['packages'].items():need(importlib.metadata.version(name)==version,'package version differs: '+name)
    if 'assets_manifest_path' in env:need(sha(env['assets_manifest_path'])==env['assets_manifest_sha256'],'model asset manifest changed')
    return env

