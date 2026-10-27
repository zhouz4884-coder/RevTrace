"""Development-only receipt ETA bank; never a physical GPU-cost estimate."""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json


def quantile(xs, q):
    xs=sorted(xs);z=(len(xs)-1)*q;i=int(z)
    return xs[i] if i==len(xs)-1 else xs[i]+(z-i)*(xs[i+1]-xs[i])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    assert not args.output.exists()
    groups=defaultdict(list);inputs=[];included=[];excluded=[]
    for stage in ['A','C']:
        summary_path=args.results/(stage+'_SUMMARY.json')
        raw=summary_path.read_bytes();summary=json.loads(raw)
        inputs.append(dict(path=str(summary_path.relative_to(args.results)),
                           sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
        assert summary['cells']==len(summary['completed'])
        for name in summary['completed']:
            if stage=='C' and '-hold_0-' not in name:
                excluded.append(stage+'/'+name);continue
            included.append(stage+'/'+name)
            path=args.results/stage/name/'worker_records.jsonl'
            raw=path.read_bytes();rows=[json.loads(x) for x in raw.decode().splitlines() if x.strip()]
            inputs.append(dict(path=str(path.relative_to(args.results)),
                               sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
            batches=defaultdict(list)
            for x in rows:
                batches[x['job']['_delivery']['batch_id']].append(x)
            for bid,rs in batches.items():
                for x in rs:
                    j,r=x['job'],x['result'];role=j['role']
                    operation=j.get('ces_operation','generate') if role=='authority' else 'generate'
                    seconds=r['received_perf']-j['enqueue_perf']
                    assert seconds>=0
                    groups[role,len(rs),operation].append(dict(seconds=seconds,
                        cell=stage+'/'+name,job_id=j['job_id'],physical_batch=bid,
                        selector=hashlib.sha256((stage+'/'+name+'/'+j['job_id']).encode()).hexdigest()))
    entries=[]
    for (role,n,op),rows in sorted(groups.items()):
        xs=[x['seconds'] for x in rows]
        # Deterministic subsampling based on identities only; no timing/outcome
        # value or fault/source label selects the bootstrap bank.
        bank=sorted(rows,key=lambda x:x['selector'])[:64]
        entries.append(dict(role=role,physical_batch_rows=n,operation=op,
            observed_rows=len(xs),physical_batches=len({x['physical_batch'] for x in rows}),
            cells=len({x['cell'] for x in rows}),p50=quantile(xs,.5),
            p90=quantile(xs,.9),maximum=max(xs),
            eligible_for_independent_generation_initializer=(op=='generate'),
            bootstrap_samples=[dict(seconds=x['seconds'],cell=x['cell'],job_id=x['job_id']) for x in bank],
            bootstrap_selection='smallest SHA256(stage/cell/job_id), at most64 real rows, independent of outcomes'))
    report=dict(status='COMPLETE_DEVELOPMENT_ONLY_RECEIPT_CALIBRATION',
        sources='A complete24cells + C hold_0 clean/Mixed6cells; D development/heldout excluded',
        included_cells=included,excluded_C_interventions=excluded,
        scope='Actual enqueue-to-host-receipt predictor. Not lease, energy, independent samples, or net waiting benefit.',
        operation_stratified=True,no_heldout_used=True,new_GPU_calls=0,
        entries=entries,inputs=inputs,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status=report['status'],cells=len(included),
        entries=[{k:v for k,v in x.items() if k not in ('bootstrap_samples','bootstrap_selection')} for x in entries]),indent=2))


if __name__=='__main__':main()
