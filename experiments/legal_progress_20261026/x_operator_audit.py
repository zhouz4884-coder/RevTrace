"""Recompute complete outputs and paid work; source-clustered, not32 iid."""
from pathlib import Path
import json,statistics,random,csv
W=Path(__file__).resolve().parent
def main():
    src=json.loads((W/'X_GPU_OPERATOR_v1.json').read_text());r=src['rows'];assert src['formal_tuples']==32 and len(r)==128
    lookup={(x['profile'],x['mode']):x for x in r};profiles=list(dict.fromkeys(x['profile'] for x in r));comparisons=[]
    for pid in profiles:
        base=lookup[pid,'fresh'];strict=lookup[pid,'strict-full'];prefix=lookup[pid,'prefix'];protocol=lookup[pid,'revtrace-prefix']
        for x in [strict,prefix,protocol]:
            for k in ['Z','P','text','EOS','complete_Stop']:assert x['actual'][k]==base['actual'][k],(pid,k)
            assert x['actual']['complete_Stop']
            assert x['producer']['device']==0
        comparisons.append(dict(profile=pid,source_id=base['source_id'],rho=base['rho'],repeat=base['repeat'],
            prefix_over_fresh_target=prefix['target_wall_seconds']/base['target_wall_seconds'],
            prefix_over_fresh_paid_compute=prefix['paid_compute_seconds']/base['paid_compute_seconds'],
            prefix_over_strict_paid_compute=prefix['paid_compute_seconds']/strict['paid_compute_seconds'],
            same_shared_executor_protocol_over_prefix=protocol['paid_compute_seconds']/prefix['paid_compute_seconds'],
            accepted_prefix=prefix['proof']['accepted_prefix'],draft_tokens=len(prefix['draft']),
            prefix_target_seconds=prefix['target_wall_seconds'],fresh_target_seconds=base['target_wall_seconds'],
            prefix_paid_compute=prefix['paid_compute_seconds'],fresh_paid_compute=base['paid_compute_seconds']))
    def paired(rows,key):
        ids=sorted({r['source_id'] for r in rows});v=[statistics.mean(r[key] for r in rows if r['source_id']==sid) for sid in ids]
        rng=random.Random(20261026);boot=sorted(statistics.mean(rng.choices(v,k=len(v))) for _ in range(10000))
        return dict(independent_source_clusters=len(v),mean_ratio=statistics.mean(v),CI95=[boot[250],boot[9749]],
            repeats='two timing repeats averaged within source; not independent samples',scope='conditional-state operator ratio, not deployed service speedup')
    out=dict(status='PASS_INDEPENDENT_FULL_Z_P_TEXT_STOP_RECOUNT',tuples=32,methods=4,actual_method_tuples=128,
        full_equal_tuples=32,independent_source_clusters=8,
        summary={str(rho):{k:paired([r for r in comparisons if r['rho']==rho],k) for k in ['prefix_over_fresh_target','prefix_over_fresh_paid_compute','prefix_over_strict_paid_compute']} for rho in [1,3]},
        comparisons=comparisons,quality_scope='exact output equivalence in frozen batch1 target conditions; no partial-prefix WER against whole-audio transcript',
        distinction='revtrace-prefix operator is a SAME executor replication. Only actual service integration can measure WAL/Consumer overhead and deployed benefit.',
        next='GO bounded actual two-source development service; NO exclusive decoding novelty or population performance claim')
    (W/'X_OPERATOR_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n')
    with (W/'X_OPERATOR_PAIRS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparisons[0]));w.writeheader();w.writerows(comparisons)
    print(json.dumps(out['summary']))
if __name__=='__main__':main()
