"""Independent local event/quality/energy recomputation; never invokes models."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,gzip,hashlib,json,math,re,statistics,unicodedata

def read(p):
    with (gzip.open(p,'rt',encoding='utf8') if p.suffix=='.gz' else p.open(encoding='utf8')) as f:return json.load(f)
def lines(p):
    with gzip.open(p,'rt',encoding='utf8') as f:return [json.loads(x) for x in f if x.strip()]
def table(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-8),(a,b)
def qtile(xs,p):
    a=sorted(xs);z=(len(a)-1)*p;i=int(z)
    return a[i] if i==len(a)-1 else a[i]+(z-i)*(a[i+1]-a[i])
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def edit(a,b):
    # Independent column-wise dynamic program, not imported from remote auditor.
    col=list(range(len(a)+1))
    for j,y in enumerate(b,1):
        nxt=[j]+[0]*len(a)
        for i,x in enumerate(a,1):nxt[i]=min(col[i]+1,nxt[i-1]+1,col[i-1]+int(x!=y))
        col=nxt
    return col[-1]
def quality(ref,hyp):
    r=unicodedata.normalize('NFKC',ref).lower();h=unicodedata.normalize('NFKC',hyp).lower()
    rw,hw=re.findall(r"[a-z0-9']+",r),re.findall(r"[a-z0-9']+",h)
    rc,hc=[x for x in r if x.isalnum()],[x for x in h if x.isalnum()]
    return edit(rw,hw),len(rw),edit(rc,hc),len(rc)
def savecsv(p,rows):
    with p.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();R=a.root;A=a.output;assert not A.exists();A.mkdir(parents=True)
    summary=read(R/'formal_SUMMARY.json');assert summary['performance_cells']==72 and summary['GPU_queue_closed']
    gate=read(R/'formal_audit/SUMMARY.json');assert gate['cells']==72 and not gate['failures']
    refs={s['source_id']:s['reference'] for s in read(R/'source_reference_manifest.json')['sessions']}
    cells=table(R/'formal_audit/SERVICE_CELLS.csv');fronts=table(R/'formal_audit/COMMON_FRONTIERS.csv')
    qs=table(R/'formal_audit/SOURCE_QUALITY.csv');costs=table(R/'formal_audit/PHYSICAL_COSTS.csv')
    assert len(cells)==72 and {c['cell'] for c in cells}==set(summary['completed_performance'])
    checks=[];paths=[];qualities=[];groups=defaultdict(list);allfronts=0
    for c in cells:
        name=c['cell'];M=R/'cell_metadata'/'formal'/name;T=R/'traces'/'formal'/name
        es=lines(T/'events.jsonl.gz');vs=lines(T/'consumer.jsonl.gz')
        ac=lines(T/'worker_batch_accounting.jsonl.gz')
        cfg=read(M/'config.json.gz');specs=read(M/'sessions.json.gz');result=read(M/'result.json.gz')
        assert cfg['rho']==1 and cfg['fine_seconds']==2 and len(specs)==16
        commits=[e for e in es if e['kind']=='commit'];t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
        wall=max(result['wall_seconds_including_arrival_and_drain'],max(v['observed'] for v in vs));close(wall,c['wall_seconds'])
        fs={(f['source_id'],int(float(f['frontier_sample']))):f for f in fronts if f['cell']==name}
        qlookup={q['source_id']:q for q in qs if q['cell']==name}
        good=certgood=stablegood=0.;withdrawn=0;dl=[];cl=[];qsum=[0,0,0,0];nf=0
        for s in specs:
            total=round(s['duration']*16000);before=0
            sv=sorted([v for v in vs if v['session_id']==s['session_id']],key=lambda v:v['observed'])
            cs=[e for e in commits if e['session_id']==s['session_id']]
            assert max(e['audio_end_sample'] for e in cs)==total
            for frontier in list(range(32000,total,32000))+[total]:
                release=s['offset']+frontier/16000;weight=(frontier-before)/16000;before=frontier
                d=min(v['observed'] for v in sv if v['valid_visible_frontier']>=frontier)-release
                co=min(e['installed'] for e in cs if e['audio_end_sample']>=frontier)-release
                cert=min(v['observed'] for v in sv if v['certified_frontier']>=frontier)
                f=fs[s['source_id'],frontier]
                for x,k in [(d,'display'),(co,'commit'),(cert-release,'certified_consumer'),(weight,'audio_seconds')]:close(x,f[k])
                good+=weight*(d<=2 and co<=8);certgood+=weight*(d<=2 and cert-release<=8)
                start=None;seen=False;lost=False
                for v in sv:
                    if v['observed']>cert:break
                    if v['valid_visible_frontier']>=frontier:
                        if start is None:start=v['observed']
                        seen=True
                    else:
                        lost|=seen;start=None
                assert start is not None
                stablegood+=weight*(start-release<=2 and cert-release<=8);withdrawn+=lost
                dl.append(d);cl.append(co);nf+=1
            text=max((v for v in sv if v['certified_frontier']==total),key=lambda v:v['canonical_version'])['certified_text']
            counts=quality(refs[s['source_id']],text)
            for n,(key,value) in enumerate(zip(['WER_errors','reference_words','CER_errors','reference_characters'],counts)):
                close(value,qlookup[s['source_id']][key]);qsum[n]+=value
            qualities.append({'cell':name,'source_id':s['source_id'],'WER_errors':counts[0],'reference_words':counts[1],
                              'CER_errors':counts[2],'reference_characters':counts[3]})
        assert nf==len(fs)==len(commits);allfronts+=nf
        for x,k in [(good/wall,'Audio_Goodput_2_8'),(certgood/wall,'Audio_Goodput_certified_consumer_2_8'),
                    (stablegood/wall,'Audio_Goodput_stable_2_8'),(withdrawn,'withdrawn_before_certified_frontiers'),
                    (qsum[0]/qsum[1],'WER'),(qsum[2]/qsum[3],'CER')]:close(x,c[k])
        for xs,kind in [(dl,'display'),(cl,'commit')]:
            for p,label in [(.5,'P50'),(.95,'P95'),(.99,'P99')]:close(qtile(xs,p),c[kind+'_'+label])
        samples=read(M/'power_samples.json.gz')['samples'];energy=0.
        for gpu in [0,1]:
            ps=sorted((p for p in samples if p['gpu']==gpu),key=lambda p:p['t'])
            for left,right in zip(ps,ps[1:]):
                lo=max(t0,left['t']);hi=min(t0+wall,right['t'])
                if hi<=lo:continue
                mid=(lo+hi)/2;power=left['power_w']+(right['power_w']-left['power_w'])*(mid-left['t'])/(right['t']-left['t'])
                energy+=(hi-lo)*power
        close(energy/sum(s['duration'] for s in specs),c['GPU_J_audio_s'])
        close(sum(e['kind']=='wal-physical-timing' and e['phase']=='fsync' for e in es),c['physical_fsyncs'])
        calls=sum(len(x['phases']) for x in ac);close(calls,sum(float(p['physical_model_calls']) for p in costs if p['cell']==name))
        # Exact row path; concurrent lease overlap is not added to it a second time.
        jobs=lines(R/'canonical_witnesses'/'formal'/(name+'.jsonl.gz'))
        byjob={j['job']['job_id']:j['job'] for j in jobs};enqs={e['job_id']:e for e in es if e['kind']=='enqueue'}
        got={e['job_id']:e for e in es if e['kind']=='executor-complete'};cby={e['job_id']:e for e in commits}
        batches={j:x for x in ac for j in x['job_ids']}
        leases=[(min(byjob[j]['enqueue_perf'] for j in x['job_ids']),x['batch_drained_perf']) for x in ac if set(x['job_ids'])&set(byjob)]
        for rec in jobs:
            j=rec['job'];jid=j['job_id']
            if jid not in cby:
                assert not rec['was_canonically_committed']
                continue  # Still included in physical call/energy accounting, not an installed row path.
            rr=rec['selected_result']['_row_receipt'];batch=batches[jid]
            stamps=[j['audio_ready_perf'],enqs[jid]['eligible_perf'],j['enqueue_perf'],batch['worker_started_perf'],
                    rr['terminal_perf'],rr['rendered_perf'],rr['emitted_perf'],t0+got[jid]['received'],t0+cby[jid]['installed']]
            assert all(x<=y+1e-6 for x,y in zip(stamps,stamps[1:])),(name,jid,stamps)
            overlap=sum(max(0.,min(stamps[2],end)-max(stamps[1],start)) for start,end in leases)
            assert overlap<=stamps[2]-stamps[1]+1e-6
            paths.append({'cell':name,'method':c['method'],'job_id':jid,'session':j['session_id'],'window':j['end_window'],
                'release_to_parent_ready_s':stamps[1]-stamps[0],'eligible_to_enqueue_s':stamps[2]-stamps[1],
                'queue_other_authority_lease_s':overlap,'queue_nonlease_host_scheduler_s':stamps[2]-stamps[1]-overlap,
                'enqueue_to_worker_s':stamps[3]-stamps[2],'worker_to_complete_row_s':stamps[4]-stamps[3],
                'row_render_emit_receive_install_s':stamps[-1]-stamps[4],'commit_latency_s':stamps[-1]-stamps[0],
                'missed_before_enqueue':stamps[2]-stamps[0]>8,'commit_8s_miss':stamps[-1]-stamps[0]>8,
                'scope':'observed disjoint row path; queue overlaps are a decomposition, not extra latency'})
        checks.append({'cell':name,'frontiers':nf,'status':'PASS','actual_model_calls':calls,'good_audio_s':good,'wall_s':wall})
        groups[name.split('-')[1],c['method']].append(c)
    assert sum(x['actual_model_calls'] for x in checks)==gate['actual_model_calls']
    savecsv(A/'EVENT_RECOMPUTATION.csv',checks);savecsv(A/'SOURCE_QUALITY_RECOMPUTED.csv',qualities);savecsv(A/'AUTHORITY_CRITICAL_PATHS.csv',paths)
    report={'status':'PASS_SEPARATE_LOCAL_EVENT_QUALITY_ENERGY_RECOMPUTATION','online_cells':72,'frontier_observations':allfronts,
        'unique_sources':16,'same_source_repeat_not_IID_frontiers':True,'actual_model_calls':sum(x['actual_model_calls'] for x in checks),
        'new_GPU_calls':0,'source_sha256':sha(Path(__file__)),'full_GPU_inputs_and_admission':'Remote v2 audit; no neural re-execution in this local check'}
    (A/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
