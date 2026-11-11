"""Exact frozen argv/Owner/worker route contract; no model imports/execution."""
import ast, pathlib,sys

EXPECTED_ARMS={'conservative','dependency_versioned','ready_only','fullcall','uir','safe_versioned'}
LEGACY={'stage_service.py','run_service_campaign.py'}
class RouteError(RuntimeError):pass
def need(ok,message):
    if not ok:raise RouteError(message)
def tree(path):return ast.parse(pathlib.Path(path).read_text(encoding='utf8'),filename=str(path))
def function(module,name):
    found=[n for n in ast.walk(module) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name]
    need(len(found)==1,'missing/ambiguous function '+name);return found[0]
def name(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return name(node.value)+'.'+node.attr
    return ''
def call_named(fn,target):return [n for n in ast.walk(fn) if isinstance(n,ast.Call) and name(n.func)==target]
def strings(node):return [n.value for n in ast.walk(node) if isinstance(n,ast.Constant) and isinstance(n.value,str)]

def check_route(driver_root,runtime_root,cells,configs):
    driver_root=pathlib.Path(driver_root);runtime_root=pathlib.Path(runtime_root)
    fn=function(tree(driver_root/'run_confirmation.py'),'run')
    commands=[n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in n.targets)]
    need(len(commands)==1,'driver argv builder changed')
    popens=call_named(fn,'subprocess.Popen');need(len(popens)==1 and isinstance(popens[0].args[0],ast.Name) and popens[0].args[0].id=='command','Popen no longer executes exact command builder')
    need(not any(v in LEGACY for v in strings(fn)),'legacy stage/campaign entry reached from driver')
    compiled=compile(ast.Expression(commands[0].value),str(driver_root/'run_confirmation.py'),'eval')
    actual=[]
    for cell,cfg in zip(cells,configs,strict=True):
        need(cell['strategy']==cfg['arm'] and cfg['arm'] in EXPECTED_ARMS,'wrong or unsupported actual arm')
        argv=eval(compiled,{'sys':sys,'pathlib':pathlib},{'base':{'source_root':str(runtime_root),'source_manifest':'MANIFEST'},'cell':cell})
        need(argv[2]==str(runtime_root/'resilience_trial.py') and argv[3:]==['--config',cell['config'],'--manifest','MANIFEST','--out',cell['out']],'actual argv enters wrong module/config')
        actual.append(dict(cell_id=cell['cell_id'],arm=cfg['arm'],entry=argv[2],config=argv[4],out=argv[-1]))
    trial=tree(runtime_root/'resilience_trial.py');run=function(trial,'run_trial')
    need(any(isinstance(n,ast.ImportFrom) and n.module=='resilience_owner' and any(a.name=='owner_main' for a in n.names) for n in trial.body),'Supervisor Owner binding changed')
    need(any(any(k.arg=='target' and name(k.value)=='owner_main' for k in c.keywords) for c in ast.walk(run) if isinstance(c,ast.Call) and name(c.func)=='ctx.Process'),'Supervisor no longer spawns Owner')
    owner=function(tree(runtime_root/'resilience_owner.py'),'owner_main')
    allowed=[]
    for n in ast.walk(owner):
        if isinstance(n,ast.Compare) and isinstance(n.left,ast.Subscript) and isinstance(n.left.slice,ast.Constant) and n.left.slice.value=='arm' and any(isinstance(op,ast.NotIn) for op in n.ops):
            allowed.extend(ast.literal_eval(n.comparators[0]))
    need(set(allowed)==EXPECTED_ARMS,'actual Owner arm allow-list differs')
    sends=call_named(owner,'workers.send') # subscripts make full callee text unsuitable; inspect call payload instead.
    payloads=[n for n in ast.walk(owner) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' and any(k.arg=='kind' and isinstance(k.value,ast.Constant) and k.value.value=='full' for k in n.keywords)]
    need(bool(payloads),'Owner does not send original full command')
    transport=tree(runtime_root/'resilience_transport.py');start=function(transport,'start_worker');entry=function(transport,'worker_entry')
    need(any(any(k.arg=='target' and name(k.value)=='worker_entry' for k in c.keywords) for c in ast.walk(start) if isinstance(c,ast.Call) and name(c.func)=='ctx.Process'),'physical process target changed')
    need(any(isinstance(n,ast.ImportFrom) and n.module=='stage_worker' and any(a.name=='worker_main' for a in n.names) for n in ast.walk(entry)),'worker_entry no longer imports stage_worker')
    calls=call_named(entry,'worker_main');need(len(calls)==1 and isinstance(calls[0].args[2],ast.Constant) and calls[0].args[2].value=='authority','physical worker role differs')
    worker=function(tree(runtime_root/'stage_worker.py'),'worker_main')
    need(not any(isinstance(n,ast.Subscript) and isinstance(n.slice,ast.Constant) and n.slice.value=='arm' for n in ast.walk(worker)),'worker unexpectedly branches on strategy')
    need(bool(call_named(worker,'model.full_step')),'actual full worker does not call full_step')
    bridge=function(tree(runtime_root/'candidate_bridge.py'),'full_step')
    need(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='step' for n in ast.walk(bridge)),'full_step original step binding missing')
    native=function(tree(runtime_root/'native_bridge.py'),'step');need(bool(call_named(native,'self.engine.infer')),'native step no longer calls original infer')
    return dict(status='PASS_FROZEN_ACTUAL_ENTRY_ROUTE_NO_NEURAL_EXECUTION',cells=len(actual),arms=sorted({c['arm'] for c in actual}),
        route=['run_confirmation.run Popen','resilience_trial.run_trial','resilience_owner.owner_main','resilience_transport.start_worker→worker_entry','stage_worker.worker_main(mode=authority,kind=full)','CandidateBridge.full_step','NativeBridge.step','original engine.infer'],
        legacy_three_arm_entries_executed=False,actual_argv=actual,
        scope='AST and actual frozen argv expression/config contract; not model execution, CUDA attestation, or service performance')
