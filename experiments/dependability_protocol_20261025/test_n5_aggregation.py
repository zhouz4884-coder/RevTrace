import math
from aggregate_n5_normal_v1 import descriptive_bootstrap,exported,median
def test_bootstrap_preserves_all_three_whole_run_values_not_windows():
    low,hi=descriptive_bootstrap([-2,0,3]);assert low<=0<=hi
def test_zero_baseline_relative_change_is_not_imputed():
    assert descriptive_bootstrap([None,1,2]) is None
def test_infinite_latency_stays_missing_in_export_not_zero():
    assert exported(median([1.,math.inf,math.inf])) is None
    assert exported(0.)==0.
