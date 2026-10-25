"""Bounded-artifact verification and separate event-to-metric recomputation.

No model inference, oracle output substitution or re-execution of queues.
Derived outputs are separate from the immutable remote collection.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,gzip,hashlib,json,math,statistics,tarfile


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def read(p):
    if p.suffix=='.gz':
        with gzip.open(p,'rt',encoding='utf8') as f:return json.load(f)
    return json.loads(p.read_text(encoding='utf8'))


def lines(p):
    op=gzip.open if p.suffix=='.gz' else open
    with op(p,'rt',encoding='utf8') as f:return [json.loads(s) for s in f if s.strip()]


def csvrows(p):
    with p.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    for r in rows:
        for k,v in r.items():
            if v=='':r[k]=None
            elif v in ['True','False']:r[k]=v=='True'
            else:
                try:r[k]=float(v)
                except (ValueError,TypeError):pass
    return rows


def quantile(xs,q):
    assert xs and all(x is not None and math.isfinite(x) for x in xs)
    s=sorted(xs);p=(len(s)-1)*q;i=int(p)
    return s[i] if i==len(s)-1 else s[i]+(p-i)*(s[i+1]-s[i])


def close(a,b):assert math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-8),(a,b)


def savecsv(p,rows):
    with p.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def extract(stage):
    ix=read(stage/'BOUNDED_INDEX.json');archive=stage/'bounded_evidence_v1.tar.gz'
    assert archive.stat().st_size==ix['bytes'] and sha(archive)==ix['sha256']
    target=stage/'collected';assert not target.exists();target.mkdir()
    with tarfile.open(archive,'r:gz') as tf:
        for member in tf.getmembers():
            dest=(target/member.name).resolve()
            assert dest.is_relative_to(target.resolve()) and member.isfile()
        tf.extractall(target,filter='data')
    verify_manifest(target)
    print(json.dumps({'archive_verified':True,'files':ix['files'],'target':str(target)}))


def verify_manifest(root):
    manifest=read(root/'MANIFEST.json')
    for x in manifest['files']:
        p=root/x['path'];assert p.is_file() and p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],x['path']
    assert sha(root/'RAW_INDEX.json')==manifest['raw_index_sha256']
    listed={x['path'] for x in manifest['files']}|{'MANIFEST.json'}
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual==listed
    return manifest


def review(stage):
    root=stage/'collected';manifest=verify_manifest(root)
    out=stage/'local_review';assert not out.exists();out.mkdir()
    summary=read(root/'SUMMARY.json');assert summary['online_cells']==48 and summary['GPU_queue_closed']
    rows=csvrows(root/'pilot_v1_audit_corrected/SERVICE_CELLS.csv')
    fronts=csvrows(root/'pilot_v1_audit_corrected/COMMON_FRONTIERS.csv')
    quality=csvrows(root/'pilot_v1_audit_corrected/SOURCE_QUALITY.csv')
    costs=csvrows(root/'pilot_v1_audit_corrected/PHYSICAL_COSTS.csv')
    original=root/'pilot_v1_audit';corrected=root/'pilot_v1_audit_corrected'
    for n in ['SERVICE_CELLS.csv','COMMON_FRONTIERS.csv','SOURCE_QUALITY.csv','PHYSICAL_COSTS.csv']:
        assert sha(original/n)==sha(corrected/n)
    assert len(rows)==48 and len({r['cell'] for r in rows})==48
    expected=set(summary['completed_online']);assert {r['cell'] for r in rows}==expected
    assert sum(c['physical_model_calls'] for c in costs)==read(corrected/'SUMMARY.json')['actual_model_calls']
    audits=[];decision_rows=[];deferrals=[];headrooms=[];critical=[];coverage=[]
    for r in rows:
        cell=r['cell'];key='pilot_v1-'+cell
        cfg=read(root/'cell_metadata'/(key+'-config.json.gz'))
        specs=read(root/'cell_metadata'/(key+'-sessions.json.gz'))
        result=read(root/'cell_metadata'/(key+'-result.json.gz'))
        es=lines(root/'traces'/(key+'-events.jsonl.gz'))
        vs=lines(root/'traces'/(key+'-consumer.jsonl.gz'))
        ac=lines(root/'traces'/(key+'-worker_batch_accounting.jsonl.gz'))
        commits=[e for e in es if e['kind']=='commit']
        fs=[q for q in fronts if q['cell']==cell]
        qs=[q for q in quality if q['cell']==cell]
        assert cfg['rho']==1 and cfg['fine_seconds']==2
        assert len(specs)==16 and len({s['source_id'] for s in specs})==16
        wall=max(result['wall_seconds_including_arrival_and_drain'],max(v['observed'] for v in vs))
        close(wall,r['wall_seconds']);close(sum(s['duration'] for s in specs),r['audio_seconds'])
        recalculated=[]
        for s in specs:
            sv=[v for v in vs if v['session_id']==s['session_id']]
            total=round(s['duration']*16000);before=0
            for f in list(range(32000,total,32000))+[total]:
                release=s['offset']+f/16000
                dd=min(v['observed'] for v in sv if v['valid_visible_frontier']>=f)-release
                cc=min(c['installed'] for c in commits if c['session_id']==s['session_id'] and c['audio_end_sample']>=f)-release
                cv=min(v['observed'] for v in sv if v['certified_frontier']>=f)-release
                q=next(q for q in fs if q['source_id']==s['source_id'] and q['frontier_sample']==f)
                close(dd,q['display']);close(cc,q['commit']);close(cv,q['certified_consumer'])
                close((f-before)/16000,q['audio_seconds']);before=f
                recalculated.append((q,dd,cc,cv))
        assert len(recalculated)==len(fs)==len(commits)
        good=sum(q['audio_seconds'] for q,d,c,v in recalculated if d<=2 and c<=8)
        close(good/wall,r['Audio_Goodput_2_8'])
        close(sum(q['audio_seconds'] for q,d,c,v in recalculated if d<=2 and v<=8)/wall,r['Audio_Goodput_certified_consumer_2_8'])
        for metric,index in [('display',1),('commit',2)]:
            for name,p in [('P50',.5),('P95',.95),('P99',.99)]:
                close(quantile([v[index] for v in recalculated],p),r[metric+'_'+name])
        stable_good=0.;withdrawals=0
        for s in specs:
            sv=sorted((v for v in vs if v['session_id']==s['session_id']),key=lambda v:v['observed'])
            total=round(s['duration']*16000);before=0
            for f in list(range(32000,total,32000))+[total]:
                release=s['offset']+f/16000
                cert=next(v['observed'] for v in sv if v['certified_frontier']>=f)
                start=None;seen=False;lost=False
                for v in sv:
                    if v['observed']>cert:break
                    if v['valid_visible_frontier']>=f:
                        if start is None:start=v['observed']
                        seen=True
                    else:
                        if seen:lost=True
                        start=None
                assert start is not None
                if start-release<=2 and cert-release<=8:stable_good+=(f-before)/16000
                withdrawals+=lost;before=f
        close(stable_good/wall,r['Audio_Goodput_stable_2_8']);close(withdrawals,r['withdrawn_before_certified_frontiers'])
        t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
        samples=read(root/'cell_metadata'/(key+'-power_samples.json.gz'))['samples'];energy=0.
        for gpu in [0,1]:
            ps=sorted((p for p in samples if p['gpu']==gpu),key=lambda p:p['t'])
            for a,b in zip(ps,ps[1:]):
                left=max(t0,a['t']);right=min(t0+wall,b['t'])
                if right<=left:continue
                mid=(left+right)/2
                power=a['power_w']+(b['power_w']-a['power_w'])*(mid-a['t'])/(b['t']-a['t'])
                energy+=power*(right-left)
        close(energy/r['audio_seconds'],r['GPU_J_audio_s'])
        close(sum(q['WER_errors'] for q in qs)/sum(q['reference_words'] for q in qs),r['WER'])
        close(sum(q['CER_errors'] for q in qs)/sum(q['reference_characters'] for q in qs),r['CER'])
        last_release=max(s['offset']+s['duration'] for s in specs)
        headrooms.append({'cell':cell,'method':r['method'],'last_audio_release_s':last_release,
            'audio_seconds':r['audio_seconds'],'actual_full_run_wall_s':wall,'actual_good_audio_s':good,
            'actual_goodput':good/wall,'arrival_only_goodput_upper_bound':r['audio_seconds']/last_release,
            'max_relative_goodput_headroom':(r['audio_seconds']/last_release)/(good/wall)-1,
            'actual_all_audio_throughput':r['audio_seconds']/wall,
            'max_relative_throughput_headroom':wall/last_release-1,
            'scope':'Mathematical arrival-only upper bound, ignores all finite compute; not an achievable oracle or measured speedup'})
        close(sum(e['kind']=='wal-physical-timing' and e['phase']=='fsync' for e in es),r['physical_fsyncs'])
        for role in ['proposal','authority']:
            aa=[a for a in ac if a['worker'].startswith(role)]
            # Worker labels are checked explicitly against immutable jobs below.
            jobs=lines(root/'canonical_witnesses'/(key+'.jsonl.gz')) if role=='authority' else []
            if role=='authority':
                ids={j['job']['job_id'] for j in jobs}
                aa=[a for a in ac if set(a['job_ids'])&ids]
                assert sum(len(a['job_ids']) for a in aa)==len(jobs)==len(commits)
                actual_calls=sum(len(a['phases']) for a in aa)
                c=next(c for c in costs if c['cell']==cell and c['role']==role)
                close(actual_calls,c['physical_model_calls']);close(len(aa),c['physical_batches'])
        decisions=[e for e in es if e['kind']=='ces-decision' and e['operation'] is not None]
        feature_observations=sum(len(e['features']) for e in decisions)
        coverage.append({'cell':cell,'method':r['method'],'target_feature_observations':feature_observations,
            'released_successor_opportunity_coverage':'OBSERVED_AT_RECORDED_DECISIONS' if feature_observations else 'NOT_OBSERVED_NO_FEATURE_TELEMETRY',
            'zero_observations_are_not_zero_real_opportunities':True})
        v5=[e for e in decisions if 'common_cut_sids' in e]
        for e in v5:
            assert all(e['observed_perf']>=f['ready'] for f in e['features'])
            assert len(set(s for p in e['plan'] for s in p['sids']))==len(e['common_cut_sids'])
            assert set(s for p in e['plan'] for s in p['sids'])==set(e['common_cut_sids'])
            decision_rows.append({'cell':cell,'method':r['method'],'operation':e['operation'],
                'current_cut':len(e['common_cut_sids']),'first_rows':len(e['sids']),
                'batches_in_plan':len(e['plan']),'same_operation_split':len(e['plan'])>1 and len({p['operation'] for p in e['plan']})==1,
                'planner_wall_s':e['planner_wall_seconds'],'zero_residual_credit':e['zero_residual_credit'],
                'display_met_targets':e['actual_display_met_targets'],'expired_targets':e['display_expired_targets'],
                'expected_credit_audio':e['expected_credit_audio'],'expected_cut_wall_s':e['expected_cut_wall_seconds']})
        authority_jobs={j['job']['job_id']:j['job'] for j in jobs}
        authority_leases=[(min(authority_jobs[jid]['enqueue_perf'] for jid in a['job_ids']),a['batch_drained_perf'])
            for a in ac if set(a['job_ids'])&set(authority_jobs)]
        for j in jobs:
            job=j['job'];sid=job['session_id'];q=job['end_window']
            enq=next(e for e in es if e['kind']=='enqueue' and e['job_id']==job['job_id'])
            got=next(e for e in es if e['kind']=='executor-complete' and e['job_id']==job['job_id'])
            commit=next(c for c in commits if c['job_id']==job['job_id'])
            batch=next(a for a in ac if job['job_id'] in a['job_ids'])
            rr=j['selected']['_row_receipt']
            stamps=[job['audio_ready_perf'],enq['eligible_perf'],job['enqueue_perf'],batch['worker_started_perf'],
                rr['terminal_perf'],rr['rendered_perf'],rr['emitted_perf'],t0+got['received'],t0+commit['installed']]
            assert all(a<=b+1e-6 for a,b in zip(stamps,stamps[1:])),(cell,job['job_id'],stamps)
            segments=['release_to_parent_eligible_s','eligible_to_enqueue_s','enqueue_to_worker_start_s',
                'worker_start_to_complete_row_s','row_to_trusted_render_s','render_to_emit_s','emit_to_owner_receive_s','owner_receive_to_install_s']
            cc={k:b-a for k,a,b in zip(segments,stamps,stamps[1:])}
            close(sum(cc.values()),commit['installed']-(job['audio_ready_perf']-t0))
            occupied=sum(max(0.,min(stamps[2],end)-max(stamps[1],start)) for start,end in authority_leases)
            assert cc['eligible_to_enqueue_s']-occupied>=-1e-6
            critical.append({'cell':cell,'method':r['method'],'job_id':job['job_id'],'session':sid,'window':q,
                'parent':job['parent'],'operation':job['ces_operation'],**cc,
                'eligible_queue_overlap_other_authority_lease_s':occupied,
                'eligible_queue_nonlease_host_and_scheduler_s':cc['eligible_to_enqueue_s']-occupied,
                'commit_latency_s':sum(cc.values()),'commit_8s_missed':sum(cc.values())>8,
                'worker_lease_s_not_additive_to_row_path':batch['batch_drained_perf']-batch['worker_started_perf']})
            seen=[e for e in v5 if any(f['sid']==sid and f['window']==q for f in e['features']) and e['observed_perf']<=job['enqueue_perf']]
            if not seen:continue
            deferrals.append({'cell':cell,'method':r['method'],'session':sid,'window':q,'job_id':job['job_id'],
                'eligible_decision_observations':len(seen),
                'first_batch_deferrals':sum(sid not in e['sids'] for e in seen),
                'first_observed_to_enqueue_s':job['enqueue_perf']-seen[0]['observed_perf'],
                'actual_commit_latency_s':commit['installed']-(job['audio_ready_perf']-t0),
                'already_displayed_at_first_observation':next(f['display_met'] for f in seen[0]['features'] if f['sid']==sid and f['window']==q),
                'scope':'actual observed deferrals; not the unobserved earliest eligibility or a counterfactual speedup'})
        audits.append({'cell':cell,'event_frontiers_recomputed':len(fs),'audio_seconds':r['audio_seconds'],
            'good_audio_s':good,'complete_canonical_admissions':len(commits),'status':'PASS'})
    groups=defaultdict(list)
    for r in rows:groups[r['cell'].split('-')[1],r['method']].append(r)
    grouped=[]
    metrics=['Audio_Goodput_2_8','Audio_Goodput_stable_2_8','display_P99','commit_P99','GPU_J_audio_s','WER','CER',
        'verified_rows','rejected_rows','fallback_physical_calls','planner_wall_s','physical_fsyncs','capped_authority_admissions',
        'withdrawn_before_certified_frontiers','obsolete_private_jobs','direct_consumed_F2_jobs','wall_seconds']
    for (arrival,method),rr in sorted(groups.items()):
        assert len(rr)==3
        grouped.append({'arrival':arrival,'method':method,'runs':3,
            **{k:statistics.median(x[k] for x in rr) for k in metrics},
            'dual_P99_passes':sum(x['dual_P99_2_8_pass'] for x in rr)})
    contrasts=[]
    for arrival in ['sync','staggered']:
        for treatment in ['risk_cost','progress','progress_joint']:
            for baseline in ['fine','standard','cost','risk_cost']:
                if baseline==treatment:continue
                b={int(x['cell'].rsplit('-r',1)[1]):x for x in groups[arrival,baseline]}
                t={int(x['cell'].rsplit('-r',1)[1]):x for x in groups[arrival,treatment]}
                for metric in ['Audio_Goodput_2_8','GPU_J_audio_s','display_P99','commit_P99','Audio_Goodput_stable_2_8']:
                    changes=[t[i][metric]/b[i][metric]-1 for i in range(3)]
                    contrasts.append({'arrival':arrival,'treatment':treatment,'baseline':baseline,'metric':metric,
                        'r0':changes[0],'r1':changes[1],'r2':changes[2],'paired_median':statistics.median(changes),
                        'all_positive':all(x>0 for x in changes),'all_negative':all(x<0 for x in changes)})
    savecsv(out/'GROUPS.csv',grouped);savecsv(out/'PAIRED_EFFECTS.csv',contrasts)
    savecsv(out/'EVENT_RECOMPUTATION.csv',audits);savecsv(out/'V5_DECISION_BEHAVIOR.csv',decision_rows)
    savecsv(out/'TARGET_DEFERRALS.csv',deferrals)
    savecsv(out/'ARRIVAL_HEADROOM_BOUNDS.csv',headrooms)
    savecsv(out/'AUTHORITY_CRITICAL_PATHS.csv',critical)
    savecsv(out/'OPPORTUNITY_COVERAGE.csv',coverage)
    report={'status':'PASS_SEPARATE_LOCAL_EVENT_AND_DENOMINATOR_RECOMPUTATION','online_cells':48,
        'frontier_observations':len(fronts),'unique_sources':16,'same_source_repeat_not_IID_frontiers':True,
        'bounded_file_hashes_verified':len(manifest['files']),'actual_calls_in_corrected_audit':sum(c['physical_model_calls'] for c in costs),
        'GPU_calls_in_local_audit':0,'metrics_CSVs_byte_identical_after_metadata_fix':True,
        'full_input_tensor_replay_and_trusted_render_audit':'Remote independent CPU audit; not re-executed by this local trace audit',
        'no_unchosen_GPU_counterfactual_inference':True,'script_sha256':sha(Path(__file__))}
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('operation',choices=['extract','review']);ap.add_argument('--stage',type=Path,default=Path(__file__).resolve().parent)
    a=ap.parse_args();(extract if a.operation=='extract' else review)(a.stage)
