"""Summarize nested timings without summing inclusive/overlapping intervals."""
from __future__ import annotations
import argparse
import collections
import pathlib
import statistics
from cost_common import jsonl, read, put

def quantile(rows, q):
    x=sorted(rows)
    if not x:
        return None
    t=(len(x)-1)*q; i=int(t); j=min(i+1,len(x)-1)
    return x[i]+(x[j]-x[i])*(t-i)

def summarize(raw):
    raw=pathlib.Path(raw)
    origin=read(raw/'ORIGIN.json')['origin_perf'] if (raw/'ORIGIN.json').exists() else None
    end=read(raw/'SERVICE_END.json')['service_end_perf'] if (raw/'SERVICE_END.json').exists() else None
    rows=[]; observer=[]
    for path in (raw/'cost_spans').glob('*_SUMMARY.json'):
        meta=read(path)
        if meta['overflow']:
            raise ValueError('span overflow invalidates cost measurement')
        observer.append(meta)
    for path in (raw/'cost_spans').glob('*.jsonl'):
        rows.extend(jsonl(path))
    # Strict containment avoids inventing CPU time for partial boundary spans.
    selected=[r for r in rows if origin is None or
              (r['start_ns']>=origin*1e9 and r['end_ns']<=end*1e9)]
    selected_ids={(r['pid'],r['span_id']) for r in selected}
    partial=[r for r in rows if origin is not None and r['start_ns']<end*1e9 and
             r['end_ns']>origin*1e9 and (r['pid'],r['span_id']) not in selected_ids]
    by=collections.defaultdict(list)
    for r in selected:
        by[(r['role'],r['label'],r.get('file_name'))].append(r)
    families=[]
    for (role,label,file_name), values in sorted(by.items(),key=lambda x:str(x[0])):
        families.append(dict(role=role,label=label,file_name=file_name,count=len(values),
            wall_us_median=statistics.median(v['wall_ns']/1000 for v in values),
            wall_us_p95=quantile([v['wall_ns']/1000 for v in values],.95),
            thread_cpu_us_median=statistics.median(v['thread_cpu_ns']/1000 for v in values),
            inclusive_wall_ms=sum(v['wall_ns'] for v in values)/1e6,
            exclusive_thread_cpu_ms=sum(v['exclusive_thread_cpu_ns'] for v in values)/1e6,
            exclusive_wall_ms=sum(v['exclusive_wall_ns'] for v in values)/1e6))
    # Only non-nested roots on one process/thread may be combined directly.
    # Parallel threads/processes stay in their own rows, never a serving wall sum.
    per_thread=collections.defaultdict(list)
    ids={(r['pid'],r['span_id']) for r in selected}
    for r in selected:
        if (r['pid'],r['parent_span_id']) not in ids:
            per_thread[(r['role'],r['pid'],r['thread_id'])].append(r)
    roots=[]
    for key,values in per_thread.items():
        intervals=sorted((v['start_ns'],v['end_ns']) for v in values)
        for a,b in zip(intervals,intervals[1:]):
            if a[1]>b[0]:
                raise ValueError('root spans overlap on a single observed thread')
        roots.append(dict(role=key[0],pid=key[1],thread_id=key[2],
            nonnested_observed_wall_ms=sum(b-a for a,b in intervals)/1e6,
            nonnested_observed_thread_cpu_ms=sum(v['thread_cpu_ns'] for v in values)/1e6))
    return dict(original_origin=origin,original_service_end=end,observer=observer,
        total_span_count=len(rows),selected_fully_contained_spans=len(selected),
        boundary_spans_not_prorated=len(partial),families=families,thread_root_accounts=roots,
        scope='observed function footprint, not counterfactual protocol overhead',
        forbidden_operations=['sum inclusive families','sum parallel process wall as service wall',
            'wall minus thread CPU called lock wait','pro-rate partial CPU at time boundaries'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();put(a.out,summarize(a.raw))
if __name__=='__main__':
    main()
