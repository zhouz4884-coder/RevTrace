"""Recompute bounded published tables under their own measurement contracts."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,statistics
W=Path(__file__).resolve().parent;T=W/'public_tables/experiments'
def rows(p):return list(csv.DictReader(p.open(newline='',encoding='utf8')))
def med(xs):return statistics.median(map(float,xs))
cells=T/'phase_n_20261021/tables/T1_CELLS.csv';pairs=T/'phase_n_20261021/tables/T1_FACTORIAL_PAIRS.csv'
groups=defaultdict(list)
for r in rows(cells):
    if '-obs1-' not in r['cell']:continue
    name=r['cell'].split('-obs1-')[0];groups[name].append(r)
assert len(groups)==4 and all(len(rs)==3 for rs in groups.values())
t1=[dict(config=k,repeats=len(rs),**{m:med(r[m] for r in rs) for m in ['xrt','display_p99','commit_p99','gpu_j_per_audio_second']},
         obsolete_publications=sum(int(r['obsolete_publication']) for r in rs),
         whole_display_P99_passes=sum(float(r['display_p99'])<=2 for r in rs)) for k,rs in sorted(groups.items())]
ps=defaultdict(list)
for r in rows(pairs):ps[(r['comparison'],r['mode'],r['policy'])].append(r)
effects=[]
for key,rs in sorted(ps.items()):
    assert len(rs)==3
    effect=dict(zip(['comparison','mode','policy'],key));effect['repeats']=3
    for m in ['throughput_ratio','gpu_energy_ratio','display_p99_reduction','commit_p99_ratio']:
        if all(r[m] for r in rs):effect[m]={'paired_median':med(r[m] for r in rs),'min':min(float(r[m]) for r in rs),'max':max(float(r[m]) for r in rs)}
    effects.append(effect)
r4file=T/'phase_d_20261021/tables/R4_GOODPUT_AND_RUN_PASS.csv'
r4=rows(r4file)
for r in r4:
    assert len(json.loads(r['goodput_each_repeat']))==int(r['runs'])==3
    assert med(json.loads(r['goodput_each_repeat']))==float(r['goodput_2_8_median'])
rowfile=T/'causal_row_completion_20261023/evidence_formal/ROW_FORMAL_RESULTS_v1/GROUPS.csv'
row=rows(rowfile);assert len(row)==50
for r in row:assert int(r['repeats'])==3
summary={'status':'PASS_PUBLISHED_NUMERICAL_TABLE_RECOUNT_NOT_NEW_GPU_REEXECUTION',
  'T1_contract':'repaired v4 e73115c; c16, same 12 sources/16 slots, full observer on, fine2/rho1or3, durable group-ready; frontier P99',
  'T1_groups':t1,'T1_paired_effects':effects,
  'R4_contract':'fixed repaired PhaseD carrier, nested c8/c4 subsets of metadata-selected16 speakers, actual FIFO Consumer,2s/8s; not sustained maximum capacity',
  'R4_groups':r4,
  'Row150_contract':'120 core+30 distinct-source validation;50groups x3; shared Row SDK for all methods, not exclusive DGFT executor',
  'Row150_groups':row,
  'input_sha256':{str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [cells,pairs,r4file,rowfile]}}
(W/'PERFORMANCE_RECOUNT_v1.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'T1':t1,'paired':effects,'R4_groups':len(r4),'Row150_groups':len(row)}))
