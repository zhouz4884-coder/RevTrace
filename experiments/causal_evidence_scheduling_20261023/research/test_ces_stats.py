"""Synthetic CPU checks only, not additional measured serving evidence."""
from pathlib import Path
import copy,math,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'online_admission_20261022'))
from analysis_core import paired_bootstrap as old
from row_stats_core import paired_bootstrap,stratified_quality_bootstrap,_weighted_quantile

def arms():
    aa=[]
    for mode in range(2):
        arm={}
        for r in range(3):
            source={}
            for i in range(16):
                fs=[{'display':(.2+i/12+j/8)*(1-mode*.07+r*.03),'commit':2+i/4+j/9+mode*.02,'audio_seconds':2.} for j in range(3+i%4)]
                source[str(i)]={'frontiers':fs,'WER_errors':i%3+mode*(i==5),'CER_errors':i%7+mode*(i==8),'reference_words':20+i,'reference_characters':50+i}
            arm[r]={'wall':20+r-mode,'energy':30+r-mode,'sources':source}
        aa.append(arm)
    return aa

def test_matches_archived_statistic():
    a=arms();x,y=old(a,samples=143),paired_bootstrap(a,samples=143)
    for section in ['paired_median','paired_95_interval']:
        for k in x[section]:np.testing.assert_allclose(x[section][k],y[section][k],rtol=1e-12,atol=1e-12)
    for k,bounds in y['paired_99_84375_interval'].items():
        assert bounds[0]<=y['paired_95_interval'][k][0]<=y['paired_95_interval'][k][1]<=bounds[1]

def test_weighted_quantile_zero_weights_and_infinity():
    v=[1,5,None,3];s=[0,0,1,1];c=np.array([[2,0],[0,2],[1,1]])
    q=_weighted_quantile(v,s,c)
    assert q[0]==5 and math.isinf(q[1]) and math.isinf(q[2])

def test_stratified_identity_and_subjects():
    first=arms();second=copy.deepcopy(first)
    for a in second:
        for r in a:a[r]['sources']={'new-'+k:v for k,v in a[r]['sources'].items()}
    x=stratified_quality_bootstrap([(first[0],first[0]),(second[0],second[0])],samples=137)
    assert x['unique_sources']==32 and x['quality_noninferiority_0_5pp']
    assert all(v['paired_median_delta']==0 and v['paired_95_interval']==[0,0] for v in x['quality'].values())
