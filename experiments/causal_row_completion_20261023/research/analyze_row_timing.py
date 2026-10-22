"""Post-serving actual clocks/costs/Rescue upper-bound screen; no model calls."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,re,sys
from row_timing_core import free_gaps,available_windows,union_duration

def main():
    B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023'
    sys.path.insert(0,str(B/'projects/revtrace_online_admission_20261022'))
    from analysis_core import quantile
    assert json.loads((O/'FORMAL_ROW_SUMMARY_v1.json').read_text())['status']=='COMPLETE_ALL150_INDEPENDENT_AUDITS_PASS'
    D=O/'row_timing_v1';D.mkdir(exist_ok=False)
    def read(p):return json.loads(p.read_text())
    def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
    def csvsave(n,rs):
        if not rs:(D/n).write_text('no_rows\n');return
        with (D/n).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    summaries=[];allmiss=[];screen=[];rowevents=[]
    for stage in ['formal_row_v1','validation_row_v1']:
        for C in sorted((O/stage).iterdir()):
            if not C.is_dir() or not (C/'result.json').exists():continue
            cfg=read(C/'config.json');result=read(C/'result.json');es=lines(C/'events.jsonl');vs=lines(C/'consumer.jsonl')
            rs=lines(C/'worker_records.jsonl');ss=read(C/'sessions.json');t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
            byid={r['job']['job_id']:r for r in rs};commits=[e for e in es if e['kind']=='commit'];cm={(e['session_id'],e['version']):e for e in commits}
            commit_job={e['job_id']:e for e in commits};pub={(e['session_id'],e['kind'],e['displayed']):e for e in es if e['kind'] in ['display','canonical-display']}
            rend={e['job_id']:e for e in es if e['kind']=='render-checked'};wals=defaultdict(dict)
            for e in es:
                if e['kind'] in ['wal-owner-start','wal-owner-complete']:
                    for jid in e['job_ids']:wals[jid][e['kind']]=e['time']
            delivery=cfg['result_delivery'];method=cfg['online_study']['method'];accounts={};bybatch={};physical=[]
            if delivery=='row':
                accounts={a['batch_id']:a for a in lines(C/'worker_batch_accounting.jsonl')}
                for bid,a in accounts.items():
                    physical.append({'enqueue':min(byid[j]['job']['enqueue_perf'] for j in a['job_ids'])-t0,
                      'drained':a['batch_drained_perf']-t0,'role':byid[a['job_ids'][0]]['job']['role'],'worker':a['worker']})
                    for jid in a['job_ids']:bybatch[jid]=a
            terminal_render=[];ipc=[];render_owner=[];install_before_drain=pass_before_fallback=private_before_drain=0
            for rec in rs:
                j,z=rec['job'],rec['result'];jid=j['job_id'];receipt=z.get('_row_receipt');a=bybatch.get(jid)
                if receipt:
                    terminal_render.append(receipt['rendered_perf']-receipt['terminal_perf']);ipc.append(z['received_perf']-receipt['emitted_perf'])
                    inst=commit_job.get(jid,{}).get('installed');drain=a['batch_drained_perf']-t0
                    if inst is not None and inst<drain:install_before_drain+=1
                    proof=z.get('online_verification',{});fallback=[p for p in a['phases'] if p['phase']=='fresh-FP32-fallback']
                    accepted=bool(proof and not proof['fallback_used'])
                    if accepted and fallback and inst is not None and inst+t0<fallback[-1]['completed_perf']:pass_before_fallback+=1
                    applicable=[v for v in vs if v['session_id']==j['session_id'] and v['source_kind']=='display' and
                      pub[v['session_id'],v['source_kind'],v['server_time']]['job_id']==jid and v['valid_visible_frontier']>=j['audio_end_sample']]
                    if applicable and min(v['observed'] for v in applicable)<drain:private_before_drain+=1
                    rowevents.append({'stage':stage,'cell':C.name,'role':j['role'],'job_id':jid,'batch_id':z['physical_batch_id'],
                      'terminal_s':receipt['terminal_perf']-t0,'worker_Render_complete_s':receipt['rendered_perf']-t0,
                      'message_emitted_s':receipt['emitted_perf']-t0,'owner_received_s':z['received_perf']-t0,
                      'physical_batch_drained_s':drain,'WAL_install_s':inst,'verified_success':accepted,
                      'IPC_clock_includes_queue_and_owner_polling':True})
                render_owner.append(rend[jid]['host_cpu_wall_seconds'])
            for s in ss:
                sid=s['session_id'];sv=[v for v in vs if v['session_id']==sid];total=round(s['duration']*16000)
                for f in list(range(32000,total,32000))+[total]:
                    release=s['offset']+f/16000;first=min((v for v in sv if v['valid_visible_frontier']>=f),key=lambda v:v['observed'])
                    if first['observed']-release<=2:continue
                    p=pub[sid,first['source_kind'],first['server_time']];r=byid[p['job_id']];j,z=r['job'],r['result'];birth=cm.get((sid,j['parent']))
                    a=bybatch.get(j['job_id']);receipt=z.get('_row_receipt');w=wals[j['job_id']]
                    predecessor=[x for x in rs if x['job']['session_id']==sid and x['job']['role']=='proposal' and
                      x['job']['end_window']==j['chunk_id'] and x['job'].get('branch_generation')==j.get('branch_generation') and
                      x['job']['parent']==j['parent'] and x['result']['state_tokens']==j['prompt_tokens']] if j['role']=='proposal' else []
                    candidate=byid.get(j.get('candidate_origin_job_id'));parent_ready=birth['installed'] if birth else 0.
                    if predecessor:parent_ready=max(parent_ready,max(x['result']['received_perf']-t0 for x in predecessor))
                    if candidate:parent_ready=max(parent_ready,candidate['result']['received_perf']-t0)
                    allmiss.append({'stage':stage,'cell':C.name,'method':method,'delivery':delivery,'source_id':s['source_id'],
                      'frontier_sample':f,'audio_release_s':release,'first_legal_display_s':first['observed'],'display_delay_s':first['observed']-release,
                      'first_view_kind':first['source_kind'],'job_id':j['job_id'],'role':j['role'],'required_parent_or_candidate_available_s':parent_ready,
                      'target_job_audio_ready_s':j['audio_ready_perf']-t0,'enqueue_s':j['enqueue_perf']-t0,'worker_started_s':z['started_perf']-t0,
                      'row_terminal_s':receipt['terminal_perf']-t0 if receipt else None,'row_emitted_s':receipt['emitted_perf']-t0 if receipt else None,
                      'physical_batch_complete_s':a['batch_result_complete_perf']-t0 if a else z['completed_perf']-t0,
                      'physical_batch_drained_s':a['batch_drained_perf']-t0 if a else None,'owner_received_s':z['received_perf']-t0,
                      'owner_Render_checked_upper_s':rend[j['job_id']]['time'],'WAL_owner_start_s':w.get('wal-owner-start'),
                      'WAL_owner_complete_s':w.get('wal-owner-complete'),'consumer_applied_s':first['observed'],
                      'birth_parent':j['parent'],'consumer_parent':first['canonical_version'],'overlapping_causes_not_summed':True})
            # Exact-P incompatibility is an observable state fact,not an F2 label.
            # Free worker lease windows are an optimistic opportunity upper bound,
            # not a claim of a re-executed or faster alternative schedule.
            if method=='dgft' and delivery=='row':
                authority=[p for p in physical if p['role']=='authority'];workers={p['worker'] for p in authority};assert len(workers)==1
                gaps=free_gaps(authority,result['wall_seconds_including_arrival_and_drain'])
                failures=[e for e in es if e['kind']=='private-continuity-proof' and not e['eligible'] and e['witness']=='boundary-projection-mismatch']
                sessions={s['session_id']:s for s in ss}
                for e in failures:
                    c=cm[e['session_id'],e['canonical_version']];s=sessions[e['session_id']];total=round(s['duration']*16000)
                    if c['audio_end_sample']>=total:continue
                    target=min(total,(c['audio_end_sample']//32000+1)*32000);release=s['offset']+target/16000;deadline=release+2
                    windows=available_windows(gaps,known=c['installed'],released=release,deadline=deadline)
                    actual=min(v['observed'] for v in vs if v['session_id']==s['session_id'] and v['valid_visible_frontier']>=target)
                    screen.append({'stage':stage,'cell':C.name,'source_id':s['source_id'],'session_id':s['session_id'],
                      'known_parent':c['version'],'parent_job_id':c['job_id'],'parent_prompt_sha256':hashlib.sha256(json.dumps(c['next_prompt_tokens'],separators=(',',':')).encode()).hexdigest(),
                      'parent_frontier':c['audio_end_sample'],'target_frontier':target,'known_parent_s':c['installed'],'target_audio_release_s':release,
                      'deadline_s':deadline,'actual_legal_display_delay_s':actual-release,'already_timely_under_existing_rebase':actual<=deadline,
                      'available_worker_lease_windows':json.dumps(windows,separators=(',',':')),'largest_observed_window_s':max((b-a for a,b in windows),default=0.),
                      'full_new_parent_GPU_cost_not_measured_by_this_screen':True,'not_a_free_rescue_or_feasible_algorithm_claim':True})
            def q99(v):return quantile(v,.99) if v else None
            eventsync=[e for e in es if e['kind']=='wal-physical-timing' and e['phase']=='fsync']
            cpu_text=(O/stage/(C.name+'.CPU_IO.txt')).read_text();cpu={}
            for name,pattern in [('process_user_CPU_s',r'User time \(seconds\):\s*([0-9.]+)'),('process_system_CPU_s',r'System time \(seconds\):\s*([0-9.]+)'),('process_peak_RSS_kib',r'Maximum resident set size \(kbytes\):\s*(\d+)')]:
                m=re.search(pattern,cpu_text);assert m;cpu[name]=float(m.group(1))
            power=read(C/'power_samples.json')['samples'];during=[p for p in power if t0<=p['t']<=t0+result['wall_seconds_including_arrival_and_drain']]
            summaries.append({'stage':stage,'cell':C.name,'method':method,'delivery':delivery,
              'row_receipts':sum('_row_receipt' in r['result'] for r in rs),'early_WAL_installs_before_physical_drain':install_before_drain,
              'verified_success_installs_before_peer_fallback_end':pass_before_fallback,'legal_private_applications_before_batch_drain':private_before_drain,
              'worker_terminal_to_Render_P99_s':q99(terminal_render),'emitted_to_owner_received_P99_s':q99(ipc),
              'owner_Render_host_wall_sum_s':sum(render_owner),'owner_Render_host_wall_P99_s':q99(render_owner),
              'physical_fsync_count':len(eventsync),'fsync_wall_union_s':union_duration([(e['started'],e['completed']) for e in eventsync]),
              'fsync_P99_s':q99([e['completed']-e['started'] for e in eventsync]),'GPU_memory_peak_mib_both_devices_max':max(p['memory_mib'] for p in during),
              **cpu,'process_CPU_includes_initialization_and_postwindow_logging':True,'clock_segments_not_additive_causal_fractions':True})
            print('TIMING',C.name,flush=True)
    assert len(summaries)==150
    csvsave('CLOCK_AND_COSTS.csv',summaries);csvsave('MISSED_DISPLAY_FRONTIERS.csv',allmiss);csvsave('ROW_DELIVERY_EVENTS.csv',rowevents);csvsave('RESCUE_OBSERVABLE_SCREEN.csv',screen)
    out={'status':'COMPLETE_ROW_CLOCK_COST_AND_OBSERVABLE_RESCUE_SCREEN','cells':150,'display_missed_frontiers':len(allmiss),
      'exact_P_conflict_next_frontier_opportunities':len(screen),'already_timely_existing_rebase':sum(s['already_timely_under_existing_rebase'] for s in screen),
      'late_with_positive_observed_worker_window':sum(not s['already_timely_under_existing_rebase'] and s['largest_observed_window_s']>0 for s in screen),
      'new_model_calls':0,'screen_is_not_a_GPU_cost_measurement':True,'no_independent_extra_coordination_rule_tested':True,
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (D/'SUMMARY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out))

if __name__=='__main__':main()
