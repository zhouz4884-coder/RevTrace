"""Small real two-GPU service for the fixed StreamCorrect adaptation.

Authority always executes the published recognizer + learned selector. Private
uses an identity prediction through the same selected-feedback update adapter.
No recorded neural output or recorded runtime is replayed.
"""
from __future__ import annotations
import argparse,datetime,hashlib,importlib.metadata,json,multiprocessing as mp,os,pathlib,platform,queue,subprocess,sys,threading,time,traceback
from feedback_contract import FeedbackCut,BranchStep,Reconciler,digest
from native_worker import worker_main

def put(path,x):path.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def verify_source(path):
    root=pathlib.Path(__file__).resolve().parent;m=json.loads(path.read_text())
    def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    if git('rev-parse','--show-toplevel').replace('\\','/')!=root.as_posix():raise ValueError('not an independent execution checkout')
    if git('rev-parse','HEAD')!=m['source_commit'] or git('status','--porcelain','--untracked-files=all'):raise ValueError('actual native source commit/clean gate')
    files=set(git('ls-files','-z').split('\x00'))-{''}
    if files!={x['path'] for x in m['files']}:raise ValueError('native complete source manifest mismatch')
    for x in m['files']:
        p=root/x['path'];b=p.read_bytes()
        if len(b)!=x['bytes'] or hashlib.sha256(b).hexdigest()!=x['sha256']:raise ValueError('native source bytes changed')
    return dict(source_commit=m['source_commit'],source_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),files_verified=len(files),source_clean=True)
class Journal:
    def __init__(self,path,fsync=False):self.f=open(path,'x',encoding='utf-8');self.fsync=fsync
    def write(self,x):
        self.f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n');self.f.flush()
        if self.fsync:os.fsync(self.f.fileno())
    def close(self):self.f.close()

class Consumer:
    def __init__(self,initials,path,origin):
        self.q=queue.Queue();self.error=None;self.rows=[];self.origin=origin
        self.states={sid:Reconciler(c,True) for sid,c in initials.items()};self.processed={sid:0 for sid in initials}
        self.log=Journal(path);self.t=threading.Thread(target=self.run,daemon=True);self.t.start()
    def publish(self,e):self.q.put(e)
    def run(self):
        try:
            while True:
                e=self.q.get()
                if e is None:return
                sid=e['source_id'];r=self.states[sid]
                if e['kind']=='canonical':
                    c=FeedbackCut(e['state']);r.install(c);self.processed[sid]=max(self.processed[sid],e['processed_frontier'])
                elif e['kind']=='private':
                    if r.canonical.sha256!=e['canonical_sha']:raise ValueError('publication canonical clock/order changed')
                    previous=r.canonical;steps=[]
                    for s in e['steps']:
                        start=FeedbackCut(s['start']);end=FeedbackCut(s['end'])
                        step=BranchStep(s['job_id'],start.sha256,start,end)
                        if not start.same(previous):raise ValueError('consumer independently rejected branch chain')
                        steps.append(step);previous=end
                    # A completed recomputation behind an already legal view
                    # cannot by itself retract it. Native state compatibility
                    # at canonical installation governs necessary withdrawal.
                    if previous.frontier>=r.tail.frontier:r.steps=steps
                else:raise ValueError('unknown native Consumer publication')
                v=r.visible();v['certified_frontier']=self.processed[sid]
                if not v['text']:v['visible_frontier']=0
                row=dict(kind=e['kind'],source_id=sid,observed=time.perf_counter(),**v)
                self.rows.append(row);self.log.write(row)
        except BaseException:self.error=traceback.format_exc()
    def close(self):
        self.q.put(None);self.t.join(timeout=30);self.log.close()
        if self.t.is_alive():raise RuntimeError('actual consumer did not drain')
        if self.error:raise RuntimeError(self.error)

class Power:
    def __init__(self,path):self.stop=threading.Event();self.rows=[];self.path=path;self.t=threading.Thread(target=self.run,daemon=True);self.t.start()
    def run(self):
        with open(self.path,'x',encoding='utf-8') as f:
            while not self.stop.is_set():
                before=time.perf_counter()
                x=subprocess.check_output(['nvidia-smi','--query-gpu=index,power.draw','--format=csv,noheader,nounits'],text=True)
                watts={int(a.split(',')[0]):float(a.split(',')[1]) for a in x.splitlines() if a.strip()}
                row=dict(time=(before+time.perf_counter())/2,watts=watts);self.rows.append(row)
                f.write(json.dumps(row)+'\n');f.flush();self.stop.wait(.10)
    def close(self):self.stop.set();self.t.join(timeout=15)
    def energy(self,start,end):
        by={}
        for gpu in (0,1):
            pts=sorted((r['time'],r['watts'][gpu]) for r in self.rows if gpu in r['watts'])
            if len(pts)<2 or pts[0][0]>start or pts[-1][0]<end:raise ValueError('power integration lacks actual boundary samples')
            val=0.
            for (a,x),(b,y) in zip(pts,pts[1:]):
                lo=max(start,a);hi=min(end,b)
                if hi<=lo:continue
                vl=x+(y-x)*(lo-a)/(b-a);vh=x+(y-x)*(hi-a)/(b-a);val+=(vl+vh)/2*(hi-lo)
            by[str(gpu)]=val
        return dict(gpu_joules=by,total_joules=sum(by.values()))

def paired_metrics(sources,rows,origin,ended):
    frontiers=[];credit=0.;latd=[];latc=[];rollbacks=0
    for source in sources:
        sid=source['source_id'];n=source['frames'];past=0;observed=[r for r in rows if r['source_id']==sid]
        for a,b in zip(observed,observed[1:]):rollbacks+=int(b['visible_frontier']<a['visible_frontier'])
        for F in list(range(8000,n,8000))+[n]:
            offered=origin+F/16000
            d=next((r['observed']-offered for r in observed if r['observed']>=offered and r['visible_frontier']>=F),None)
            c=next((r['observed']-offered for r in observed if r['observed']>=offered and r['certified_frontier']>=F),None)
            delta=(F-past)/16000;past=F;ok=d is not None and c is not None and d<=2.0 and c<=8.0
            if ok:credit+=delta
            if d is not None:latd.append(d)
            if c is not None:latc.append(c)
            frontiers.append(dict(source_id=sid,frontier=F,offered=offered,seconds=delta,D=d,C=c,dual_met=ok))
    def p99(a):
        if not a:return None
        import math
        return sorted(a)[max(0,math.ceil(.99*len(a))-1)]
    return dict(offered_audio_seconds=sum(x['frames']/16000 for x in sources),dual_deadline_audio_credit_seconds=credit,
        valid_delay_p99=p99(latd),certified_delay_p99=p99(latc),offered_frontiers=len(frontiers),
        fully_valid_frontiers=len(latd),fully_certified_frontiers=len(latc),visible_audio_rollbacks=rollbacks,
        service_wall_seconds=ended-origin,frontier_rows=frontiers)

def serve(settings,arm,out):
    if arm not in ('sequential','drop','joint'):raise ValueError(arm)
    ctx=mp.get_context('spawn');result=ctx.Queue();commands={r:ctx.Queue() for r in ('authority','private')};children={}
    ready={};logs=Journal(out/'native_jobs.jsonl');events=Journal(out/'events.jsonl');canon=Journal(out/'canonical_wal.jsonl',True);ingress=Journal(out/'accepted_input_wal.jsonl',True)
    power=Power(out/'power.jsonl');consumer=None
    try:
        for role,gpu in [('authority',0),('private',1)]:
            if role=='private' and arm=='sequential':continue
            child=ctx.Process(target=worker_main,args=(role,gpu,settings,commands[role],result));child.start();children[role]=child
        deadline=time.perf_counter()+600
        while len(ready)<len(children):
            if time.perf_counter()>deadline:raise TimeoutError('native worker initialization')
            try:r=result.get(timeout=.2)
            except queue.Empty:
                if any(not c.is_alive() for c in children.values()):raise RuntimeError('native worker exited before ready')
                continue
            if r['kind']=='failed':raise RuntimeError(r['traceback'])
            if r['kind']!='ready':raise ValueError('unexpected native initialization message')
            ready[r['role']]=r
        source_ids=[x['source_id'] for x in settings['sources']];sources={x['source_id']:x for x in settings['sources']}
        initial={sid:FeedbackCut(ready['authority']['initials'][sid]) for sid in source_ids}
        if 'private' in ready:
            for sid in source_ids:
                if not initial[sid].same(FeedbackCut(ready['private']['initials'][sid])):raise ValueError('native genesis full-state mismatch')
        owners={sid:Reconciler(initial[sid],arm=='joint') for sid in source_ids};accepted={sid:0 for sid in source_ids};processed={sid:0 for sid in source_ids}
        origin=time.perf_counter()+1.;consumer=Consumer(initial,out/'consumer.jsonl',origin)
        busy={role:None for role in children};cursor={role:0 for role in children};sequence=0;histories={sid:[] for sid in source_ids};selections=[];reconciliations=[]
        put(out/'READY.json',ready);put(out/'ORIGIN.json',dict(origin_perf=origin,cadence_seconds=.5,original_D=2.,original_C=8.))
        end_by=origin+300
        while True:
            now=time.perf_counter()
            if now>end_by:raise TimeoutError('bounded native application service')
            if consumer.error:raise RuntimeError(consumer.error)
            for sid in source_ids:
                n=sources[sid]['frames'];elapsed=max(0.,now-origin)
                a=n if elapsed>=n/16000 else min(n,int(elapsed/.5)*8000)
                if a>accepted[sid]:
                    ingress.write(dict(source_id=sid,accepted=a,observed=now,original_offer=origin+a/16000,audio_sha256=sources[sid]['audio_sha256']))
                    accepted[sid]=a
            while True:
                try:r=result.get_nowait()
                except queue.Empty:break
                if r['kind']=='failed':raise RuntimeError(r['traceback'])
                if r['kind']!='completed':raise ValueError('unexpected worker service message')
                role=r['role'];job=busy[role]
                if job is None or job['job_id']!=r['job_id']:raise ValueError('native result worker/job mismatch')
                busy[role]=None;logs.write(r);sid=r['source_id'];owner=owners[sid];start=FeedbackCut(r['start']);finish=FeedbackCut(r['end'])
                if role=='authority':
                    if not start.same(owner.canonical):raise ValueError('trusted native feedback sequence changed')
                    in_flight=busy.get('private')
                    concurrent=(in_flight is not None and in_flight['source_id']==sid and in_flight['end']>finish.frontier)
                    canon.write(dict(source_id=sid,state=finish.state,state_sha256=finish.sha256,selected=r['record']['selected_correction']))
                    installed_now=time.perf_counter()
                    recon=owner.install(finish);recon.update(source_id=sid,frontier=finish.frontier,time=installed_now,
                        private_pending_ahead=concurrent,pending_job=in_flight['job_id'] if concurrent else None)
                    reconciliations.append(recon)
                    # Empty initial-buffer updates advance state but earn no
                    # processed-audio service credit until a real native model call.
                    if r['record'].get('native_model_evaluated'):processed[sid]=finish.frontier
                    histories[sid].append(dict(F=finish.frontier,state=finish.state,state_sha256=finish.sha256,token_ids=r['record']['token_ids']))
                    if r['record']['selected_correction'] is not None:selections.append(dict(source_id=sid,frontier=finish.frontier,changed=r['record']['selection_changed']))
                    consumer.publish(dict(kind='canonical',source_id=sid,state=finish.state,processed_frontier=processed[sid]))
                else:
                    still_eligible=start.same(owner.tail) and (arm=='joint' or job['canonical_sha']==owner.canonical.sha256)
                    if still_eligible:
                        owner.append(BranchStep(job['job_id'],start.sha256,start,finish))
                        if r['record'].get('native_model_evaluated'):
                            consumer.publish(dict(kind='private',source_id=sid,canonical_sha=owner.canonical.sha256,
                                steps=[dict(job_id=s.job_id,start=s.start.state,end=s.end.state) for s in owner.steps]))
                    events.write(dict(kind='private-admission',job_id=job['job_id'],source_id=sid,eligible=still_eligible,returned=now))
            if all(owners[sid].canonical.frontier==sources[sid]['frames'] for sid in source_ids) and all(x is None for x in busy.values()):break
            for role in children:
                if busy[role] is not None:continue
                for pos in range(len(source_ids)):
                    idx=(cursor[role]+pos)%len(source_ids);sid=source_ids[idx];owner=owners[sid]
                    start=owner.canonical if role=='authority' else owner.tail;n=sources[sid]['frames']
                    if start.frontier>=n:continue
                    target=min(n,start.frontier+8000)
                    if target>accepted[sid]:continue
                    if role=='private' and target>owner.canonical.frontier+32000:continue
                    sequence+=1;job=dict(job_id=f'{role}-{sequence:06d}',source_id=sid,start=start.state,end=target,canonical_sha=owner.canonical.sha256)
                    busy[role]=job;commands[role].put(job);cursor[role]=(idx+1)%len(source_ids)
                    events.write(dict(kind='dispatch',role=role,job_id=job['job_id'],source_id=sid,start=start.frontier,end=target,dispatched=time.perf_counter()))
                    break
            if any(not c.is_alive() for c in children.values()):raise RuntimeError('native worker exited while serving')
            time.sleep(.001)
        consumer.close();finished=time.perf_counter()
        metrics=paired_metrics(settings['sources'],consumer.rows,origin,finished)
        put(out/'CANONICAL_HISTORIES.json',histories);put(out/'SELECTIONS.json',selections);put(out/'RECONCILIATION.json',reconciliations)
        put(out/'SERVICE_METRICS.json',metrics)
        # Keep a post-boundary power sample before ending integration.
        time.sleep(.25);energy=power.energy(origin,finished);put(out/'ENERGY.json',energy)
        return dict(status='PASS_ACTUAL_NATIVE_SERVICE_PENDING_CROSS_ARM_AUDIT',arm=arm,
            native_correction_updates=len(selections),corrected_updates=sum(x['changed'] is True for x in selections),
            unchanged_updates=sum(x['changed'] is False for x in selections),compatible_boundaries=sum(x['compatible'] for x in reconciliations),
            compatible_ahead_boundaries=sum(x['compatible'] and x['ahead'] for x in reconciliations),
            metrics={k:v for k,v in metrics.items() if k!='frontier_rows'},energy=energy)
    finally:
        if consumer is not None and consumer.t.is_alive():consumer.close()
        for q in commands.values():q.put(None)
        for role,c in children.items():
            c.join(timeout=45)
            if c.is_alive():c.terminate();c.join(timeout=15)
            if c.is_alive():raise RuntimeError('owned native worker failed to stop')
        power.close()
        for l in (logs,events,canon,ingress):l.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--source-manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    source_gate=verify_source(a.source_manifest)
    c=json.loads(a.config.read_text());out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    if c['code_commit']!=source_gate['source_commit']:raise ValueError('frozen config source commit mismatch')
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True).strip()
    if apps:raise ValueError('foreign GPU processes present; no worker launched')
    env=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('torch','transformers','numpy','peft','soundfile','torchaudio')},
        hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total','--format=csv,noheader'],text=True),
        frozen_backend=c['settings']['backend'],model_data_inventory=c['settings'].get('asset_manifest'))
    put(out/'CONFIG.json',c);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=c['experiment_id'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),code_commit=c['code_commit'],source_gate=source_gate,
        frozen_config_sha256=hashlib.sha256(a.config.read_bytes()).hexdigest(),environment_sha256=hashlib.sha256((out/'ENVIRONMENT.json').read_bytes()).hexdigest(),
        raw_result=str(out/'native_jobs.jsonl'),summary=str(out/'SUMMARY.json'),gate=str(out/'GATE.json')))
    try:s=serve(c['settings'],c['arm'],out);put(out/'SUMMARY.json',s);put(out/'GATE.json',dict(status=s['status']));return 0
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());put(out/'GATE.json',dict(status='FAIL_NATIVE_SERVICE_PRESERVED'));return 1
if __name__=='__main__':raise SystemExit(main())
