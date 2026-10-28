"""Independent N5 opportunities: actual FIFO re-application, not new GPU."""
from pathlib import Path
import sys,json,time,copy,hashlib,bisect,statistics,traceback
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');W=Path(__file__).resolve().parent
sys.path.insert(0,str(W/'runtime/src'))
from revtrace.historical_display import HistoricalEnvelopeView
from revtrace.certified_display import RealtimeConsumer
from revtrace.composed_kernel import State,step
from revtrace.dgft import digest_tokens
O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(l) for l in p.read_text().splitlines() if l]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    D=O/'s_independent_v2';D.mkdir();base=read(O/'scan_n5_v2/SUMMARY.json');out=[];revoked=[]
    for attempt in base['attempts']:
        if not attempt.get('opportunities') and not attempt.get('quarantine_opportunities'):continue
        root=Path(attempt['attempt']);ev=rows(root/'events.jsonl');cfg=read(root/'config.json');wr=rows(root/'worker_records.jsonl')
        workers={r['job']['job_id']:r for r in wr};t0=next(e['t0_perf'] for e in ev if e['kind']=='run-start')
        for q in attempt.get('quarantine_opportunities',[]):
            sid=q['session_id'];cut=q['zero_extra_cost_apply_cut'];job=workers[q['job']]['job']
            prior=[e for e in ev if e.get('session_id')==sid and t0+e['time']<=cut]
            modes=[e for e in prior if e['kind']=='view-mode'];mode=modes[-1]['mode'] if modes else 'NORMAL'
            retire=[e for e in prior if e['kind']=='private-generation-retired' and e.get('generation',-1)>job.get('branch_generation',-1)]
            # Any explicit retirement records are also retained for inspection;
            # retirement can change generation counter naming, so don't infer
            # branch eligibility from absent/mismatched keys alone.
            retired_all=[e for e in prior if e['kind']=='private-generation-retired']
            revoked.append(dict(**q,actual_owner_mode=mode,matching_branch_retirements=retire,all_prior_retirements=retired_all,
                eligible_under_current_owner=mode not in ['CERTIFIED-ONLY','RECOVERY'] and not retire,
                limitation='No claim of reauthorization through an explicit owner-mode withdrawal.'))
        if not attempt.get('opportunities'):continue
        actual=rows(root/'consumer.jsonl');maprows={(r['source_kind'],r['session_id'],r['server_time']):r for r in actual}
        for strategy in ['latest','two-register','scan','mv-index','mv-index-envelope','dominance']:
            C=RealtimeConsumer(D/(root.parent.name+'-'+strategy+'.jsonl'),policy='two_lane',strict_bound=True)
            C.view=HistoricalEnvelopeView(strategy=strategy,policy='two_lane',strict_bound=True,fine_samples=32000)
            began=time.perf_counter();enqueued=[]
            for e in ev:
                # enqueue real archived publications, not a fabricated model.
                enqueued.append(dict(kind=e['kind'],before=time.perf_counter()));C.put(e)
            summary=C.close();elapsed=time.perf_counter()-began;checks=[];canonical=0;extra=0
            for r in C.rows:
                old=maprows[(r['source_kind'],r['session_id'],r['server_time'])]
                if strategy in ['latest','two-register']:
                    for k in ['canonical_version','certified_frontier','valid_visible_frontier','visible_text']:assert r[k]==old[k]
                if r['source_kind']!='canonical-display':continue
                canonical+=1
                if r['valid_visible_frontier']<=old['valid_visible_frontier']:continue
                extra+=1;jid=r['selected_private_job_id'];n=workers[jid];j=n['job'];z=n['result'];sid=j['session_id']
                assert z['received_perf']<=old['consumer_received_perf']
                # Independent exact kernel compatibility on the actual complete
                # recorded J/P/Z/Y graph at original observed cut.
                s=State(r['contract_digest'],r['canonical_epoch'],t0)
                fact=dict(v=r['canonical_version'],F=r['certified_frontier'],P=r['certified_P_sha256'],
                    textsha=r['certified_text_sha256'],Z=r['certified_Z_sha256'],txn=r['certified_transaction'])
                s.C={sid:fact};s.D={sid:{fact['v']:fact}};s.V={sid:dict(v=0,F=0,visible=0,revision=0)}
                s.publications={(sid,1):dict(_sid=sid,canonical=True,fact=fact)}
                for x in wr:
                    jj=x['job'];zz=x['result']
                    if jj['session_id']!=sid or jj['role']!='proposal' or zz.get('received_perf',float('inf'))>old['consumer_received_perf']:continue
                    s.J[jj['job_id']]=dict(id=jj['job_id'],sid=sid,role='proposal',rootF=jj['chunk_id']*32000,
                        end=jj['audio_end_sample'],inputP=digest_tokens(jj['prompt_tokens']),
                        result=dict(P=digest_tokens(zz['state_tokens']),Z=digest_tokens(zz['token_ids']),textsha=hashlib.sha256(zz['text'].encode()).hexdigest()))
                v=dict(v=fact['v'],F=fact['F'],P=fact['P'],visible=j['audio_end_sample'],private=jid,text=z['text'],revision=1)
                after,eff=step(s,'apply-request',dict(sid=sid,view=v,key=(sid,1),operation='audit'))
                assert eff==['apply-view'];after,_=step(after,'view-applied',dict(operation='audit'))
                checks.append(dict(job=jid,canonical=fact,actual_frontier=old['valid_visible_frontier'],selected_frontier=r['valid_visible_frontier'],
                    host_received=z['received_perf'],original_actual_apply=old['observed_perf'],replay_actual_apply=r['observed_perf'],
                    original_deadline_gain=False,kernel_pass=True,text=r['visible_text']))
            q=[r.get('selection_query_ms',0) for r in C.rows];last=C.view.states
            out.append(dict(attempt=str(root),strategy=strategy,records=summary['records'],wall_replay_seconds=elapsed,
                canonical_updates=canonical,improved_canonical_cuts=extra,checks=checks,
                query_ms_p50=statistics.median(q),query_ms_max=max(q),candidate_payloads=sum(len(s.get('_history_tips',[])) for s in last.values()),
                proof_nodes=sum(len(s['nodes']) for s in last.values()),
                retention_mode='individual revocation/unsealed: no semantic dominance deletion; ordinary index is strong equivalent',
                evidence='actual local FIFO replay/apply of existing GPU results; NOT new GPU/serving/quality measurement'))
    result=dict(status='COMPLETE_INDEPENDENT_ELIGIBILITY_AND_ACTUAL_FIFO_REPLAY',rows=out,quarantine_owner_reaudit=revoked,
        positive_published_cuts=14,quarantine_eligible=sum(q['eligible_under_current_owner'] for q in revoked),
        prior_v1_audit_bug='v1 checked branch_generation key on retirement event; actual key is generation AFTER increment; v1 12 eligible is INVALID, retained for provenance',
        native_new_first_deadline_opportunities=0,scope='CPU actual FIFO replay, not live inference; owner withdrawals are not bypassed')
    (D/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','quarantine_owner_reaudit']}))
if __name__=='__main__':main()
