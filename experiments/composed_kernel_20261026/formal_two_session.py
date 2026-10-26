"""Additional finite cut: two sessions sharing one physical two-row lease.

Partial per-row sync/install/application and one process-group restart are
interleaved. Private ancestry is covered by the separate one-session product.
"""
from pathlib import Path
from collections import deque
from dataclasses import asdict
import sys,hashlib,json
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.composed_kernel import State,step,Denied
from formal_explore import canonical
def H(k):return hashlib.sha256(json.dumps(canonical(asdict(k)),sort_keys=True).encode()).hexdigest()
def ts(x):return hashlib.sha256(x.encode()).hexdigest()
G=dict(v=0,F=0,P='p0',Z='',textsha=ts(''),txn='')
def fresh(old=None):
    epoch=1 if old is None else 2;k=State('fixed',epoch,float(epoch))
    for sid in [0,1]:
        history={} if old is None else old.D[sid];v=max(history,default=0)
        f=history[v] if v else G
        k,_=step(k,'recover-fact',dict(sid=sid,fact=f,history=history))
    items={sid:dict(accepted=1,offered=1,reserved=1,prefix='a'*64,origin=100.) for sid in [0,1]}
    k,_=step(k,'input-synced',dict(items=items,recovery=True))
    return k
def events(k):
    if 'a' not in k.ready:yield 'worker-ready',dict(worker='a')
    todo=[sid for sid in [0,1] if k.C[sid]['v']==0 and f'a{sid}e{k.epoch}' not in k.J]
    if todo:
        jobs=[dict(id=f'a{sid}e{k.epoch}',sid=sid,role='authority',parent=0,start=0,end=1,rootF=0,
            inputP='p0',identity=f'a{sid}e{k.epoch}') for sid in todo]
        yield 'dispatch',dict(worker='a',jobs=jobs)
    if 'a' in k.leases:yield 'batch-drained',dict(worker='a')
    for sid in [0,1]:
        jid=f'a{sid}e{k.epoch}';op=f'{sid}:0:1';ap='apply:'+str(sid);key='pub:'+str(sid)
        j=k.J.get(jid);c=k.C[sid]
        if j and j['result'] is None:
            yield 'row-complete',dict(id=jid,worker='a',identity=jid,Z='z',P='p1',textsha=ts('new'))
        if j and j['result'] and c['v']==0 and 1 not in k.D[sid] and op not in k.prepared:
            f=dict(v=1,F=1,P='p1',Z='z',textsha=ts('new'),txn=op)
            yield 'admission-request',dict(sid=sid,job=jid,operation=op,fact=f)
        if op in k.prepared:yield 'canonical-synced',dict(operation=op)
        if c['v']==0 and 1 in k.D[sid]:yield 'install',dict(sid=sid,fact=k.D[sid][1])
        if c['v'] and key not in k.publications:
            yield 'publish',dict(sid=sid,key=key,publication=dict(canonical=True,fact=c))
        if key in k.publications and k.V[sid]['v']==0 and ap not in k.prepared:
            v=dict(v=1,F=1,P='p1',visible=1,text='new',revision=1,private=None)
            yield 'apply-request',dict(sid=sid,key=key,operation=ap,view=v)
        if ap in k.prepared:yield 'view-applied',dict(operation=ap)
def independent(k):
    for sid in [0,1]:
        c=k.C[sid];v=k.V[sid];assert c['F']<=k.I[sid]['accepted']==1
        assert 0<=v['F']<=c['F'] and v['v']<=c['v']
        if c['v']:assert k.D[sid][c['v']]==c and c['txn'].startswith(str(sid)+':')
    for worker,ids in k.leases.items():assert all(k.J[j]['worker']==worker for j in ids)
def explore(dfs=False):
    q=deque([fresh()]);seen={H(q[0])};edges=bad=progress=partial=0
    while q:
        k=q.pop() if dfs else q.popleft();independent(k)
        if all(k.C[s]['v']==k.V[s]['v']==1 for s in [0,1]) and not k.leases:progress+=1
        if k.C[0]['v']!=k.C[1]['v'] and k.leases:partial+=1
        for kind,p in events(k):
            try:n,_=step(k,kind,p)
            except (Denied,KeyError):bad+=1;continue
            edges+=1;h=H(n)
            if h not in seen:seen.add(h);q.append(n)
        if k.epoch==1:
            n=fresh(k);edges+=1;h=H(n)
            if h not in seen:seen.add(h);q.append(n)
        assert len(seen)<250000,'report unexpected expansion, never silently truncate'
    assert progress and partial
    return dict(states=len(seen),edges=edges,illegal_events_rejected=bad,legal_complete_progress_states=progress,
        partial_session_install_while_batch_still_leased_states=partial,
        state_set_sha256=hashlib.sha256('\n'.join(sorted(seen)).encode()).hexdigest())
if __name__=='__main__':
    result=explore();assert result==explore(True)
    result.update(status='EXHAUSTED_TWO_SESSION_PARTIAL_ROW_RECOVERY_CUT',
        bounds='two sessions; one canonical interval each; one two-row authority lease; one restart; private path belongs to separate product',
        source_kernel_sha256=hashlib.sha256((W/'runtime/src/revtrace/composed_kernel.py').read_bytes()).hexdigest(),
        scope='same pure executed kernel plus independent invariant checks/BFS-DFS set match; not full stack refinement')
    out=W/'FORMAL_TWO_SESSION_v6.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
