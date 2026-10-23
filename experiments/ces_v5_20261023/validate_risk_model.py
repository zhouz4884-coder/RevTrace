"""Audit the exact online scenario predictor against historical actual batches."""
from pathlib import Path
from collections import defaultdict
import csv, gzip, hashlib, json, statistics, sys

W=Path(__file__).resolve().parent
OLD=W.parent/'causal_evidence_scheduling_20261023'
sys.path.insert(0,str(W/'runtime/src'))
from revtrace.ces_policy import Target
from revtrace.ces_v5_policy import predict_batch,_weighted_quantile,_row_moments,choose_v5,V5Target

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def loadcsv(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def make_target(j):
    return V5Target(j['session_id'],j['end_window'],0.,8.,'candidate_token_ids' in j,
        False,False,len(j.get('candidate_token_ids',[])),0,0.,None,
        audio_seconds=j['audio_end_sample']/16000,
        interval_seconds=(j['audio_end_sample']-j['audio_start_sample'])/16000,
        prompt_tokens=len(j['prompt_tokens']))

out=W/'calibration_v2_predictor_audit'
assert not out.exists()
out.mkdir()
calpath=W/'calibration_v2/CALIBRATION.json'
cal=json.loads(calpath.read_text())
diag=OLD/'collected/evidence/formal_diagnosis_v1'
batchmap={(r['cell'],r['batch_id']):r for r in loadcsv(diag/'BATCH_PREDICTION_VS_ACTUAL.csv')}
targetmap={(r['cell'],int(r['session']),int(r['window'])):r for r in loadcsv(diag/'TARGETS.csv')}
bybatch=defaultdict(list)
for p in sorted((OLD/'collected/canonical_witnesses').glob('*.jsonl.gz')):
    cell=p.name[:-9]
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for line in f:
            r=json.loads(line)
            bybatch[(cell,r['selected']['_row_receipt']['binding']['batch_id'])].append(r['job'])
records=[]
for key,jobs in sorted(bybatch.items()):
    actual=batchmap[key]
    n=len(jobs);assert n==int(actual['rows'])
    rows=[make_target(j) for j in jobs]
    op=jobs[0]['ces_operation']
    outcomes=predict_batch(cal,op,rows)
    assert 0<len(outcomes)<=8 and abs(sum(o.weight for o in outcomes)-1)<1e-12
    lease=float(actual['actual_batch_occupancy_s'])
    mean=sum(o.weight*o.lease for o in outcomes)
    q90=_weighted_quantile([(o.lease,o.weight) for o in outcomes],.9)
    rowtimes=[float(targetmap[(key[0],j['session_id'],j['end_window'])]['row_result_after_start_s']) for j in jobs]
    errors=[]
    for k in range(1,10):
        threshold=lease*k/10
        predicted=sum(o.weight*_row_moments(o,threshold)[0] for o in outcomes)
        empirical=sum(t<=threshold for t in rowtimes)/n
        errors.append(abs(predicted-empirical))
    records.append({'cell':key[0],'pool':key[0].split('-')[0],'operation':op,'rows':n,
        'batch_id':key[1],'actual_lease_s':lease,'predicted_mean_lease_s':mean,
        'predicted_q90_lease_s':q90,'covered_by_predicted_q90':lease<=q90,
        'absolute_mean_error_s':abs(lease-mean),'row_CDF_decile_MAE':statistics.mean(errors),
        'scenario_source':outcomes[0].source})
summary={}
for pool in ['development','validation']:
    for op in ['generate','verify']:
        xs=[r for r in records if r['pool']==pool and r['operation']==op]
        summary[pool+'_'+op]={'physical_batches':len(xs),
            'median_absolute_mean_error_s':statistics.median(r['absolute_mean_error_s'] for r in xs),
            'empirical_q90_coverage':statistics.mean(r['covered_by_predicted_q90'] for r in xs),
            'mean_row_CDF_decile_MAE':statistics.mean(r['row_CDF_decile_MAE'] for r in xs)}
smoke=[]
for key,jobs in list(sorted(bybatch.items()))[:6]:
    rows=[make_target(j) for j in jobs]
    for mode in ['risk_cost','progress','progress_joint']:
        d=choose_v5(rows,now=0.,mode=mode,cal=cal,limit=16)
        assert sorted(sid for b in d['plan'] for sid in b['sids'])==sorted(j['session_id'] for j in jobs)
        smoke.append({'cell':key[0],'mode':mode,'decision':d})
with (out/'PREDICTIONS.csv').open('w',encoding='utf-8',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
(out/'SMOKE_DECISIONS.json').write_text(json.dumps(smoke,indent=2)+'\n')
report={'status':'EXACT_SCENARIO_PREDICTOR_AUDITED','schema':'historical-calibration-check-v1',
    'summary':summary,'actual_batches':len(records),'calibration_sha256':sha(calpath),
    'policy_sha256':sha(W/'runtime/src/revtrace/ces_v5_policy.py'),'script_sha256':sha(Path(__file__)),
    'GPU_calls':0,'scope':'Historical V4 selected physical batches; old validation is diagnostic and no new V5 online result',
    'row_CDF_metric':'Predicted exchangeable row service CDF compared with observed rows at 9 retrospective lease-relative thresholds; not Display Goodput',
    'in_sample_development':True,'validation_excluded_from_cost_fit':True,
    'actual_batch_choice_counterfactual_executed':False}
(out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
