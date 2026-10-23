"""Trusted render and local FIFO consumer. Never joins unproved text suffixes."""
from __future__ import annotations
import hashlib,heapq,json,queue,threading,time,re
from .dgft import digest_tokens
def text_sha(text):return hashlib.sha256(text.encode('utf8')).hexdigest()

class TrustedQwenRender:
    def __init__(self,tokenizer,parse,eos,budget=256):
        self.tokenizer,self.parse,self.eos,self.budget=tokenizer,parse,set(eos),int(budget)
    def __call__(self,job,Z):
        Z=list(Z)
        if not Z or len(Z)>self.budget:raise ValueError('invalid complete token budget')
        stops=[i for i,t in enumerate(Z) if t in self.eos]
        if stops and stops!=[len(Z)-1]:raise ValueError('EOS must terminate selected sequence')
        if not stops and len(Z)!=self.budget:raise ValueError('unterminated short selected sequence')
        tok=self.tokenizer;raw=tok.decode(job['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
        if job['chunk_id']>=2 and raw:
            ids=tok.encode(raw);k=5
            while True:
                prefix=tok.decode(ids[:max(0,len(ids)-k)])
                if '\ufffd' not in prefix or k>=len(ids):break
                k+=1
        raw=prefix+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        _,text=self.parse(raw,user_language=job['language'])
        return list(tok.encode(raw)),text

def validate_bound_text(render,job,result):
    P,text=render(job,result['token_ids'])
    if list(result['state_tokens'])!=P:raise ValueError('trusted render projection mismatch')
    if result['text'].encode('utf8')!=text.encode('utf8'):raise ValueError('trusted render text mismatch')
    return {'text_sha256':text_sha(text),'render_inputs':{'prompt_tokens':list(job['prompt_tokens']),'chunk_id':job['chunk_id'],'language':job['language'],'token_ids':list(result['token_ids']),'state_tokens':P},'rendered_text':text}

def replay_bound_text(render,event):
    proof=event.get('text_binding')
    if proof is None:raise ValueError('missing durable text binding')
    inp=proof['render_inputs'];P,text=render(inp,inp['token_ids'])
    cert=event['certificate']
    if (P!=inp['state_tokens'] or text_sha(text)!=proof['text_sha256'] or text.encode()!=event['committed_text'].encode()
        or digest_tokens(inp['token_ids'])!=cert['display_sha256'] or digest_tokens(P)!=cert['feedback_state_sha256']
        or digest_tokens(inp['prompt_tokens'])!=cert['prompt_sha256']):raise ValueError('recovered render/text mismatch')
    return text

class ContinuityView:
    """Trusted single-owner FIFO stream, independently versioned certified lane.

    A compatible whole provisional hypothesis is NEVER a certified suffix.
    Exact text-state equality at the same audio boundary and a complete causal
    chain permit only a provisional view. No token/audio alignment is inferred.
    """
    def __init__(self,policy='snapshot',fine_samples=32000,strict_bound=False):
        self.policy=policy;self.fine=fine_samples;self.states={};self.commits={};self.epoch=None;self.records=[];self.strict_bound=strict_bound;self.contract=None
    def consume(self,e,observed=None):
        kind=e['kind']
        if kind=='run-start':
            self.epoch=e.get('t0_perf');self.contract=e.get('contract_digest');self.states={};self.commits={};return
        sid=e.get('session_id')
        if kind=='commit':
            if self.strict_bound and e['certificate']['contract_digest']!=self.contract:raise ValueError('commit belongs to another declared contract')
            self.commits[sid,e['version']]=e;return
        if kind not in ['display','canonical-display']:return
        s=self.states.setdefault(sid,{'version':0,'F':0,'text':'','visible':0,'visible_text':'','nodes':{},'tentative':None,'buffer':[],'revision':0})
        if self.strict_bound and (e.get('contract_digest')!=self.contract or 'contract_epoch' not in e):raise ValueError('missing/wrong publication contract or epoch')
        incoming_epoch=e.get('contract_epoch',s.get('epoch'))
        if s.get('epoch') is not None and incoming_epoch!=s['epoch']:
            if incoming_epoch<s['epoch']:return
            raise ValueError('new epoch requires a fresh declared FIFO stream')
        if kind=='display' and e.get('canonical_version',e.get('version',0))<s['version']:return
        s['epoch']=incoming_epoch
        if e.get('display_revision',0)<=s['revision']:return
        before=s['visible'];oldtext=s['visible_text'];s['revision']=e.get('display_revision',s['revision']+1);retained=False;invalid=False
        if kind=='canonical-display':
            version=e['version']
            if version<s['version']:return
            if not e.get('recovered'):
                commit=self.commits.get((sid,version))
                if commit is None or commit['segment_id']!=e['transaction_id'] or commit['audio_end_sample']!=e['audio_end_sample']:raise ValueError('uninstalled canonical display')
                if e.get('canonical_projection_sha256') not in (None,digest_tokens(commit['next_prompt_tokens'])):raise ValueError('canonical P mismatch')
                if self.strict_bound and e.get('canonical_Z_sha256')!=commit['certificate']['display_sha256']:raise ValueError('canonical selected Z mismatch')
            if e.get('text_sha256') not in (None,text_sha(e['text'])):raise ValueError('canonical text binding mismatch')
            s.update(version=version,F=e['audio_end_sample'],text=e['text'],Psha=e.get('canonical_projection_sha256'),Zsha=e.get('canonical_Z_sha256'),transaction=e.get('transaction_id'),textsha=e.get('text_sha256'),buffer=[],stable_text=e['text'])
            tent=s['tentative']
            retained=bool(self.policy=='two_lane' and tent and tent['audio_end_sample']>s['F'] and self._compatible(s,tent,e.get('canonical_projection_sha256')))
            invalid=bool(tent and not retained)
            if retained:s.update(visible=tent['audio_end_sample'],visible_text=tent['text'])
            else:s.update(visible=s['F'],visible_text=s['text'],tentative=None)
        else:
            if e.get('canonical_version',e.get('version',0))<s['version'] or e['audio_end_sample']<=s['F']:return
            s['nodes'][e['job_id']]=e
            if self.policy=='two_lane' and s['version'] and not self._compatible(s,e,s.get('Psha')):
                invalid=True;s.update(visible=s['F'],visible_text=s['text'],tentative=None)
            elif self.policy.startswith('localagreement'):
                n=int(self.policy[-1]);s['buffer'].append(e['text']);s['buffer']=s['buffer'][-n:]
                text=s.get('stable_text',s['text'])
                if len(s['buffer'])==n:
                    # Credited LocalAgreement-n display adaptation: complete
                    # words for English, codepoints for no-whitespace CJK.
                    cjk=any('\u4e00'<=ch<='\u9fff' for ch in e['text'])
                    units=[list(t) if cjk else re.findall(r'\S+',t) for t in s['buffer']]
                    common=0
                    for group in zip(*units):
                        if len(set(group))!=1:break
                        common+=1
                    if cjk:candidate=e['text'][:common]
                    else:
                        spans=list(re.finditer(r'\S+',e['text']));candidate=e['text'][:spans[common-1].end()] if common else ''
                    # Never blank/withdraw the current confirmed view merely
                    # because a fresh buffer is not yet in agreement. Only an
                    # actual canonical correction can override that view.
                    if candidate.startswith(text):text=candidate
                s['stable_text']=text
                # Without word/audio alignment a partial stable prefix cannot
                # claim the entire source interval as legally displayed.
                s.update(visible=s['F'],visible_text=text,tentative=e)
            elif self.policy=='canonical_only':return
            else:s.update(visible=e['audio_end_sample'],visible_text=e['text'],tentative=e)
        common=0
        for a,b in zip(oldtext,s['visible_text']):
            if a!=b:break
            common+=1
        row={'kind':'consumer-view','source_kind':kind,'session_id':sid,'server_time':e.get('displayed',e['time']),'observed_perf':observed,'owner_incarnation':self.epoch,'contract_digest':self.contract,'canonical_epoch':s.get('epoch'),'canonical_version':s['version'],'certified_transaction':s.get('transaction'),'certified_Z_sha256':s.get('Zsha'),'certified_P_sha256':s.get('Psha'),'certified_text_sha256':s.get('textsha'),'certified_frontier':s['F'],'certified_text':s['text'],'valid_visible_frontier':s['visible'],'visible_text':s['visible_text'],'audio_rollback_samples':max(0,before-s['visible']),'erased_characters':len(oldtext)-common,'compatible_provisional_retained':retained,'tentative_invalidated':invalid,'joined_suffix':False,'policy':self.policy}
        self.records.append(row);return row
    def _compatible(self,s,node,Psha):
        if not Psha:return False
        seen=set()
        while node['job_id'] not in seen:
            seen.add(node['job_id']);chunk=node.get('chunk_id');inp=node.get('input_projection_sha256')
            if chunk is None or inp is None:return False
            if chunk==round(s['F']/self.fine) and inp==Psha:return True
            candidates=[p for p in s['nodes'].values() if p.get('end_window')==chunk and p.get('output_projection_sha256')==inp and p['audio_end_sample']>=s['F'] and p['audio_end_sample']<node['audio_end_sample'] and p.get('branch_generation')==node.get('branch_generation')]
            if len(candidates)!=1:return False
            node=candidates[0]
            if node['audio_end_sample']==s['F']:return node.get('output_projection_sha256')==Psha
        return False

class RealtimeConsumer:
    """Independent CPU thread and FIFO queue; not a browser or network proof."""
    def __init__(self,path,policy='snapshot',strict_bound=False):
        self.path=path;self.view=ContinuityView(policy,strict_bound=strict_bound);self.q=queue.Queue();self.error=None;self.base=None;self.cpu_seconds=0.;self.rows=[];self.max_depth=0
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def put(self,row):
        # Immutable serialized copy also makes actual payload/copy cost visible.
        self.q.put(json.dumps(row,ensure_ascii=False));self.max_depth=max(self.max_depth,self.q.qsize())
    def _run(self):
        try:
            while True:
                raw=self.q.get()
                if raw is None:break
                began=time.thread_time();e=json.loads(raw);now=time.perf_counter()
                if e['kind']=='run-start':self.base=e['t0_perf']
                row=self.view.consume(e,now)
                if row:
                    applied=time.perf_counter();row['consumer_received_perf']=now;row['observed_perf']=applied
                    row['observed']=applied-self.base;row['view_application_seconds']=applied-now;self.rows.append(row)
                self.cpu_seconds+=time.thread_time()-began
        except BaseException as ex:self.error=repr(ex)
    def close(self):
        self.q.put(None);self.thread.join(timeout=20)
        if self.thread.is_alive() or self.error:raise RuntimeError('consumer failed: '+str(self.error))
        with self.path.open('w',encoding='utf8') as f:
            for row in self.rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        return {'records':len(self.rows),'consumer_cpu_seconds':self.cpu_seconds,'queue_max_depth':self.max_depth,'scope':'local FIFO actual consumer observation; no browser/network claim'}
