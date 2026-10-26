"""Finite product exploration of the SAME pure kernel used by the service.
This is not a proof of arbitrary Python/GPU/filesystem executions.
"""
from pathlib import Path
from collections import deque,Counter
from dataclasses import asdict
import sys,json,hashlib
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.composed_kernel import State,step,Denied

def canonical(x):
    if isinstance(x,dict):return sorted([(repr(k),canonical(v)) for k,v in x.items()])
    if isinstance(x,(tuple,list)):return [canonical(v) for v in x]
    if isinstance(x,set):return sorted(x)
    return x
def digest(k):return hashlib.sha256(json.dumps(canonical(asdict(k)),sort_keys=True).encode()).hexdigest()
def tsh(s):return hashlib.sha256(s.encode()).hexdigest()
G=dict(v=0,F=0,P='p0',Z='',textsha=tsh(''),txn='')

def initial(epoch=1):
    k,_=step(State('frozen',epoch,1.),'recover-fact',dict(sid=0,fact=G))
    return k

def events(k):
    # One interval, one authority and one longer private target; two possible
    # selected projections capture compatible and incompatible late results.
    if not k.restored_input:
        yield 'input-synced',dict(items={0:dict(accepted=2,offered=2,reserved=2,prefix='a'*64)},recovery=True)
    for w in ['a','p']:
        if w not in k.ready:yield 'worker-ready',dict(worker=w)
    c=k.C[0]
    for w,role,end in [('a','authority',1),('p','proposal',2)]:
        jid=w+str(k.epoch)
        if jid not in k.J and c['v']==0:
            yield 'dispatch',dict(worker=w,jobs=[dict(id=jid,sid=0,role=role,parent=0,start=0,end=end,
                rootF=0,inputP='p0',identity=jid)])
        if w in k.leases:yield 'batch-drained',dict(worker=w)
    for jid,j in k.J.items():
        if j['result'] is None:
            for P in ['p0','p1']:
                yield 'row-complete',dict(id=jid,worker=j['worker'],identity=j['identity'],P=P,Z='z',textsha=tsh(P))
        elif j['role']=='authority' and c['v']==0 and 't' not in k.prepared and 1 not in k.D[0]:
            r=j['result'];f=dict(v=1,F=1,P=r['P'],Z=r['Z'],textsha=r['textsha'],txn='t')
            yield 'admission-request',dict(sid=0,job=jid,operation='t',fact=f)
    if 't' in k.prepared:yield 'canonical-synced',dict(operation='t')
    if 1 in k.D[0] and c['v']==0:yield 'install',dict(sid=0,fact=k.D[0][1])
    if c['v'] and 'canon' not in k.publications:
        yield 'publish',dict(sid=0,key='canon',publication=dict(canonical=True,fact=c))
    for jid,j in k.J.items():
        if j['role']=='proposal' and j['result'] and jid not in k.publications:
            yield 'publish',dict(sid=0,key=jid,publication=dict(canonical=False,job=jid,end=j['end'],textsha=j['result']['textsha']))
    if 'apply' in k.prepared:
        yield 'view-applied',dict(operation='apply')
    else:
        old=k.V[0]
        if old['revision']<2:
            for key,p in k.publications.items():
                if p['canonical']:
                    f=p['fact']
                    if f['v']<=old['v']:continue
                    v=dict(v=f['v'],F=f['F'],P=f['P'],visible=f['F'],text=f['P'],revision=old['revision']+1,private=None)
                else:
                    j=k.J[p['job']]
                    if old.get('private')==j['id']:continue
                    v=dict(v=old['v'],F=old['F'],P=old.get('P') or 'p0',visible=j['end'],text=j['result']['P'],
                        revision=old['revision']+1,private=j['id'])
                yield 'apply-request',dict(sid=0,key=key,view=v,operation='apply')

def independent(k):
    # Independent observations, not an alias to production check().
    for sid,c in k.C.items():
        assert c['v']==0 or k.D[sid][c['v']]==c
        if k.restored_input:assert k.I[sid]['accepted']>=c['F']
        assert 0<=k.V[sid]['F']<=c['F'] and k.V[sid]['v']<=c['v']
    for j in k.J.values():assert j['end']<=k.I[j['sid']]['accepted']
    for w,ids in k.leases.items():assert len(ids)==len(set(ids))

def explore(depth_first=False):
    root=initial();queue=deque([root]);seen={digest(root)};edges=denied=0;terminal=0;hist=Counter()
    while queue:
        k=queue.pop() if depth_first else queue.popleft();independent(k)
        if k.C[0]['v']==k.V[0]['v']==1 and not k.leases:terminal+=1
        for kind,p in events(k):
            try:n,fx=step(k,kind,p)
            except (Denied,KeyError):denied+=1;continue
            edges+=1;hist[kind]+=1;h=digest(n)
            if h not in seen:seen.add(h);queue.append(n)
        # A process-group failure destroys old queues/leases. Only persisted
        # facts and accepted obligations survive. This is NOT warm adoption.
        if k.epoch==1:
            n=initial(2);latest=max(k.D[0],default=0)
            if latest:
                n=State('frozen',2,2.)
                n,_=step(n,'recover-fact',dict(sid=0,fact=k.D[0][latest],history=k.D[0]))
            if k.restored_input:n,_=step(n,'input-synced',dict(items=k.I,recovery=True))
            edges+=1;hist['process-group-kill/replay']+=1;h=digest(n)
            if h not in seen:seen.add(h);queue.append(n)
        assert len(seen)<250000,'finite bound unexpectedly expanded; report rather than truncate silently'
    assert terminal>0,'reject-all is not success'
    return dict(status='EXHAUSTED_FINITE_COMPOSED_PRODUCT',states=len(seen),edges=edges,illegal_events_rejected=denied,
        exact_state_set_sha256=hashlib.sha256('\n'.join(sorted(seen)).encode()).hexdigest(),
        legal_progress_states=terminal,transition_counts=hist,bounds='one session; one canonical interval; one ahead private interval; two projections; two workers; one process-group restart; at most two view revisions',
        assumptions='trusted complete selection and render receipts; intact durable storage; killed old workers; no full implementation refinement claim')

if __name__=='__main__':
    result=explore();other=explore(True)
    assert result==other,'independent traversal disagrees'
    result['BFS_DFS_crosscheck']='identical state/edge/transition counts; same transition specification'
    result['executed_kernel_sha256']=hashlib.sha256((W/'runtime/src/revtrace/composed_kernel.py').read_bytes()).hexdigest()
    p=W/(sys.argv[1] if len(sys.argv)>1 else 'FORMAL_PRODUCT_v1.json');assert not p.exists()
    p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
