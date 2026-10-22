"""Explain actual legal-view decisions and overlapping deadline facts, CPU only."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,sys

def main():
    B=Path(sys.argv[1]);P=B/'projects/revtrace_row_completion_20261023';O=B/'results/revtrace/row_completion_20261023'
    OLD=B/'results/revtrace/online_admission_20261022';S=P/'source_row_sdk_v2';sys.path[:0]=[str(S/'src'),str(B/'projects/revtrace_online_admission_20261022')]
    from revtrace.certified_display import ContinuityView
    from analysis_core import quantile
    assert json.loads((O/'POST_ROW_CPU_SUMMARY_v1.json').read_text())['status']=='COMPLETE_CPU_RESTAGING_TIMING_STATISTICS_AND_RAW_INDEX'
    D=O/'private_blocker_audit_v1';D.mkdir(exist_ok=False)
    oldindex={r['path']:r for r in json.loads((OLD/'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())['files']}
    def read(p,old=False,lines=False):
        raw=p.read_bytes()
        if old:
            r=oldindex[p.relative_to(OLD).as_posix()];assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
        return [json.loads(x) for x in raw.splitlines()] if lines else json.loads(raw)
    def csvsave(n,rs):
        with (D/n).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    class DecisionTrace(ContinuityView):
        def __init__(self,*a,**kw):super().__init__(*a,**kw);self.checks=[];self.current=None
        def _compatible(self,s,node,Psha):
            ok=super()._compatible(s,node,Psha)
            self.checks.append({'job_id':node['job_id'],'session_id':node['session_id'],'target':node['audio_end_sample'],
                'compatible':ok,'current_frontier':s['F'],'current_version':s['version'],
                'publication_kind':self.current['kind'],'publication_time':self.current.get('displayed',self.current['time'])})
            return ok
    facts=[];decisions=[];costs=[];counts=defaultdict(int)
    try:
        stages=[('old72_subset',OLD/'formal_v1',True),('core120',O/'formal_row_v1',False),('validation30',O/'validation_row_v1',False)]
        for label,root,old in stages:
            for C in sorted(root.iterdir()):
                if not C.is_dir() or not (C/'result.json').exists():continue
                cfg=read(C/'config.json',old);method=cfg['online_study']['method']
                if old and method not in ['fine','dgft','standard']:continue
                es=read(C/'events.jsonl',old,True);vs=read(C/'consumer.jsonl',old,True);rs=read(C/'worker_records.jsonl',old,True)
                ss=read(C/'sessions.json',old);result=read(C/'result.json',old);byid={r['job']['job_id']:r for r in rs}
                t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');delivery=cfg.get('result_delivery','batch')
                saved={(v['session_id'],v['source_kind'],v['server_time']):v for v in vs};view=DecisionTrace(cfg['consumer_policy'],strict_bound=True)
                observed_checks=[];dropped=[]
                for e in es:
                    view.current=e;view.checks=[];key=(e.get('session_id'),e['kind'],e.get('displayed'))
                    actual=saved.get(key);replayed=view.consume(e,actual['consumer_received_perf'] if actual else t0+e['time'])
                    if replayed:
                        assert actual is not None
                        for k in ['canonical_version','certified_frontier','valid_visible_frontier','visible_text','tentative_invalidated','compatible_provisional_retained']:
                            assert replayed[k]==actual[k]
                    if e['kind']=='display' and not replayed:
                        dropped.append({'job_id':e['job_id'],'target':e['audio_end_sample'],'session_id':e['session_id'],
                            'server_time':e['displayed'],'reason':'stale_epoch_revision_or_already_covered_not_an_ExactP_test'})
                    for check in view.checks:
                        assert actual is not None
                        observed_checks.append({**check,'consumer_applied_s':actual['observed']})
                assert len(view.records)==len(vs)
                for check in observed_checks:decisions.append({'cohort':label,'cell':C.name,**check,'offline_semantic_replay_at_actual_consumer_event':True})
                physical=[]
                if delivery=='row':
                    ac=read(C/'worker_batch_accounting.jsonl',False,True)
                    for a in ac:
                        role=byid[a['job_ids'][0]]['job']['role']
                        physical.extend({'role':role,'start':p['started_perf']-t0,'end':p['completed_perf']-t0,'kind':'measured_model_phase_not_continuous_kernel_activity'} for p in a['phases'])
                else:
                    seen=set()
                    for r in rs:
                        j,z=r['job'],r['result'];key=(j['role'],z['started_perf'],z['completed_perf'])
                        if key in seen:continue
                        seen.add(key);phases=z.get('online_verification',{}).get('phases',[])
                        if not phases and z.get('model_started_perf') is not None:phases=[{'started_perf':z['model_started_perf'],'completed_perf':z['model_completed_perf']}]
                        physical.extend({'role':j['role'],'start':p['started_perf']-t0,'end':p['completed_perf']-t0,'kind':'measured_model_phase_unknown_individual_row_terminal'} for p in phases)
                for s in ss:
                    sid=s['session_id'];sv=[v for v in vs if v['session_id']==sid];total=round(s['duration']*16000)
                    for f in list(range(32000,total,32000))+[total]:
                        release=s['offset']+f/16000;deadline=release+2;first=min(v['observed'] for v in sv if v['valid_visible_frontier']>=f)
                        if first<=deadline:continue
                        incompatible=[c['job_id'] for c in observed_checks if c['session_id']==sid and c['target']>=f and
                          not c['compatible'] and c['consumer_applied_s']<=deadline and c['publication_kind']=='display']
                        rejected_stale=[c['job_id'] for c in dropped if c['session_id']==sid and c['target']>=f and c['server_time']<=deadline]
                        jobs=[r for r in rs if r['job']['session_id']==sid and r['job']['audio_end_sample']>=f and r['job']['audio_ready_perf']-t0<=deadline]
                        row_queued_before_owner_late=[];terminal_before_render_late=[]
                        for r in jobs:
                            j,z=r['job'],r['result'];m=z.get('_row_receipt')
                            if not m:continue
                            if m['emitted_perf']-t0<=deadline<z['received_perf']-t0:row_queued_before_owner_late.append(j['job_id'])
                            if m['terminal_perf']-t0<=deadline<m['rendered_perf']-t0:terminal_before_render_late.append(j['job_id'])
                        phases=[p for p in physical if p['start']<=deadline<p['end']]
                        facts.append({'cohort':label,'cell':C.name,'method':method,'delivery':delivery,'source_id':s['source_id'],'frontier':f,
                          'release_s':release,'deadline_s':deadline,'first_legal_display_s':first,
                          'actual_early_provisional_ExactP_rejection_jobs':json.dumps(sorted(set(incompatible))),
                          'stale_or_covered_publication_jobs_not_ExactP':json.dumps(sorted(set(rejected_stale))),
                          'row_queued_by_deadline_but_owner_received_later_jobs':json.dumps(sorted(row_queued_before_owner_late)),
                          'row_terminal_by_deadline_but_worker_Render_later_jobs':json.dumps(sorted(terminal_before_render_late)),
                          'audio_released_job_enqueued_after_deadline_count_parent_may_not_be_ready':sum(r['job']['enqueue_perf']-t0>deadline for r in jobs),
                          'enqueued_by_deadline_worker_start_late_count':sum(r['job']['enqueue_perf']-t0<=deadline<r['result']['started_perf']-t0 for r in jobs),
                          'authority_model_phase_spans_deadline':any(p['role']=='authority' for p in phases),
                          'proposer_model_phase_spans_deadline':any(p['role']=='proposal' for p in phases),
                          'individual_row_final_unknown_for_batch_return':delivery=='batch','dropped_publication_consumer_apply_clock_unknown':True,
                          'flags_overlap_and_are_not_unique_causal_shares':True})
                consumer=result['consumer']
                costs.append({'cohort':label,'cell':C.name,'actual_Consumer_thread_CPU_s':consumer['consumer_cpu_seconds'],
                  'actual_Consumer_queue_peak_depth':consumer['queue_max_depth'],
                  'Consumer_application_wall_P99_s':quantile([v['view_application_seconds'] for v in vs],.99),
                  'scope':'actual_local_FIFO_consumer_not_browser_network_or_host_energy'})
                counts[label]+=1;print('PRIVATE_DECISIONS',label,C.name,flush=True)
        assert dict(counts)=={'old72_subset':36,'core120':120,'validation30':30}
        csvsave('MISSED_FRONTIER_MULTILABEL_FACTS.csv',facts);csvsave('EXACT_COMPATIBILITY_DECISIONS.csv',decisions);csvsave('ACTUAL_CONSUMER_COSTS.csv',costs)
        out={'status':'PASS_ACTUAL_CONSUMER_COMPATIBILITY_REPLAY_AND_MULTILABEL_DEADLINE_FACTS','cells':dict(counts),
          'missed_display_frontiers':len(facts),'compatibility_tests':len(decisions),'overlapping_facts_not_additive_cause_percentages':True,
          'old_row_terminal_times_not_invented':True,'new_model_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
    except BaseException as e:
        (D/'STOP.json').write_text(json.dumps({'error':repr(e),'completed_cells':dict(counts),'new_model_calls':0,'raw_retained':True})+'\n');raise

if __name__=='__main__':main()
