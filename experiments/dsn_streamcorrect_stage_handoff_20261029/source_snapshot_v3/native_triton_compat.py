"""Official-Whisper-equivalent host JIT source setter repair, no kernel rewrite."""
import ast,copy,hashlib,inspect,pathlib,types
PINNED_AUTHOR_TRITON_SHA='164c8317baac5a415615206e489e12bc7bdeb6c43ba4fca1bb20c626f8cdc957'
WIDTH7_GENERATED_SHA='9412b2ad3b2b4546d79f348423341178238301f181d7098c2429ea819fabf43a'

def repaired_generator(module):
    path=pathlib.Path(module.__file__);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINNED_AUTHOR_TRITON_SHA:raise ValueError('changed original native Triton source')
    tree=ast.parse(raw.decode(),filename=str(path));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='median_kernel')
    class Setter(ast.NodeTransformer):
        count=0
        def visit_Assign(self,node):
            if len(node.targets)==1 and isinstance(node.targets[0],ast.Attribute) and isinstance(node.targets[0].value,ast.Name) and node.targets[0].value.id=='kernel' and node.targets[0].attr=='src':
                self.count+=1
                return ast.copy_location(ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Name(id='kernel',ctx=ast.Load()),attr='_unsafe_update_src',ctx=ast.Load()),args=[node.value],keywords=[])),node)
            return self.generic_visit(node)
    change=Setter();new=change.visit(copy.deepcopy(fn));assert change.count==3
    scope=dict(module.__dict__)
    # Original filename/line positions retain inspect.getsource(kernel.fn), so
    # Triton receives the byte-identical original nested kernel source body.
    exec(compile(ast.fix_missing_locations(ast.Module(body=[new],type_ignores=[])),str(path),'exec'),scope)
    return scope['median_kernel']

def source_equivalence(module,patched,widths=(1,3,5,7,9,31)):
    original=module.median_kernel.__wrapped__
    class LegacyHolder:
        def __init__(self,fn):self.src=module.triton.JITFunction(fn).src
    proxy=types.SimpleNamespace(jit=module.triton.jit,JITFunction=LegacyHolder)
    scope=dict(original.__globals__);scope['triton']=proxy
    legacy=types.FunctionType(original.__code__,scope)
    rows=[]
    for width in widths:
        a=legacy(width).src;b=patched(width).src;assert a==b
        assert patched(width) is patched(width)
        rows.append(dict(width=width,source_sha256=hashlib.sha256(b.encode()).hexdigest(),byte_equal=True,lru_cache_identity=True))
    assert next(r for r in rows if r['width']==7)['source_sha256']==WIDTH7_GENERATED_SHA
    return rows

def install():
    from simul_whisper.whisper import triton_ops as module
    original=module.median_kernel;patched=repaired_generator(module);proof=source_equivalence(module,patched)
    module.median_kernel=patched
    return dict(original=original,patched=patched,module=module,source_proof=proof)
