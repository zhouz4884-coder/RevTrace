"""C/D/V/I/J transition kernel. Trusted host receipts, not GPU attestation.

The pure step function is also the executable specification. ReceiptBroker
only admits single-use, operation-bound objects minted by trusted wrappers.
This is an API ownership boundary, not protection against hostile host Python.
"""
from dataclasses import dataclass, field
from copy import copy
from copy import deepcopy
import hashlib, json, threading, time

def sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),
        allow_nan=False).encode()).hexdigest()

class Denied(ValueError):pass

@dataclass
class State:
    contract: str
    epoch: int
    owner: float
    C: dict = field(default_factory=dict)
    D: dict = field(default_factory=dict)
    V: dict = field(default_factory=dict)
    I: dict = field(default_factory=dict)
    J: dict = field(default_factory=dict)
    leases: dict = field(default_factory=dict)
    ready: set = field(default_factory=set)
    publications: dict = field(default_factory=dict)
    prepared: dict = field(default_factory=dict)
    restored_input: bool = False
    recovery_roots: dict = field(default_factory=dict)

def need(condition, reason):
    if not condition:raise Denied(reason)

def check(k):
    for sid,c in k.C.items():
        d=k.D.get(sid,{}).get(c['v'])
        need(c['v']==0 or d==c,'installed state lacks durable selected fact')
        if k.restored_input:need(c['F']<=k.I[sid]['accepted'],'lost input obligation')
        v=k.V.get(sid,{'v':0,'F':0,'visible':0})
        need(v['v']<=c['v'] and v['F']<=c['F'],'consumer ahead of installed history')
        need(v['visible']>=v['F'],'visible certified root lost')
    for sid,i in k.I.items():
        need(0<=i['accepted']<=i['offered'] and i['accepted']<=i['reserved'],
             'input acceptance outside offered/reserved prefix')
    return k

def event_copy(state,kind,p):
    """Ordinary event-local COW; retained objects are immutable by this API.

    Top-level J/publication maps are shallow-copied, hence NOT an O(1) or
    bounded-memory claim. Every nested object this event mutates is copied.
    The deep-copy step stays the reference and is tested on the SAME events.
    """
    k=copy(state)
    fields={
        'recover-fact':['C','D','V','recovery_roots'],
        'input-sync-request':['prepared'],'input-synced':['prepared'],
        'worker-ready':['ready'],'dispatch':['J','leases'],'row-complete':['J'],
        'batch-drained':['leases'],'admission-request':['prepared'],
        'canonical-synced':['prepared','D'],'install':['C'],'publish':['publications'],
        'apply-request':['prepared'],'view-applied':['prepared','V'],'execution-failed':['ready']}
    for name in fields.get(kind,[]):setattr(k,name,copy(getattr(state,name)))
    if kind=='row-complete' and p.get('id') in k.J:k.J[p['id']]=dict(k.J[p['id']])
    if kind=='canonical-synced':
        req=state.prepared.get(p.get('operation'))
        if isinstance(req,dict) and req.get('sid') in state.D:k.D[req['sid']]=dict(state.D[req['sid']])
    return k

def step(state, kind, p,*,incremental=False):
    """Pure transition. All effects are approved BEFORE their external action.

    Sync completion, installation and actual application are distinct events.
    An adapter supplies validated P/Z/Y and actual execution provenance; it
    never supplies a success flag to waive a predicate.
    """
    k=event_copy(state,kind,p) if incremental else deepcopy(state);effects=[]
    need(p.get('epoch',k.epoch)==k.epoch,'old owner/epoch')
    need(p.get('owner',k.owner)==k.owner,'old owner incarnation')
    need(p.get('contract',k.contract)==k.contract,'wrong contract')
    if kind=='recover-fact':
        need(not k.restored_input,'recovery after input activation')
        sid=p['sid'];c=p['fact'];need(sid not in k.C,'duplicate recovery')
        need(c['v']>=0 and c['F']>=0,'invalid recovered fact')
        history=p.get('history',{c['v']:c} if c['v'] else {})
        need(set(history)==set(range(1,c['v']+1)),'recovery omitted durable admission identities')
        need(not c['v'] or history[c['v']]==c,'recovered current fact/history mismatch')
        need(len({f['txn'] for f in history.values()})==len(history),'recovered duplicate identity')
        k.C[sid]=c;k.D[sid]=history
        k.recovery_roots[sid]=(c['v'],c['F'])
        k.V[sid]=dict(v=0,F=0,visible=0,P='',text='',revision=0)
        effects=['publish-recovered-fact'] if c['v'] else []
    elif kind in ['input-sync-request','input-synced']:
        items=p['items']
        need(set(items)==set(k.C),'input session manifest mismatch')
        origins={i.get('origin') for i in items.values()}
        need(len(origins)<=1,'input session clocks disagree')
        for sid,i in items.items():
            old=k.I.get(sid,dict(accepted=0,offered=0,reserved=0))
            need(i['accepted']>=old['accepted'] and i['offered']>=old['offered'],'input regressed')
            need(i['accepted']>=k.C[sid]['F'],'accepted history shorter than canonical')
            if sid in k.I:
                need(i.get('origin')==old.get('origin'),'original input clock changed')
                if i['accepted']==old['accepted']:
                    need(i.get('prefix')==old.get('prefix'),'immutable accepted input changed')
                    need(i.get('sources')==old.get('sources'),'source revision without new durable input')
            if 'sources' in i:
                need(all(isinstance(v,int) and v>=0 for v in i['sources'].values()),'invalid source version')
                need(all(i['sources'].get(key,-1)>=v for key,v in old.get('sources',{}).items()),'source version regressed')
            if i['accepted']:need(len(i['prefix'])==64,'missing immutable input binding')
        if kind=='input-sync-request':
            need('input' not in k.prepared,'input synchronization already pending')
            k.prepared['input']=sha(items);effects=['fsync-input']
        else:
            if p.get('recovery'):need(not k.restored_input,'input recovery reentry')
            # Recovery and successful real fsync use the same validation.
            need(p.get('recovery') or k.prepared.get('input')==sha(items),'unrequested input receipt')
            k.I=items;k.restored_input=True;k.prepared.pop('input',None);effects=['input-ack']
    elif kind=='worker-ready':
        k.ready.add(p['worker'])
    elif kind=='dispatch':
        worker=p['worker'];need(worker in k.ready,'executor not ready')
        need(worker not in k.leases,'physical worker still leased')
        need(k.restored_input,'input obligations not restored')
        need(all(k.V[sid]['v']>=v and k.V[sid]['F']>=F for sid,(v,F) in k.recovery_roots.items()),
             'recovered facts not yet actually applied')
        ids=[]
        for job in p['jobs']:
            sid=job['sid'];c=k.C[sid];jid=job['id']
            need(jid not in k.J,'duplicate job identity')
            need(job['end']<=k.I[sid]['accepted'],'unaccepted audio dispatched')
            need(job['start']<job['end'] and job['rootF']<=job['end'],'future/empty input')
            need(job['parent']==c['v'],'job born from stale canonical parent')
            if job['role']=='authority':
                need(job['start']==c['F'] and job['inputP']==c['P'],'authority gap/parent input')
            if 'sources' in k.I[sid]:
                need(job.get('readset') and all(k.I[sid]['sources'].get(key)==version
                    for key,version in job['readset'].items()),'noncurrent source read at dispatch')
            k.J[jid]=dict(job,worker=worker,result=None);ids.append(jid)
        k.leases[worker]=ids;effects=['submit-frozen-batch']
    elif kind=='row-complete':
        j=k.J[p['id']];need(j['worker']==p['worker'],'cross-worker result')
        need(j['result'] is None,'duplicate row receipt')
        need(p['identity']==j['identity'],'changed job/input/contract identity')
        need(p['Z'] and p['P'] and len(p['textsha'])==64,'unbound complete selection/render')
        j['result']=p;effects=['accept-private-result' if j['role']=='proposal' else 'prepare-admission']
    elif kind=='batch-drained':
        ids=k.leases.get(p['worker']);need(ids is not None,'drain of unleased worker')
        need(all(k.J[j]['result'] is not None for j in ids),'drain before complete rows')
        del k.leases[p['worker']];effects=['reuse-worker']
    elif kind=='admission-request':
        sid=p['sid'];c=k.C[sid];j=k.J[p['job']];r=j['result'];f=p['fact']
        need(j['role']=='authority' and r is not None,'private/unselected canonical write')
        need(j['sid']==sid,'cross-session authority admission')
        if 'sources' in k.I[sid]:
            need(j.get('readset') and all(k.I[sid]['sources'].get(key)==version
                for key,version in j['readset'].items()),'source read invalidated before admission')
        need(p['operation'] not in k.prepared,'pending operation identity reused')
        need(j['parent']==c['v'] and j['start']==c['F'],'stale/gapped admission')
        need(f['v']==c['v']+1 and f['F']==j['end'],'invalid new frontier/version')
        need((f['P'],f['Z'],f['textsha'])==(r['P'],r['Z'],r['textsha']),'selected content changed')
        need(f['txn'] not in [d['txn'] for d in k.D[sid].values()],'duplicate transaction')
        need(f['F']<=k.I[sid]['accepted'],'unaccepted admission')
        k.prepared[p['operation']]=dict(type='admission',sid=sid,fact=f);effects=['fsync-canonical']
    elif kind=='canonical-synced':
        request=k.prepared.get(p['operation'])
        need(isinstance(request,dict) and request.get('type')=='admission','unmatched canonical sync operation')
        del k.prepared[p['operation']];sid=request['sid'];f=request['fact']
        need(f['v'] not in k.D[sid],'duplicate durable admission')
        k.D[sid][f['v']]=f;effects=['install-selected-state']
    elif kind=='install':
        sid=p['sid'];f=p['fact'];c=k.C[sid]
        need(k.D[sid].get(f['v'])==f,'install before matching fsync')
        need(f['v']==c['v']+1 and f['F']>c['F'],'installation not successor')
        k.C[sid]=f;effects=['publish-canonical']
    elif kind=='publish':
        sid=p['sid'];pub=p['publication'];key=p['key']
        need(key not in k.publications,'publication identity reused')
        if pub.get('mode'):
            effects=['withdraw-private-view']
        elif pub['canonical']:
            need(pub['fact']==k.C[sid],'publication not installed fact')
        else:
            j=k.J[pub['job']];r=j['result']
            need(j['role']=='proposal' and r is not None,'unselected private publication')
            need(j['sid']==sid,'cross-session private publication')
            need(pub['textsha']==r['textsha'] and pub['end']==j['end'],'private result relabelled')
            need(j['end']>k.C[sid]['F'],'stale-as-fresh publication')
        k.publications[key]=dict(pub,_sid=sid);effects=['enqueue-view']
    elif kind=='apply-request':
        sid=p['sid'];v=p['view'];old=k.V[sid];key=p['key'];pub=k.publications[key]
        need(pub['_sid']==sid,'cross-session consumer publication')
        need(p['operation'] not in k.prepared,'pending operation identity reused')
        need(v['revision']>old['revision'],'old consumer revision')
        need(v['v']>=old['v'],'consumer root regression')
        if v['v']:
            f=k.D[sid].get(v['v']);need(f is not None and f['F']==v['F'] and f['P']==v['P'],
                'consumer certified root not durable')
        if v['visible']>v['F']:
            node=k.J.get(v['private']);need(node and node['result'],'missing actual private result')
            need(node['sid']==sid,'cross-session private dependency')
            need(node['end']==v['visible'] and node['result']['textsha']==hashlib.sha256(v['text'].encode()).hexdigest(),
                 'private consumer text/frontier relabelled')
            seen=set()
            while not ((node['rootF']==v['F'] and node['inputP']==v['P']) or
                       (node['end']==v['F'] and node['result']['P']==v['P'])):
                need(node['id'] not in seen,'private chain cycle');seen.add(node['id'])
                parents=[j for j in k.J.values() if j['sid']==sid and j['role']=='proposal' and j['result'] and
                    j['end']==node['rootF'] and j['result']['P']==node['inputP'] and j['end']<node['end']]
                need(len(parents)==1,'private view incompatible with applied certified root');node=parents[0]
        elif v['v']:
            need(hashlib.sha256(v['text'].encode()).hexdigest()==f['textsha'],'certified consumer text changed')
        if pub['canonical']:need(v['v']==pub['fact']['v'],'wrong canonical publication applied')
        k.prepared[p['operation']]=dict(type='view',sid=sid,view=v);effects=['apply-view']
    elif kind=='view-applied':
        pending=k.prepared.get(p['operation'])
        need(isinstance(pending,dict) and pending.get('type')=='view','unmatched view completion operation')
        old=k.V[pending['sid']];v=pending['view']
        need(v['revision']>old['revision'] and v['v']>=old['v'],'stale view completion')
        del k.prepared[p['operation']];k.V[pending['sid']]=v
    elif kind=='execution-failed':
        k.ready.discard(p['worker']);effects=['retain-debt-no-new-dispatch']
    else:raise Denied('unknown transition '+kind)
    return check(k),effects

class ReceiptBroker:
    """Single-use boundary receipts; fields alone cannot forge completion."""
    def __init__(self):self.pending={}
    def issue(self,boundary,operation,payload):
        token=object();self.pending[token]=(boundary,operation,deepcopy(payload));return token
    def take(self,token,boundary,operation):
        need(token in self.pending,'unknown/consumed boundary receipt')
        b,o,p=self.pending[token];need((b,o)==(boundary,operation),'receipt operation misbinding')
        del self.pending[token];return p

class Kernel:
    def __init__(self,contract,epoch,owner,*,incremental=False):
        self.state=State(contract,epoch,owner);self.lock=threading.RLock();self.trace=[]
        self.broker=ReceiptBroker();self.cpu_seconds=0.
        self.incremental=bool(incremental)
    def event(self,boundary,kind,operation,payload):
        with self.lock:
            started=time.thread_time();receipt=self.broker.issue(boundary,operation,payload)
            p=self.broker.take(receipt,boundary,operation)
            state,effects=step(self.state,kind,p,incremental=self.incremental);self.state=state
            self.cpu_seconds+=time.thread_time()-started
            self.trace.append(dict(kind=kind,boundary=boundary,operation=operation,
                payload_sha256=sha(payload),effects=effects,observed_perf=time.perf_counter()))
            return effects
