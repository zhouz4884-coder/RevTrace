"""Constructed CPU histories only: no actual serving/GPU conclusions."""
from pathlib import Path
import dataclasses,json,sys,tempfile,unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'/'src'))
import profile_closed_snapshots as p
from revtrace.ces_closed_loop import ClosedLoopState,PlannerConfig,Identity,TargetContext,choose_closed_loop
from revtrace.ces_v5_policy import V5Target
from revtrace.dgft import digest_tokens

def save(path,v,ls=False):
    path.write_text(('\n'.join(json.dumps(x) for x in v) if ls else json.dumps(v))+'\n',encoding='utf8')

def fixture(root):
    C=root/'CPU-FIXTURE-NOT-GPU';C.mkdir();t0=100.
    cal={'global_reject':0.,'causal_reject':{},'cost_seconds':{op:{'1':v,'2':3*v,'16':10*v}
        for op,v in [('generate',.4),('verify',.1),('fallback',.4)]},
        'v5_risk_model':{'min_bucket_samples':1,'owner_delivery_seconds':.08,
        'generation_scenarios':{'global':[{'weight':1.,'lease_ratio':1.,'row_fraction':1.}]},
        'verification_scenarios':{'global':[{'weight':1.,'original_rows':1,'failed_count':0,'verify_ratio':1.,'verify_row_fraction':1.}]}}}
    cfg={'rho':1,'fine_seconds':2,'microbatch':1,'ces_study':{'method':'causal','calibration':cal,
        'display_slo':2.,'commit_slo':8.,'closed_loop_config':dataclasses.asdict(PlannerConfig())}}
    cd=p.fingerprint(cfg);book=ClosedLoopState(scope=(t0,cd));remaining=set(range(3));events=[{'kind':'run-start','t0_perf':t0}];records=[]
    initials=[{'session_id':s,'state':{'checkpoint_id':0,'audio_frontier_window':0,'contract_epoch':1,'prompt_tokens':[]}} for s in remaining]
    for i in range(3):
        now=102.1+i*.1
        ts=[V5Target(sid=s,window=1,ready=102.,deadline=110.,candidate_ready=False,same_birth=False,
            previous_reject=False,candidate_tokens=0,descendant_count=0,descendant_seconds=0.,candidate_eta=None,
            audio_seconds=2.,interval_seconds=2.) for s in sorted(remaining)]
        contexts={s:TargetContext(Identity(s,1,0,digest_tokens([]),0,32000,cd)) for s in remaining}
        book.observe(contexts,now)
        obs={'kind':'closed-loop-observation','prediction_not_authorization':True,'observed_perf':now,
            'elapsed_seconds':now-t0,'observed_credit_audio':2.*i,'service_book':book.to_audit(),
            'contexts':{str(s):{'identity':dataclasses.asdict(c.identity),'released_successors':[],
                'target_context':dataclasses.asdict(c)} for s,c in contexts.items()}}
        out=choose_closed_loop(ts,contexts,now=now,mode='causal',cal=cal,limit=1,observed_credit_audio=2.*i,
            elapsed_seconds=now-t0,state=book,display_slo=2.,config=PlannerConfig())
        assert len(out['sids'])==1
        event=dict(out,kind='ces-decision',observed_perf=now,features=[dataclasses.asdict(t) for t in ts],
            planner_wall_seconds=[.03,.01,.02][i],feature_wall_seconds=.001)
        events.extend([obs,event]);sid=out['sids'][0];jid=f'CPU-a{i}'
        j={'job_id':jid,'session_id':sid,'end_window':1,'ces_operation':out['operation'],'parent':0,
            'contract_epoch':1,'parent_prompt_digest':digest_tokens([]),'contract_digest':cd,
            'audio_start_sample':0,'audio_end_sample':32000,'audio_ready_perf':102.,'enqueue_perf':now+.01}
        records.append({'job':j})
        receipt=book.record_dispatch(out,contexts,now=now+.01)
        events.extend([dict(receipt,kind='closed-loop-service-dispatch',actual_dispatch_perf=now+.01,decision_token=out['decision_token']),
            {'kind':'batch-dispatched','role':'authority','job_ids':[jid]},
            {'kind':'ces-consumer-ack','session_id':sid,'valid_visible_frontier':32000,'observed_perf':now+.04},
            {'kind':'commit','job_id':jid,'session_id':sid,'version':1,'audio_end_sample':32000,
             'audio_start_sample':0,'next_prompt_tokens':[sid+1],'installed':now+.05-t0,'audio_ready':2.}])
        retired=book.admitted(sid,epoch=1,frontier=32000,now=now+.05)
        events.append({'kind':'closed-loop-service-retired','session_id':sid,'installed_perf':now+.05,
            'actual_durable_install_observed':True,'retired':retired,'service_book':book.to_audit()})
        remaining.remove(sid)
    save(C/'config.json',cfg);save(C/'events.jsonl',events,True);save(C/'worker_records.jsonl',records,True)
    save(C/'initial_states.json',initials);save(C/'sessions.json',[{'session_id':s,'duration':2.} for s in range(3)])
    save(C/'result.json',{'fine_window_accounting_complete':True,'decision':'PASS_PROTOCOL_COMPLETENESS'})
    return C

class SnapshotTests(unittest.TestCase):
    def test_largest_measured_wall_not_best_performance_selection(self):
        events=[{'kind':'other'}]+[{'kind':'ces-decision','planner_wall_seconds':v} for v in [3,1,2,3]]
        self.assertEqual(p.select_indices(events,2),{1,4})
        with self.assertRaises(AssertionError):p.select_indices(events,6)

    def test_selected_exact_replay_skips_middle_but_rebuilds_all_actual_debt(self):
        with tempfile.TemporaryDirectory(prefix='cpu_profile_',dir=HERE) as d:
            root=Path(d);C=fixture(root);out=root/'profile';out.mkdir()
            rows,hot,check=p.replay_cell(C,out,2)
            self.assertEqual([r['decision'] for r in rows],[0,2])
            self.assertEqual(check['service_dispatches_reconstructed'],3)
            self.assertEqual(check['residual_records'],0)
            self.assertTrue(hot);self.assertEqual(len(list(out.glob('*.prof'))),2)
            self.assertTrue(all(r['exact_all_planner_fields'] for r in rows))

    def test_mismatched_score_fails_before_profiling(self):
        with tempfile.TemporaryDirectory(prefix='cpu_profile_',dir=HERE) as d:
            root=Path(d);C=fixture(root);out=root/'profile';out.mkdir();events=p.lines(C/'events.jsonl')
            next(e for e in events if e['kind']=='ces-decision')['score']+=1
            save(C/'events.jsonl',events,True)
            with self.assertRaisesRegex(AssertionError,'score'):p.replay_cell(C,out,2)
            self.assertFalse(list(out.glob('*.prof')))

    def test_changed_service_book_is_not_accepted_as_snapshot_truth(self):
        with tempfile.TemporaryDirectory(prefix='cpu_profile_',dir=HERE) as d:
            root=Path(d);C=fixture(root);out=root/'profile';out.mkdir();events=p.lines(C/'events.jsonl')
            next(e for e in events if e['kind']=='closed-loop-observation')['service_book']['actual_dispatches']=4
            save(C/'events.jsonl',events,True)
            with self.assertRaisesRegex(AssertionError,'service book'):p.replay_cell(C,out,2)

if __name__=='__main__':unittest.main()
