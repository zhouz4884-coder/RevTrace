"""Explicit bounded protocol model, not production GPU evidence.

Every transition interleaving of the declared finite cut is exhausted. This is
an abstraction: one canonical transition, a private path of depth up to two,
one restart, immutable row-before-drain and a FIFO Consumer. It is NOT a proof
of arbitrary history, completeness of the fault model, or unconditional liveness.
An independently written JS checker must match before results may be cited.
"""
from collections import deque
from pathlib import Path
import argparse,hashlib,json

# State is deliberately a positional JSON array for cross-language identity.
M,F,V,P,E,G,OK,W,D,JP,JA,Q,UF,UP,VIS,BAD = range(16)
REL1,REL2,DP,CP,BP,RP,DA,CA,BA,RA,WS,SY,IN,PA,CR,RE,RT,GR = [1<<i for i in range(18)]
ACK=1<<18
ANCESTRY,GAP,FRESH,CHAIN,DURABLE = [1<<i for i in range(5)]
PROPERTIES=['authorized_ancestry','gap_free_commit','fresh_provisional_publication',
            'exact_chain_private_continuity','durable_certified_view']

def initial():return (0,0,0,0,0,0,False,False,False,-1,-1,(),0,0,False,0)
def encode(s):return json.dumps(s,separators=(',',':'))
def update(s,changes):
    a=list(s)
    for k,v in changes.items():a[k]=v
    return tuple(a)

def successors(s,c):
    mask=s[M];omit=c['omit'];case=c['case']
    target=1 if case=='covered' else 2
    boundary=1 if case=='ahead_equal' else 3
    if case=='covered':boundary=0
    a_parent=1 if case=='stale_parent' else 0
    a_input=9 if case=='stale_parent' else 0
    a_start=1 if case=='gap' else 0
    a_end=2 if case=='gap' else 1
    source_bad=case=='wrong_receipt';text_bad=case=='bad_render'
    def freshA():return omit=='epoch' or s[JA]==s[E]
    def legalA():return ((omit=='parent' or (a_parent==s[V] and a_input==s[P])) and
        (omit=='frontier' or (a_start==s[F] and a_end>s[F])) and freshA())
    def emit(bit,name,changes=None):
        return name,update(s,{M:mask|bit,**(changes or {})})
    if not mask&REL1:yield emit(REL1,'release-1')
    if mask&REL1 and not mask&REL2:yield emit(REL2,'release-2')
    # Dispatch only once in epoch0. Old completed receipts may still arrive in
    # epoch1; this models transport fencing, not reconnectable worker adoption.
    if s[E]==0 and mask&(REL1 if target==1 else REL2) and not mask&DP:
        yield emit(DP,'dispatch-private-frozen', {JP:s[E]})
    if mask&DP and not mask&CP:yield emit(CP,'row-complete-private')
    if mask&CP and not mask&BP:yield emit(BP,'batch-drained-private')
    if mask&CP and not mask&RP:
        stale=target<=s[F] or s[G]!=0 or s[JP]!=s[E]
        accept=(omit=='freshness' or not stale)
        q=s[Q]
        if accept:q=q+(('P',s[E],s[V],target,boundary,False),)
        yield emit(RP,'receive-private-and-publish' if accept else 'retire-private',
            {Q:q,BAD:s[BAD]|(FRESH if accept and stale else 0)})
    if s[E]==0 and mask&(REL2 if a_end==2 else REL1) and not mask&DA:
        yield emit(DA,'dispatch-authority-frozen',{JA:s[E]})
    if mask&DA and not mask&CA:yield emit(CA,'row-complete-authority')
    if mask&CA and not mask&BA:yield emit(BA,'batch-drained-authority')
    if mask&CA and not mask&RA:
        ok=(not source_bad or omit=='row_identity') and (not text_bad or omit=='render') and freshA()
        yield emit(RA,'receive-authority' if ok else 'reject-authority',{OK:ok})
    if s[OK] and not mask&WS and legalA():yield emit(WS,'append-WAL-incomplete',{W:False})
    if mask&WS and not mask&SY and s[OK] and legalA():
        yield emit(SY,'complete-frame-and-fsync',{W:True,D:True})
    if s[OK] and not mask&IN and legalA() and (s[D] or omit=='persist'):
        bad=s[BAD]
        if a_parent!=s[V] or a_input!=s[P] or source_bad or s[JA]!=s[E]:bad|=ANCESTRY
        if a_start!=s[F] or a_end<=s[F]:bad|=GAP
        yield emit(IN,'install-canonical',{F:a_end,V:s[V]+1,P:1,BAD:bad})
    if mask&IN and not mask&PA and s[F]:
        yield emit(PA,'publish-certified',{Q:s[Q]+(('A',s[E],s[V],s[F],s[P],text_bad),)})
    if mask&IN and not mask&ACK and s[F]:
        yield emit(ACK,'return-install-receipt',{BAD:s[BAD]|(DURABLE if not s[D] else 0)})
    # A simulated generation retirement is an owner invalidation, not GPU
    # cancellation. It may race only with an already dispatched private row.
    if mask&DP and not mask&RP and not mask&GR and mask&IN:
        yield emit(GR,'retire-private-generation',{G:1})
    if s[Q]:
        msg=s[Q][0];kind,epoch,version,end,p,badtext=msg
        uf,up,vis,bad=s[UF],s[UP],s[VIS],s[BAD]
        if epoch==s[E]:
            if kind=='A':
                uf=end;up=p
                if not s[D] or badtext:bad|=DURABLE
                # Whole provisional view may be retained only over a same-
                # boundary equality, never promoted to a certified suffix.
                if vis:
                    vis=target>uf and (omit=='chain' or boundary==up)
                if vis and boundary!=up:bad|=CHAIN
            elif end>uf:
                compatible=(uf==0 or (uf==1 and boundary==up))
                vis=compatible or omit=='chain'
                if vis and not compatible:bad|=CHAIN
        yield 'consume-FIFO',update(s,{Q:s[Q][1:],UF:uf,UP:up,VIS:vis,BAD:bad})
    if not mask&CR:
        # Only successful sync is guaranteed. A partial tail is ignored; full
        # checksummed corruption is fail-closed in separate production tests.
        yield emit(CR,'crash-restart-new-stream', {E:1,F:a_end if s[D] else 0,
            V:1 if s[D] else 0,P:1 if s[D] else 0,OK:False,W:s[D],
            Q:(),UF:0,UP:0,VIS:False,G:1})
    if mask&CR and s[D] and not mask&RE:
        yield emit(RE,'replay-render-and-republish',{Q:s[Q]+(('A',s[E],1,a_end,1,text_bad),)})
    if s[D] and not mask&RT:
        # An exact retry returns the durable fact, not another installation.
        yield emit(RT,'retry-returns-prior-receipt')

def explore(c,max_states=800000):
    root=initial();seen={root};todo=deque([root]);parent={root:None};labels={}
    witnesses={};transitions=0
    while todo:
        s=todo.popleft()
        for name,n in successors(s,c):
            transitions+=1
            if n in seen:continue
            seen.add(n);parent[n]=s;labels[n]=name;todo.append(n)
            if len(seen)>max_states:raise RuntimeError('state cutoff reached; not complete')
            for i,prop in enumerate(PROPERTIES):
                if n[BAD]&(1<<i) and prop not in witnesses:
                    path=[];cursor=n
                    while parent[cursor] is not None:
                        path.append({'action':labels[cursor],'state':json.loads(encode(cursor))});cursor=parent[cursor]
                    witnesses[prop]=list(reversed(path))
    state_hash=hashlib.sha256()
    for key in sorted(map(encode,seen)):state_hash.update((key+'\n').encode())
    return {'config':c,'complete':True,'states':len(seen),'transitions':transitions,
        'reachable_state_sha256':state_hash.hexdigest(),'violations':sorted(witnesses),
        'shortest_witnesses':witnesses}

def configs():
    for case in ['covered','ahead_equal','ahead_diff','bad_render','wrong_receipt','stale_parent','gap']:
        for omit in ['none','freshness','chain','render','persist','epoch','row_identity','parent','frontier']:
            yield {'case':case,'omit':omit}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--max-states',type=int,default=800000);a=p.parse_args()
    assert not a.output.exists();result=[]
    for c in configs():
        r=explore(c,a.max_states);result.append(r);print(c,r['states'],r['violations'],flush=True)
    assert all(not r['violations'] for r in result if r['config']['omit']=='none')
    a.output.write_text(json.dumps({'status':'PYTHON_COMPLETE_PENDING_INDEPENDENT_JS_CHECK',
        'bounds':'one canonical interval over two released frontiers, private depth<=2, one restart, immutable row before drain, one retry; seven cuts; finite complete BFS, not arbitrary history induction',
        'state_fields':['mask','F','version','P','epoch','private_generation','authority_accepted','complete_WAL','durable_WAL','private_job_epoch','authority_job_epoch','publication_FIFO','consumer_F','consumer_P','whole_provisional_visible','property_monitor_bits'],
        'results':result},indent=2)+'\n')
