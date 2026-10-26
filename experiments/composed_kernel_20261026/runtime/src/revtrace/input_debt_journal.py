"""Single-owner durable input-prefix obligations, never canonical model state.

Prepared immutable audio and its manifest must survive recovery. This journal
does not persist incoming waveform bytes, provide a network server, or attest
GPU execution. It pins actually supplied prefix hashes before acceptance ACK.
Conventional checksummed WAL/locking are credited implementation techniques.
"""
from pathlib import Path
import hashlib,json,os,struct,time

def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(encode(x)).hexdigest()

class InputJournalError(RuntimeError):pass

class InputJournal:
    def __init__(self,path,*,manifest_sha256,policy_sha256):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        if len(manifest_sha256)!=64 or len(policy_sha256)!=64:raise ValueError('pinned SHA256 identities required')
        self.context=dict(manifest_sha256=manifest_sha256,policy_sha256=policy_sha256)
        self.lockfd=None;self.fd=None;self.poisoned=False;self.seq=0;self.previous=''
        self.accepted={};self.receipts={};self.snapshot=None;self.truncated_tail_bytes=0;self.fsync_calls=0;self.fsync_seconds=0.
        try:
            self.lockfd=os.open(str(self.path)+'.lock',os.O_CREAT|os.O_RDWR|getattr(os,'O_BINARY',0),0o600)
            if os.name=='nt':
                import msvcrt
                if os.fstat(self.lockfd).st_size==0:os.write(self.lockfd,b'\0');os.fsync(self.lockfd)
                os.lseek(self.lockfd,0,os.SEEK_SET);msvcrt.locking(self.lockfd,msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            existed=self.path.exists()
            self.fd=os.open(self.path,os.O_CREAT|os.O_RDWR|os.O_APPEND|getattr(os,'O_BINARY',0),0o600)
            if not existed and os.name!='nt':
                directory=os.open(self.path.parent,os.O_RDONLY|getattr(os,'O_DIRECTORY',0))
                try:os.fsync(directory)
                finally:os.close(directory)
            self._read()
            if not self.seq:self._append(dict(kind='input-genesis',**self.context))
        except BaseException:
            self.close();raise
    def _apply(self,r):
        if r['sequence']!=self.seq or r['previous_sha256']!=self.previous:raise InputJournalError('input log chain/sequence')
        if self.seq==0:
            if r.get('kind')!='input-genesis' or any(r.get(k)!=v for k,v in self.context.items()):raise InputJournalError('input log context')
        elif r.get('kind')=='accepted-input':
            sid=r['session_id'];start=self.accepted.get(sid,0)
            if r['from_sample']!=start or not start<r['to_sample'] or len(r['prefix_sha256'])!=64:raise InputJournalError('input prefix gap/overlap')
            identity={k:r[k] for k in ['session_id','from_sample','to_sample','prefix_sha256']}
            if r['decision_id']!=digest(dict(identity,**self.context)):raise InputJournalError('input receipt identity')
            self.accepted[sid]=r['to_sample'];self.receipts[sid,r['to_sample']]=dict(r)
        elif r.get('kind')=='envelope-snapshot':
            snap=r['snapshot'];self.validate_snapshot(snap)
            if r['snapshot_sha256']!=digest(snap):raise InputJournalError('input snapshot identity')
            self.snapshot=json.loads(json.dumps(snap))
            self.accepted={int(sid):v['accepted'] for sid,v in snap['sessions'].items()}
        else:raise InputJournalError('unknown input record')
        self.previous=digest(r);self.seq+=1
    def _read(self):
        os.lseek(self.fd,0,os.SEEK_SET);blocks=[]
        while True:
            block=os.read(self.fd,1024*1024)
            if not block:break
            blocks.append(block)
        raw=b''.join(blocks);offset=0
        while offset<len(raw):
            if len(raw)-offset<4:break
            length=struct.unpack_from('>I',raw,offset)[0]
            if not 0<length<=1_000_000:raise InputJournalError('invalid input frame length')
            end=offset+4+length+32
            if end>len(raw):break
            payload=raw[offset+4:offset+4+length]
            if hashlib.sha256(payload).digest()!=raw[offset+4+length:end]:raise InputJournalError('complete input frame checksum corruption')
            self._apply(json.loads(payload));offset=end
        if offset<len(raw):
            self.truncated_tail_bytes=len(raw)-offset;os.ftruncate(self.fd,offset);os.fsync(self.fd)
        os.lseek(self.fd,0,os.SEEK_END)
    def _sync(self):
        start=time.perf_counter();os.fsync(self.fd)
        self.fsync_seconds+=time.perf_counter()-start;self.fsync_calls+=1
    def _append(self,fields):
        if self.fd is None or self.poisoned:raise InputJournalError('input journal unavailable/poisoned')
        r=dict(fields,sequence=self.seq,previous_sha256=self.previous)
        raw=encode(r);frame=struct.pack('>I',len(raw))+raw+hashlib.sha256(raw).digest()
        try:
            view=memoryview(frame)
            while view:
                n=os.write(self.fd,view)
                if n<=0:raise OSError('short input journal write')
                view=view[n:]
            self._sync()
            self._apply(r)
        except BaseException:
            self.poisoned=True;raise
        return dict(r)
    def accept(self,sid,*,from_sample,to_sample,prefix_sha256):
        if self.poisoned:raise InputJournalError('input journal poisoned')
        if type(sid) is not int or type(from_sample) is not int or type(to_sample) is not int or from_sample<0 or to_sample<=from_sample or len(prefix_sha256)!=64:
            raise ValueError('actual positive input prefix required')
        prior=self.receipts.get((sid,to_sample))
        if prior:
            if (prior['from_sample'],prior['prefix_sha256'])!=(from_sample,prefix_sha256):raise InputJournalError('changed input retry')
            return dict(prior,idempotent_input_retry=True)
        if from_sample!=self.accepted.get(sid,0):raise InputJournalError('accepted input cannot skip a prefix')
        fields=dict(session_id=sid,from_sample=from_sample,to_sample=to_sample,prefix_sha256=prefix_sha256)
        fields.update(kind='accepted-input',decision_id=digest(dict(fields,**self.context)))
        return self._append(fields)
    def validate_snapshot(self,snap):
        if type(snap.get('budget')) is not int or snap['budget']<=0 or type(snap.get('epoch')) is not int or snap['epoch']<1:
            raise InputJournalError('snapshot budget/epoch')
        if not isinstance(snap.get('origin_perf'),(int,float)) or snap['origin_perf']<0:
            raise InputJournalError('snapshot original clock')
        old=self.snapshot
        if old and (snap['budget']!=old['budget'] or snap['origin_perf']!=old['origin_perf'] or snap['epoch']<old['epoch']):
            raise InputJournalError('snapshot changed policy/clock or regressed epoch')
        if old and set(snap['sessions'])!=set(old['sessions']):raise InputJournalError('session manifest changed')
        reserved=0
        for sid,s in snap['sessions'].items():
            int(sid)
            for key in ['offered','accepted','certified','reserved','version','visible','visible_version']:
                if type(s[key]) is not int:raise InputJournalError('noninteger audio snapshot')
            if not 0<=s['certified']<=s['accepted']<=s['offered'] or s['reserved']<s['accepted']:
                raise InputJournalError('snapshot loses accepted debt')
            if s['rejected'] and (s['accepted'] or not s.get('rejection_reason')):raise InputJournalError('rejection erased accepted input')
            prior=old['sessions'][sid] if old else None
            if s['accepted']<self.accepted.get(int(sid),0):raise InputJournalError('input prefix regressed')
            if s['accepted'] and len(s.get('accepted_prefix_sha256',''))!=64:raise InputJournalError('unbound accepted audio')
            if prior:
                if s['offered']<prior['offered'] or s['certified']<prior['certified']:raise InputJournalError('input/canonical snapshot regressed')
                if prior['rejected'] and not s['rejected']:raise InputJournalError('terminal rejection forgotten')
                if s['accepted']==prior['accepted'] and s.get('accepted_prefix_sha256','')!=prior.get('accepted_prefix_sha256',''):
                    raise InputJournalError('same accepted prefix changed audio')
            reserved+=s['reserved']-s['certified']
        if reserved>snap['budget']:raise InputJournalError('snapshot exceeds certified-debt credit')
    def checkpoint(self,snapshot):
        self.validate_snapshot(snapshot)
        frozen=json.loads(json.dumps(snapshot,allow_nan=False))
        return self._append(dict(kind='envelope-snapshot',snapshot=frozen,snapshot_sha256=digest(frozen)))
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None
        if self.lockfd is not None:
            # Closing releases the OS lock; only this journal's own handle.
            os.close(self.lockfd);self.lockfd=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
