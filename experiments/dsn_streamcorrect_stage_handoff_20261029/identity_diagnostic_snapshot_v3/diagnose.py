"""CPU-only introspection of original loaded methods; never constructs a model."""
from __future__ import annotations
import ast, hashlib, inspect, json, os, pathlib, platform, sys, types, dis

FIELDS = ('co_code','co_names','co_varnames','co_freevars','co_cellvars',
          'co_argcount','co_posonlyargcount','co_kwonlyargcount','co_flags','co_exceptiontable')
def sha(data): return hashlib.sha256(data).hexdigest()
def describe(x):
    if isinstance(x, bytes): return dict(type='bytes', bytes=len(x), sha256=sha(x))
    if isinstance(x, types.CodeType): return dict(type='code',name=x.co_name,flags=x.co_flags)
    return dict(type=type(x).__name__,value=repr(x)[:1500])
def diffs(a,b,path='code'):
    out=[]
    for name in FIELDS:
        if getattr(a,name,None)!=getattr(b,name,None):out.append(dict(path=path+'.'+name,actual=describe(getattr(a,name,None)),expected=describe(getattr(b,name,None))))
    if len(a.co_consts)!=len(b.co_consts):out.append(dict(path=path+'.co_consts.length',actual=len(a.co_consts),expected=len(b.co_consts)))
    for i,(x,y) in enumerate(zip(a.co_consts,b.co_consts)):
        p=path+'.co_consts['+str(i)+']'
        if isinstance(x,types.CodeType) and isinstance(y,types.CodeType):out+=diffs(x,y,p)
        elif type(x) is not type(y) or x!=y:out.append(dict(path=p,actual=describe(x),expected=describe(y)))
    return out
def find(code,name):return next(c for c in code.co_consts if isinstance(c,types.CodeType) and c.co_name==name)
def run(author_root,adapter_root):
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
    sys.path[:0]=[str(adapter_root),str(author_root)]
    from native_tail import AUTHOR_SHA256,AUTHOR_CLASS,compile_original_tail,_same_code
    author_file=pathlib.Path(author_root)/'simul_whisper/simul_whisper.py';raw=author_file.read_bytes();assert sha(raw)==AUTHOR_SHA256
    import simul_whisper.simul_whisper as module
    import torch
    assert not torch.cuda.is_initialized()
    cls=getattr(module,AUTHOR_CLASS);artifact=compile_original_tail(author_file)
    full=compile(raw,str(author_file.resolve()),'exec',dont_inherit=True,optimize=0);full_class=find(full,AUTHOR_CLASS)
    methods={}
    for name,expected in artifact._method_codes:
        bound=inspect.getattr_static(cls,name);actual=inspect.unwrap(bound).__code__;oracle=find(full_class,name)
        instruction_pairs=[(x,y) for x,y in zip(dis.get_instructions(actual),dis.get_instructions(expected)) if (x.opname,x.arg,x.argrepr)!=(y.opname,y.arg,y.argrepr)]
        methods[name]=dict(instruction_differences=[dict(actual=dict(offset=x.offset,op=x.opname,arg=x.arg,argrepr=x.argrepr),subset=dict(offset=y.offset,op=y.opname,arg=y.arg,argrepr=y.argrepr)) for x,y in instruction_pairs],loaded_file=actual.co_filename,loaded_flags=actual.co_flags,reference_flags=expected.co_flags,
            loaded_vs_subset=diffs(actual,expected),loaded_vs_whole_module=diffs(actual,oracle),subset_vs_whole_module=diffs(expected,oracle),
            existing_guard_loaded_vs_subset=_same_code(actual,expected),existing_guard_loaded_vs_whole=_same_code(actual,oracle))
    return dict(status='INSPECTED_CPU_ORIGINAL_DEFINITIONS_ONLY',python=sys.version,executable=sys.executable,platform=platform.platform(),
        optimize=sys.flags.optimize,author_file=str(author_file),author_sha256=sha(raw),author_pyc=getattr(module,'__cached__',None),
        model_instances_constructed=0,gpu_launched=False,cuda_initialized=torch.cuda.is_initialized(),methods=methods)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--author-root',required=True);p.add_argument('--adapter-root',required=True);a=p.parse_args()
    print(json.dumps(run(a.author_root,a.adapter_root),ensure_ascii=False,indent=2))
