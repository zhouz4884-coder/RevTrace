"""Independent conventional policy adapter, sharing executors/commit core.

Not a native external serving system or independent neural implementation.
Fences and cancellation are logical: already executing GPU work is retired,
not claimed physically preempted. Uses bisect over the finite input schedule.
"""
from bisect import bisect_right
def expired(target,job_generation,F,generation):
    return not (target>F and job_generation==generation)
def covered_indices(current,ends,F):
    stop=bisect_right(ends,F)
    return range(current,stop+1)
