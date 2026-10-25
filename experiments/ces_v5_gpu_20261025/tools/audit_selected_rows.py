"""Evaluate only actual selected first-batch row forecasts against real clocks.

Unchosen actions and second batches of abandoned plans remain unknown.
The credit predictor uses the implemented canonical-delivery approximation;
additional private display may make its real joint-credit outcome different.
"""
from pathlib import Path
from collections import defaultdict
import csv,gzip,hashlib,json,math,statistics,sys
W=Path(__file__).resolve().parent;R=W/'collected';A=W/'local_review'
sys.path[:0]=[str(W.parent/'ces_v5_20261023/runtime/src')]
from revtrace.ces_v5_policy import V5Target,predict_batch,_row_cdf,_weighted_quantile

def read(p):
    with gzip.open(p,'rt',encoding='utf8') as f:return json.load(f)
def lines(p):
    with gzip.open(p,'rt',encoding='utf8') as f:return [json.loads(s) for s in f]
def save(p,rows):
    assert not p.exists()
    with p.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

rows=[]
for p in sorted((R/'cell_metadata').glob('pilot_v1-*-config.json.gz')):
    key=p.name[:-len('-config.json.gz')];cell=key[len('pilot_v1-'):];cfg=read(p);method=cfg['ces_study']['method']
    if method not in ['risk_cost','progress','progress_joint']:continue
    es=lines(R/'traces'/(key+'-events.jsonl.gz'));vs=lines(R/'traces'/(key+'-consumer.jsonl.gz'))
    ac=lines(R/'traces'/(key+'-worker_batch_accounting.jsonl.gz'));js=lines(R/'canonical_witnesses'/(key+'.jsonl.gz'))
    t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');specs={s['session_id']:s for s in read(R/'cell_metadata'/(key+'-sessions.json.gz'))}
    commits={e['job_id']:e for e in es if e['kind']=='commit'};byid={j['job']['job_id']:j for j in js}
    decisions=[e for e in es if e['kind']=='ces-decision' and e.get('operation')]
    cal=cfg['ces_study']['calibration'];allowance=cal['v5_risk_model']['owner_delivery_seconds']
    for batch in ac:
        if not set(batch['job_ids'])&set(byid):continue
        jobs=[byid[j] for j in batch['job_ids']];first=jobs[0]['job'];op=first['ces_operation']
        ds=[d for d in decisions if d['observed_perf']<=first['enqueue_perf'] and first['session_id'] in d['sids']
            and any(f['sid']==first['session_id'] and f['window']==first['end_window'] for f in d['features'])]
        assert ds;d=ds[-1];ids={j['job']['session_id'] for j in jobs}
        targets=[V5Target(**f) for f in d['features'] if f['sid'] in ids];assert len(targets)==len(jobs)
        forecast=predict_batch(cal,op,targets);mass=[]
        for o in forecast:
            times,cum,_=_row_cdf(o);previous=0.
            assert math.isclose(cum[-1],1.) and len(cum)==len(times)+1
            for time,c in zip(times,cum[1:]):mass.append((float(time)+allowance,o.weight*float(c-previous)));previous=c
        assert math.isclose(sum(w for t,w in mass),1.)
        q90=_weighted_quantile(mass,.9)
        for item in jobs:
            j=item['job'];sid=j['session_id'];q=j['end_window'];f=next(t for t in targets if t.sid==sid)
            commit=commits[j['job_id']];installed=t0+commit['installed'];r=item['selected']['_row_receipt']
            due=f.deadline if f.display_met else min(f.deadline,f.ready+2)
            pred_commit=sum(w for t,w in mass if d['observed_perf']+t<=f.deadline)
            pred_credit=0. if f.display_expired else sum(w for t,w in mass if d['observed_perf']+t<=due)
            actual_views=[v['observed_perf'] for v in vs if v['session_id']==sid and v['valid_visible_frontier']>=j['audio_end_sample']]
            first_view=min(actual_views);good=first_view<=f.ready+2 and installed<=f.deadline
            rows.append({'cell':cell,'method':method,'operation':op,'batch_id':batch['batch_id'],
                'session':sid,'window':q,'batch_rows':len(jobs),'display_met_at_decision':f.display_met,
                'display_expired_at_decision':f.display_expired,'audio_seconds':f.audio_weight,
                'predicted_commit_probability':pred_commit,'actual_commit_met':installed<=f.deadline,
                'predicted_residual_credit_probability':pred_credit,'actual_joint_credit_met':good,
                'predicted_row_plus_owner_q90_s':q90,'actual_decision_to_owner_s':installed-d['observed_perf'],
                'covered_by_predicted_row_plus_owner_q90':installed-d['observed_perf']<=q90,
                'actual_row_terminal_to_owner_s':installed-r['terminal_perf'],
                'actual_planner_wall_s':d['planner_wall_seconds'],
                'actual_decision_to_enqueue_s':j['enqueue_perf']-d['observed_perf'],
                'private_display_precedes_canonical':first_view<installed,
                'future_private_display_could_affect_credit':not f.display_met and good and installed>f.ready+2})
save(A/'SELECTED_ROW_FORECASTS.csv',rows)
groups=defaultdict(list)
for r in rows:groups[r['cell'].split('-')[1],r['method'],r['operation']].append(r)
summary=[]
for (arrival,method,op),rr in sorted(groups.items()):
    summary.append({'arrival':arrival,'method':method,'operation':op,'selected_rows':len(rr),
        'row_plus_owner_q90_coverage':statistics.mean(r['covered_by_predicted_row_plus_owner_q90'] for r in rr),
        'mean_predicted_commit_probability':statistics.mean(r['predicted_commit_probability'] for r in rr),
        'observed_commit_met_fraction':statistics.mean(r['actual_commit_met'] for r in rr),
        'mean_predicted_credit_probability':statistics.mean(r['predicted_residual_credit_probability'] for r in rr),
        'observed_joint_credit_fraction':statistics.mean(r['actual_joint_credit_met'] for r in rr),
        'future_private_success_missing_from_canonical_only_forecast':sum(r['future_private_display_could_affect_credit'] for r in rr),
        'median_decision_to_enqueue_s':statistics.median(r['actual_decision_to_enqueue_s'] for r in rr),
        'max_decision_to_enqueue_s':max(r['actual_decision_to_enqueue_s'] for r in rr)})
save(A/'SELECTED_ROW_FORECAST_GROUPS.csv',summary)
(A/'SELECTED_ROW_AUDIT.json').write_text(json.dumps({'status':'COMPLETE_ACTUAL_SELECTED_ROW_DIAGNOSTIC',
    'selected_rows':len(rows),'GPU_calls':0,'unchosen_actions_or_unexecuted_plan_suffixes_inferred':False,
    'source_commit':'126dc815962e8f726b0cbdf214a19318b28a3629',
    'scope':'Observed calibration on reused sources; within-batch rows and repeats are dependent; not counterfactual regret',
    'credit_approximation':'Canonical-only future delivery for pending Display; observed future Private display separately identified',
    'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'selected_rows':len(rows),'groups':len(summary)}))
