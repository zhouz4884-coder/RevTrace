from row_timing_core import free_gaps,available_windows,union_duration

def test_worker_lease_not_model_gap():
    bs=[{'enqueue':1.,'drained':3.},{'enqueue':3.1,'drained':4.}]
    assert free_gaps(bs,5)==[(0.,1.),(3.,3.1),(4.,5)]

def test_deadline_and_audio_both_required():
    g=[(0.,1.),(3.,4.),(5.,6.)]
    assert available_windows(g,known=2,released=3.5,deadline=5.1)==[(3.5,4.),(5.,5.1)]
    assert available_windows(g,known=6,released=1,deadline=5)==[]

def test_overlap_is_not_sum_of_causes():
    assert union_duration([(1,3),(2,5),(8,9)])==5
