"""CPU statistics, exactly the old paired draw convention; not queue replay."""
from __future__ import annotations
import math,random
import numpy as np

def _relative(new,old):
    new,old=np.broadcast_arrays(np.asarray(new,float),np.asarray(old,float))
    with np.errstate(divide='ignore',invalid='ignore'):
        out=new/old-1
    out=np.where((old==0)&(new==0),0.,out)
    out=np.where((old==0)&(new>0),np.inf,out)
    both=~np.isfinite(new)|~np.isfinite(old)
    out=np.where(both,np.where(new==old,0.,np.where(new>old,np.inf,-1.)),out)
    return out

def _weighted_quantile(values,source_index,counts,q=.99):
    """Exact linear quantile of conceptual replicated frontier observations."""
    values=np.asarray([math.inf if x is None else x for x in values],float)
    ix=np.argsort(values,kind='stable');v=values[ix];s=np.asarray(source_index)[ix]
    cum=np.cumsum(counts[:,s],axis=1);n=cum[:,-1]
    if np.any(n<=0):raise ValueError('empty resampled population')
    pos=(n-1)*q;lo=np.floor(pos).astype(int);hi=np.ceil(pos).astype(int)
    li=(cum>lo[:,None]).argmax(axis=1);ui=(cum>hi[:,None]).argmax(axis=1)
    lower,upper=v[li],v[ui];f=pos-lo
    with np.errstate(invalid='ignore'):
        result=lower+f*(upper-lower)
    return np.where((f==0)|(li==ui),lower,np.where(np.isinf(upper),np.inf,result))

def _metric(run,sources,counts):
    data=[run['sources'][s] for s in sources];fs=[];si=[]
    for i,d in enumerate(data):
        fs.extend(d['frontiers']);si.extend([i]*len(d['frontiers']))
    good=np.array([sum(f['audio_seconds'] for f in d['frontiers'] if
        f['display'] is not None and f['commit'] is not None and f['display']<=2 and f['commit']<=8) for d in data])
    out={'goodput':counts@good/run['wall'],'energy':np.full(len(counts),run['energy']),
         'display':_weighted_quantile([f['display'] for f in fs],si,counts),
         'commit':_weighted_quantile([f['commit'] for f in fs],si,counts)}
    for prefix,denom in [('WER','reference_words'),('CER','reference_characters')]:
        out[prefix]=(counts@np.array([d[prefix+'_errors'] for d in data]))/(counts@np.array([d[denom] for d in data]))
    return out

def paired_bootstrap(arms,*,samples=10000,seed=20261022):
    a,b=arms;reps=sorted(a);assert reps==sorted(b) and len(reps)==3
    sources=sorted(a[reps[0]]['sources']);assert len(sources)==16
    for arm in arms:
        for r in reps:assert sorted(arm[r]['sources'])==sources
    # Match random.Random choices order in the archived pure-Python statistic.
    rng=random.Random(seed);draw_reps=[];counts=[]
    for _ in range(samples):
        draw_reps.append(rng.choices(range(3),k=3));draw=rng.choices(range(16),k=16)
        counts.append(np.bincount(draw,minlength=16))
    counts=np.vstack([np.ones(16,dtype=int),np.asarray(counts,int)]);sel=np.asarray(draw_reps,int)
    effects={k:[] for k in ['goodput','display','commit','WER','CER','energy']}
    for r in reps:
        ma,mb=_metric(a[r],sources,counts),_metric(b[r],sources,counts)
        for k in effects:effects[k].append(mb[k]-ma[k] if k in ['WER','CER'] else _relative(mb[k],ma[k]))
    point={};interval={};simultaneous={}
    for k,rows in effects.items():
        mat=np.stack(rows,axis=1);point[k]=float(np.median(mat[0]));res=np.median(np.take_along_axis(mat[1:],sel,axis=1),axis=1)
        interval[k]=[float(_ordered_quantile(res,.025)),float(_ordered_quantile(res,.975))]
        simultaneous[k]=[float(_ordered_quantile(res,.05/(2*32))),float(_ordered_quantile(res,1-.05/(2*32)))]
    return {'paired_median':point,'paired_95_interval':interval,'paired_99_84375_interval':simultaneous,'samples':samples,'seed':seed,
      'energy_resampling':'paired repeats only','schedule_interpretation':'conditional on observed per-source frontiers',
      'implementation':'vectorized exact conceptual frontier replication, tested against archived pure-Python convention'}

def _ordered_quantile(xs,q):
    xs=np.sort(np.asarray(xs,float));p=(len(xs)-1)*q;i=int(p);f=p-i
    if not f or i==len(xs)-1:return xs[i]
    if np.isinf(xs[i+1]):return math.inf
    return xs[i]+f*(xs[i+1]-xs[i])

def stratified_quality_bootstrap(arms_by_cohort,*,samples=10000,seed=20261022):
    """Pool quality of32 subjects, not goodput/energy of32 concurrent streams."""
    assert len(arms_by_cohort)==2
    sources=[]
    for a,b in arms_by_cohort:
        assert sorted(a)==sorted(b)==[0,1,2]
        ss=sorted(a[0]['sources']);assert len(ss)==16
        for arm in (a,b):
            for r in range(3):assert sorted(arm[r]['sources'])==ss
        sources.append(ss)
    assert not set(sources[0])&set(sources[1])
    rng=random.Random(seed);ri=[];counts=[[],[]]
    for _ in range(samples):
        ri.append(rng.choices(range(3),k=3))
        for c in range(2):counts[c].append(np.bincount(rng.choices(range(16),k=16),minlength=16))
    counts=[np.vstack([np.ones(16,dtype=int),np.asarray(v,int)]) for v in counts];ri=np.asarray(ri,int)
    result={}
    for prefix,denom in [('WER','reference_words'),('CER','reference_characters')]:
        effects=[]
        for r in range(3):
            e=[]
            for arm_index in range(2):
                numerator=np.zeros(samples+1);denominator=np.zeros(samples+1)
                for c,pair in enumerate(arms_by_cohort):
                    data=[pair[arm_index][r]['sources'][s] for s in sources[c]]
                    numerator+=counts[c]@np.array([d[prefix+'_errors'] for d in data])
                    denominator+=counts[c]@np.array([d[denom] for d in data])
                e.append(numerator/denominator)
            effects.append(e[1]-e[0])
        mat=np.stack(effects,axis=1);res=np.median(np.take_along_axis(mat[1:],ri,axis=1),axis=1)
        result[prefix]={'paired_median_delta':float(np.median(mat[0])),
          'paired_95_interval':[float(_ordered_quantile(res,.025)),float(_ordered_quantile(res,.975))]}
    return {'quality':result,'unique_sources':32,'strata':2,'sources_per_stratum':16,'samples':samples,'seed':seed,
      'not_32_concurrent_serving':True,'quality_noninferiority_0_5pp':all(result[k]['paired_95_interval'][1]<=.005 for k in result)}
