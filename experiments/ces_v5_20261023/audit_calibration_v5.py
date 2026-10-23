"""Independent compressed-calibration provenance and distribution checks.

All inputs are historical development observations. This script does not run a
model or estimate a counterfactual online policy performance result.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import gzip
import hashlib
import json
import math
import statistics
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime/src'))
from revtrace.ces_policy import Target
from revtrace.ces_v5_policy import predict_batch,_row_cdf,_weighted_quantile


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--calibration',type=Path,default=HERE/'calibration_v2')
    ap.add_argument('--output',type=Path,default=HERE/'CALIBRATION_INDEPENDENT_AUDIT.json')
    args=ap.parse_args()
    if args.output.exists():raise FileExistsError('Preserve the earlier audit; select a fresh output')
    old=HERE.parent/'causal_evidence_scheduling_20261023'
    summary=read(args.calibration/'SUMMARY.json')
    cal=read(args.calibration/'CALIBRATION.json')
    rows=[json.loads(s) for s in (args.calibration/'COST_ROWS.jsonl').read_text().splitlines()]
    assert summary['calibration_sha256']==sha(args.calibration/'CALIBRATION.json')
    assert len(rows)==summary['physical_batches']==2000
    assert len({r['cell'] for r in rows})==summary['cells']==90
    assert all(r['cell'].startswith('development-') for r in rows)
    bykey={(r['cell'],r['batch_id']):r for r in rows}
    assert len(bykey)==len(rows)
    jobs=defaultdict(list)
    for source in summary['sources']:
        path=old/Path(source['path'])
        assert sha(path)==source['sha256']
        with gzip.open(path,'rt',encoding='utf8') as stream:
            for line in stream:
                witness=json.loads(line)
                key=path.name[:-9],witness['selected']['_row_receipt']['binding']['batch_id']
                j=witness['job']
                jobs[key].append(Target(j['session_id'],j['end_window'],0.,8.,
                    'candidate_token_ids' in j,False,False,len(j.get('candidate_token_ids',[])),0,0.,None,
                    audio_seconds=j['audio_end_sample']/16000,
                    interval_seconds=(j['audio_end_sample']-j['audio_start_sample'])/16000,
                    prompt_tokens=len(j['prompt_tokens'])))
    assert set(jobs)==set(bykey)
    buckets=[]
    for operation,table in [('generate','generation_scenarios'),('verify','verification_scenarios')]:
        for size,bucket in cal['v5_risk_model'][table].items():
            raw=[r for r in rows if r['operation']==operation and (size=='global' or r['rows']==int(size))]
            reps=bucket['scenarios']
            assert bucket['count']==len(raw)
            assert 1<=len(reps)<=8
            assert sum(r['weight'] for r in reps)==len(raw)
            assert all(r['weight']>0 for r in reps)
            reconstructed=[]
            for rep in reps:
                source=bykey[rep['representative_cell'],rep['representative_batch_id']]
                assert source in raw
                for key,value in source['scenario'].items():
                    if key!='weight':assert rep[key]==value,(operation,size,key)
                assert rep['represented_physical_batches']==rep['weight']
                reconstructed.append((source,rep['weight']))
            raw_failure=sum(r['scenario'].get('failed_count',0)>0 for r in raw)/len(raw)
            rep_failure=sum(w for r,w in reconstructed if r['scenario'].get('failed_count',0)>0)/len(raw)
            assert abs(raw_failure-rep_failure)<1e-12
            raw_k=Counter();rep_k=Counter()
            for r in raw:raw_k[r['scenario'].get('failed_count',0)/r['rows']]+=1/len(raw)
            for r,w in reconstructed:rep_k[r['scenario'].get('failed_count',0)/r['rows']]+=w/len(raw)
            tv=.5*sum(abs(raw_k[k]-rep_k[k]) for k in set(raw_k)|set(rep_k))
            buckets.append({'operation':operation,'size':size,'raw_batches':len(raw),'representatives':len(reps),
                'fallback_probability_raw':raw_failure,'fallback_probability_represented':rep_failure,
                'failed_fraction_distribution_TV':tv,
                'raw_ratio_p90':_weighted_quantile([(r['ratio'],1.) for r in raw],.9),
                'compressed_ratio_p90':_weighted_quantile([(r['ratio'],w) for r,w in reconstructed],.9),
                'raw_ratio_max':max(r['ratio'] for r in raw),
                'compressed_ratio_max':max(r['ratio'] for r,w in reconstructed)})
    checked=0
    for key,targets in jobs.items():
        row=bykey[key]
        assert len(targets)==row['rows']
        outcomes=predict_batch(cal,row['operation'],targets)
        assert 1<=len(outcomes)<=8
        assert abs(sum(o.weight for o in outcomes)-1.)<1e-12
        for o in outcomes:
            assert math.isfinite(o.lease) and o.lease>0
            times,cumulative,moments=_row_cdf(o)
            assert abs(cumulative[-1]-1.)<1e-12
            assert all(0<=t<=o.lease+1e-12 for t in times)
            assert all(x<=y for x,y in zip(cumulative,cumulative[1:]))
        checked+=1
    result={'status':'PASS_SCHEMA_PROVENANCE_AND_FINAL_PREDICTOR_INVARIANTS',
        'scope':'Historical development CPU audit; not held-out performance or new GPU evidence',
        'calibration_sha256':sha(args.calibration/'CALIBRATION.json'),
        'raw_physical_batches':len(rows),'source_cells':90,'final_predictor_cases_checked':checked,
        'exactly_preserved':'No-fallback/fallback probability mass per stored bucket',
        'approximated':'Detailed failed fraction and duration tails after medoid compression',
        'maximum_failed_fraction_distribution_TV':max(b['failed_fraction_distribution_TV'] for b in buckets),
        'buckets':buckets,'new_GPU_calls':0,
        'policy_sha256':sha(HERE/'runtime/src/revtrace/ces_v5_policy.py'),
        'script_sha256':sha(Path(__file__))}
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='buckets'},indent=2))


if __name__=='__main__':main()
