"""Minimal asynchronous structured-memory application, not an ASR emulation.

LangGraph checkpoints its background computation. A separate transactional
document/memory store controls cross-thread latest-read eligibility. It is not
claimed that the framework promised to atomically coordinate that store.
"""
from pathlib import Path
from copy import deepcopy
import sqlite3,json,hashlib,time,threading,sys
from contextlib import contextmanager
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'runtime/src'))
from revtrace.composed_kernel import Kernel,Denied,sha

def textsha(s):return hashlib.sha256(s.encode()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))

class ProjectStore:
    def __init__(self,path,task,origin):
        self.path=Path(path);assert not self.path.exists();self.lock=threading.RLock();self.origin=origin
        with self.connect() as db:
            db.executescript('CREATE TABLE docs(k TEXT PRIMARY KEY,version INTEGER,text TEXT); CREATE TABLE inputs(seq INTEGER PRIMARY KEY,payload TEXT,origin REAL); CREATE TABLE memory(k TEXT PRIMARY KEY,payload TEXT,readset TEXT,receipt TEXT); CREATE TABLE journal(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,payload TEXT);')
            for i,d in enumerate(task['source_documents'],1):
                db.execute('INSERT INTO docs VALUES(?,?,?)',(d['key'],d['version'],d['text']))
                db.execute('INSERT INTO inputs VALUES(?,?,?)',(i,canonical(d),origin))
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30,check_same_thread=False);db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:yield db
        finally:db.close()
    def snapshot(self):
        with self.lock,self.connect() as db:
            docs=[dict(key=k,version=v,text=t) for k,v,t in db.execute('SELECT k,version,text FROM docs ORDER BY k')]
            inputs=list(db.execute('SELECT seq,payload,origin FROM inputs ORDER BY seq'))
            return dict(docs=docs,readset={d['key']:d['version'] for d in docs},accepted=len(inputs),prefix=sha(inputs),origin=self.origin)
    def revise(self,revision):
        with self.lock,self.connect() as db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT version FROM docs WHERE k=?',(revision['key'],)).fetchone()[0]
            assert revision['version']==old+1
            db.execute('UPDATE docs SET version=?,text=? WHERE k=?',(revision['version'],revision['text'],revision['key']))
            seq=db.execute('SELECT count(*) FROM inputs').fetchone()[0]+1
            db.execute('INSERT INTO inputs VALUES(?,?,?)',(seq,canonical(revision),self.origin))
    def planned_revision(self,revision):
        s=self.snapshot()
        with self.connect() as db:rows=list(db.execute('SELECT seq,payload,origin FROM inputs ORDER BY seq'))
        assert s['readset'][revision['key']]+1==revision['version']
        s['readset'][revision['key']]=revision['version'];s['accepted']+=1
        s['prefix']=sha(rows+[(s['accepted'],canonical(revision),self.origin)])
        return s
    def install(self,value,readset,receipt,check_versions=True):
        with self.lock,self.connect() as db:
            db.execute('BEGIN IMMEDIATE');versions=dict(db.execute('SELECT k,version FROM docs'))
            if check_versions and any(versions.get(k)!=v for k,v in readset.items()):return False
            db.execute('INSERT INTO memory VALUES(?,?,?,?) ON CONFLICT(k) DO UPDATE SET payload=excluded.payload,readset=excluded.readset,receipt=excluded.receipt',
                ('project',canonical(value),canonical(readset),canonical(receipt)))
            db.execute('INSERT INTO journal(kind,payload) VALUES(?,?)',('selected-memory',canonical(dict(value=value,readset=readset,receipt=receipt))))
        return True
    def memory(self):
        with self.connect() as db:
            row=db.execute('SELECT payload,readset,receipt FROM memory WHERE k="project"').fetchone()
            return None if row is None else dict(value=json.loads(row[0]),readset=json.loads(row[1]),receipt=json.loads(row[2]))

class MemoryKernelAdapter:
    """Optional latest-read adapter condition in addition to C1/C2/C3.

    Source versions are bound from actual two-document reads; a canonical
    parent alone does not imply that independently revised sources are current.
    Standard OCC receives exactly the same latest-read rule.
    """
    def __init__(self,store,contract):
        self.store=store;self.k=Kernel(contract,1,store.origin);self.counter=0
        self.k.event('validated-genesis','recover-fact','boot',dict(sid=0,fact=dict(v=0,F=0,P=sha({}),Z='',textsha=textsha('{}'),txn='')))
        self.sync_input(recovery=True);self.k.event('worker-ready','worker-ready','a',dict(worker='a'))
    def items(self,s):return {0:dict(accepted=s['accepted'],offered=s['accepted'],reserved=s['accepted'],prefix=s['prefix'],origin=s['origin'],sources=s['readset'])}
    def sync_input(self,recovery=False):
        s=self.store.snapshot();items=self.items(s)
        if not recovery:self.k.event('input-store-plan','input-sync-request','input',dict(items=items))
        self.k.event('actual-durable-input-store','input-synced','input',dict(items=items,recovery=recovery))
    def revise(self,revision):
        with self.k.lock,self.store.lock:
            planned=self.items(self.store.planned_revision(revision))
            self.k.event('source-input-plan','input-sync-request','input',dict(items=planned))
            self.store.revise(revision)
            actual=self.items(self.store.snapshot());assert actual==planned
            self.k.event('actual-source-input-commit','input-synced','input',dict(items=actual))
    def dispatch(self,snapshot,request):
        self.counter+=1;c=self.k.state.C[0];jid='authority-'+str(self.counter)
        job=dict(id=jid,sid=0,role='authority',parent=c['v'],start=c['F'],end=snapshot['accepted'],
            rootF=c['F'],inputP=c['P'],readset=snapshot['readset'],identity=request['identity'])
        self.k.event('actual-frozen-input','dispatch',jid,dict(worker='a',jobs=[job]));return job
    def complete(self,job,result):
        self.k.event('complete-selection-and-render','row-complete',job['id'],dict(id=job['id'],worker='a',identity=result['request_identity'],
            Z=sha(result['new_tokens']),P=sha(result['value']),textsha=textsha(canonical(result['value']))))
        # Neural call synchronizes its physical device before this receipt.
        self.k.event('actual-call-drained','batch-drained',job['id'],dict(worker='a'))
    def install(self,job,result):
        with self.k.lock,self.store.lock:return self._install_locked(job,result)
    def _install_locked(self,job,result):
        c=self.k.state.C[0];f=dict(v=c['v']+1,F=job['end'],P=sha(result['value']),Z=sha(result['new_tokens']),
            textsha=textsha(canonical(result['value'])),txn=job['id'])
        op='wal:'+job['id']
        try:self.k.event('prepare-latest-read','admission-request',op,dict(sid=0,job=job['id'],operation=op,fact=f))
        except Denied:return False
        assert self.store.install(result['value'],job['readset'],dict(job=job,fact=f),check_versions=True)
        self.k.event('real-sqlite-commit','canonical-synced',op,dict(operation=op))
        self.k.event('owner-install','install',op,dict(sid=0,fact=f))
        rev=f['v'];key=(0,rev)
        self.k.event('publication','publish',str(key),dict(sid=0,key=key,publication=dict(canonical=True,fact=f)))
        view=dict(v=f['v'],F=f['F'],P=f['P'],visible=f['F'],text=canonical(result['value']),revision=rev,private=None)
        apply='apply:'+str(key)
        self.k.event('actual-memory-consumer','apply-request',apply,dict(sid=0,key=key,view=view,operation=apply))
        # The actual consumer reads the committed value, under the same lock.
        with self.k.lock:
            assert self.store.memory()['value']==result['value']
            self.k.event('actual-memory-read-applied','view-applied',apply,dict(operation=apply))
        return True

def update_messages(task,snapshot):
    docs='\n'.join(d['text'] for d in snapshot['docs'])
    return [dict(role='system',content='Extract project memory from the source documents. Return only a JSON object with exactly the string keys destination and owner. Copy the named destination and coordinator accurately; no explanation.'),
            dict(role='user',content=f"Project: {task['project']}\nSource documents:\n{docs}")]

def answer_messages(task,memory):
    return [dict(role='system',content='Answer the project question using only the stored project memory. Return only JSON with exactly the string keys destination and owner. Do not invent changes.'),
            dict(role='user',content='Stored project memory: '+canonical(memory)+'\nQuestion: '+task['question'])]
