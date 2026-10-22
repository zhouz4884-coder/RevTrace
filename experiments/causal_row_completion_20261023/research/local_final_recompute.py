"""Second implementation audit of actual final tables/CIs on the local CPU."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,random,sys
W=Path(__file__).resolve().parent;D=W/'formal_evidence_complete_v1';OLD=W.parent/'online_admission_20261022'
sys.path.insert(0,str(OLD));from analysis_core import paired_bootstrap,good_audio,quantile,median
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def rows(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def number(v):return None if v in ['',None,'None','null'] else float(v)
F=defaultdict(list);Q=defaultdict(dict);cells={}
for cohort,stage in [('core','formal_row_v1'),('validation','validation_row_v1')]:
    A=D/(stage+'_independent_audit_v2')
    for r in rows(A/'COMMON_FRONTIERS.csv'):
        F[cohort,r['cell']].append({**r,**{k:number(r[k]) for k in ['audio_seconds','display','commit','certified_consumer']}})
    for r in rows(A/'SOURCE_QUALITY.csv'):
        Q[cohort,r['cell']][r['source_id']]={k:int(r[k]) for k in ['WER_errors','reference_words','CER_errors','reference_characters']}
    for r in rows(A/'SERVICE_CELLS.csv'):
        c=r['cell'];cells[cohort,c]=r;fronts=F[cohort,c];quality=list(Q[cohort,c].values())
        assert abs(sum(f['audio_seconds'] for f in fronts)-float(r['audio_seconds']))<1e-6
        assert abs(good_audio(fronts)/float(r['wall_seconds'])-float(r['Audio_Goodput_2_8']))<1e-10
        for k,field in [('display','display_P99'),('commit','commit_P99')]:assert abs(quantile([f[k] for f in fronts],.99)-float(r[field]))<1e-10
        assert abs(sum(q['WER_errors'] for q in quality)/sum(q['reference_words'] for q in quality)-float(r['WER']))<1e-12
        assert abs(sum(q['CER_errors'] for q in quality)/sum(q['reference_characters'] for q in quality)-float(r['CER']))<1e-12
assert len(cells)==150
def arm(cohort,policy,delivery):
    out={}
    for repeat in range(3):
        name=f'{policy}-{delivery}-sync16-F2-r{repeat}';c=cells[cohort,name]
        out[repeat]={'wall':float(c['wall_seconds']),'energy':float(c['GPU_J_audio_s']),
          'sources':{s:dict(q,frontiers=[f for f in F[cohort,name] if f['source_id']==s]) for s,q in Q[cohort,name].items()}}
    return out
stored=read(D/'ROW_FORMAL_RESULTS_v1/PAIRED_COMPARISONS.json');checks=[]
for bm,bd in [('dgft','batch'),('fine','row')]:
    x=paired_bootstrap((arm('core',bm,bd),arm('core','dgft','row')),samples=10000,seed=20261022)
    y=next(c['effect'] for c in stored if c['cohort']=='core' and c['load']=='sync16' and c['traffic']=='F2' and c['baseline']==bm+'-'+bd and c['new']=='dgft-row')
    for k in x['paired_median']:assert abs(x['paired_median'][k]-y['paired_median'][k])<1e-10
    for k in x['paired_95_interval']:
        for a,b in zip(x['paired_95_interval'][k],y['paired_95_interval'][k]):assert abs(a-b)<1e-10
    checks.append({'baseline':bm+'-'+bd,'new':'dgft-row','original_pure_Python10000_draws_match_vectorized_actual_data':True})
    print('VERIFIED_FULL_PURE_BOOTSTRAP',bm,bd,flush=True)
# Independently pool error counts,not the two cohorts' service clocks.
pairs=[(arm(cohort,'fine','row'),arm(cohort,'dgft','row')) for cohort in ['core','validation']]
sources=[sorted(a[0]['sources']) for a,b in pairs];assert all(len(x)==16 for x in sources) and not set(sources[0])&set(sources[1])
def qeffect(ri,selected):
    out={k:[] for k in ['WER','CER']}
    for r in ri:
        for prefix,denom in [('WER','reference_words'),('CER','reference_characters')]:
            values=[]
            for ai in range(2):
                ds=[pairs[c][ai][r]['sources'][s] for c in range(2) for s in selected[c]]
                values.append(sum(d[prefix+'_errors'] for d in ds)/sum(d[denom] for d in ds))
            out[prefix].append(values[1]-values[0])
    return {k:median(v) for k,v in out.items()}
point=qeffect([0,1,2],sources);rng=random.Random(20261022);draws={k:[] for k in point}
for _ in range(10000):
    ri=rng.choices([0,1,2],k=3);ss=[rng.choices(s,k=16) for s in sources];q=qeffect(ri,ss)
    for k in draws:draws[k].append(q[k])
quality={'paired_median':point,'paired_95_interval':{k:[quantile(v,.025),quantile(v,.975)] for k,v in draws.items()}}
reference=next(x for x in read(D/'ROW_FORMAL_RESULTS_v1/QUALITY32_STRATIFIED.json') if x['baseline']=='fine-row' and x['traffic']=='F2')['quality']
for k in point:
    assert abs(point[k]-reference[k]['paired_median_delta'])<1e-12
    assert all(abs(a-b)<1e-12 for a,b in zip(quality['paired_95_interval'][k],reference[k]['paired_95_interval']))
papers=read(OLD/'PAPER_BEFORE.json');assert all(hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'] for r in papers)
out={'status':'PASS_LOCAL_ALL150_FULL_DENOMINATORS_METRICS_AND_ACTUAL10000_DRAW_CI_RECOMPUTE',
 'actual_cells':150,'pure_Python_primary_and_Fine_comparison_CIs':checks,'quality32_separate_naive_recompute':quality,
 'paper_files_unchanged':len(papers),'new_model_calls':0,'archived_original_statistic_sha256':hashlib.sha256((OLD/'analysis_core.py').read_bytes()).hexdigest(),
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(W/'LOCAL_FINAL_RECOMPUTE_v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
