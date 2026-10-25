"""Policy-independent finite CDE obligation model, separate from neural serving.

Canonical selection is an assumed trusted transition inherited from the base
protocol proof. Atomic input snapshot is justified separately by actual I/O
tests; it is not a model of all filesystem implementations.
"""
from collections import deque
from pathlib import Path
import argparse,hashlib,json
O,A,C,R,J,DA,DR,DJ,ACK,E,M,U,V,PENDING,READY,BAD=range(16)
PROPS=['accepted_input_lost','reservation_recovery_unavailable','certified_only_false_view',
       'old_observation_relabelled_fresh','untrusted_canonical_admission','credit_bound_exceeded','terminal_rejection_forgotten']

def initial(n):
    z=(0,)*n;b=(False,)*n
    return (z,z,z,z,b,z,z,b,z,0,0,z,z,None,True,0)
def key(s):return json.dumps(s,separators=(',',':'))
def setv(values,i,x):v=list(values);v[i]=x;return tuple(v)
def change(s,**kw):
    v=list(s)
    for k,x in kw.items():v[int(k)]=x
    return tuple(v)
def step(s,c):
    if s[BAD]:return # monitor-terminal counterexamples; unsafe continuations are not searched
    n=c['sessions'];limit=c['frontiers'];budget=c['budget'];q=2;omit=c['omit'];mode=s[M]
    def updated(changes,persist=False):
        v=list(s)
        for k,x in changes.items():v[k]=x
        if persist:
            v[DA]=v[A];v[DR]=v[R];v[DJ]=v[J]
        bad=v[BAD]
        if sum(r-cc for r,cc in zip(v[R],v[C]))>budget:bad|=32
        v[BAD]=bad;return tuple(v)
    for i in range(n):
        if s[O][i]<limit:yield f'offer-{i}',updated({O:setv(s[O],i,s[O][i]+1)})
        if mode!=4 and not s[J][i] and s[O][i]>s[R][i]:
            end=s[R][i]+q
            if s[O][i]==limit:end=min(end,limit)
            cost=end-s[R][i]
            if cost>0 and (sum(r-cc for r,cc in zip(s[R],s[C]))+cost<=budget or omit=='credit_limit'):
                yield f'reserve-complete-interval-{i}',updated({R:setv(s[R],i,end)},True)
        if not s[J][i] and s[A][i]<min(s[O][i],s[R][i]):
            end=min(s[O][i],s[R][i])
            # The observed ACK is external history and survives an owner crash.
            yield f'accept-sync-ack-{i}',updated({A:setv(s[A],i,end),ACK:setv(s[ACK],i,end)},omit!='input_sync')
        target=min(s[C][i]+q,limit)
        if mode!=4 and target>s[C][i] and target<=s[A][i] and not s[J][i]:
            yield f'trusted-canonical-admission-{i}',updated({C:setv(s[C],i,target)})
            if omit=='admission_trust':
                yield f'negative-deadline-bypass-{i}',updated({C:setv(s[C],i,target),BAD:s[BAD]|16})
        if s[U][i]<s[C][i]:
            yield f'actual-certified-consume-{i}',updated({U:setv(s[U],i,s[C][i]),V:setv(s[V],i,s[C][i])})
        if mode not in [2,4] and s[A][i]>s[V][i] and not s[J][i]:
            yield f'actual-legal-private-consume-{i}',updated({V:setv(s[V],i,s[A][i])})
        if not s[J][i] and s[A][i]==0 and s[O][i]>0:
            yield f'explicit-reject-unaccepted-{i}',updated({J:setv(s[J],i,True),R:setv(s[R],i,0)},True)
        if s[PENDING] is None and s[V][i]>0:
            yield f'stage-actual-observation-{i}',updated({PENDING:(i,s[V][i],s[E],s[C][i])})
    if s[PENDING] is not None:
        i,F,epoch,context=s[PENDING]
        bad=s[BAD]
        if epoch!=s[E] and omit=='epoch_fence':bad|=8
        yield 'deliver-or-fence-observation',updated({PENDING:None,BAD:bad})
    if s[READY]:
        for new_mode in range(4):
            if new_mode==mode:continue
            vis=s[V]
            if new_mode==2 and omit!='mode_purge':vis=s[U]
            bad=s[BAD]
            if new_mode==2 and any(a!=b for a,b in zip(vis,s[U])):bad|=4
            yield f'apply-view-mode-{new_mode}',updated({M:new_mode,V:vis,BAD:bad})
    else:yield 'actual-new-stream-application',updated({READY:True})
    if s[E]==0:
        aa=s[DA];rr=s[DR];jj=s[DJ]
        if omit=='zero_reservation_restore':rr=s[C]
        if omit=='derive_reservation_positive':
            rr=tuple(min(limit,((a+q-1)//q)*q) for a in aa)
        if omit=='forget_rejection':jj=(False,)*n
        bad=s[BAD]
        if any(a>b for a,b in zip(s[ACK],aa)) or any(cc>a for cc,a in zip(s[C],aa)):bad|=1
        if any(a>r for a,r in zip(aa,rr)):bad|=2
        if any(old and not new for old,new in zip(s[J],jj)):bad|=64
        yield 'crash-restore-input-and-canonical-new-epoch',updated({A:aa,R:rr,J:jj,E:1,M:4,
            U:(0,)*n,V:(0,)*n,READY:False,BAD:bad})

def explore(c):
    root=initial(c['sessions']);seen={root};queue=deque([root]);parent={root:None};action={};witness={};edges=0
    while queue:
        s=queue.popleft()
        for label,t in step(s,c):
            edges+=1
            if t in seen:continue
            seen.add(t);queue.append(t);parent[t]=s;action[t]=label
            if len(seen)>600000:raise RuntimeError('state cutoff; not complete')
            for i,p in enumerate(PROPS):
                if t[BAD]&(1<<i) and p not in witness:
                    path=[];v=t
                    while parent[v] is not None:path.append(dict(action=action[v],state=json.loads(key(v))));v=parent[v]
                    witness[p]=list(reversed(path))
    h=hashlib.sha256()
    for v in sorted(map(key,seen)):h.update((v+'\n').encode())
    return dict(config=c,complete=True,states=len(seen),transitions=edges,reachable_sha256=h.hexdigest(),
        violations=sorted(witness),witnesses=witness)

def configs():
    for sessions,frontiers,budget in [(1,3,2),(2,2,2)]:
        for omit in ['none','input_sync','zero_reservation_restore','derive_reservation_positive','mode_purge','epoch_fence','admission_trust','credit_limit','forget_rejection']:
            yield dict(sessions=sessions,frontiers=frontiers,budget=budget,omit=omit)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    results=[]
    for c in configs():
        r=explore(c);results.append(r);print(c,r['states'],r['violations'],flush=True)
    assert all(not r['violations'] for r in results if r['config']['omit'] in ['none','derive_reservation_positive'])
    a.output.write_text(json.dumps(dict(status='PYTHON_FINITE_CDE_SEARCH_PENDING_SECOND_IMPLEMENTATION',results=results,
        bounds='1session/3releasedunits and2sessions/2units, quantum2,budget2,one restart,5view modes,one staged observation; invariant-violation states terminal, unsafe continuations not searched',
        limits='atomic input persistence and trusted canonical selection abstract actual I/O/base proof; no neural inference, no unbounded liveness or performance guarantee; explicit R logging is not uniquely necessary because derived reservation is a positive control'),indent=2)+'\n')
