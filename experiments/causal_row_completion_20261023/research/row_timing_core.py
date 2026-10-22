"""Descriptive geometry only; overlapping blockers are never summed as causes."""
def free_gaps(batches,wall):
    seq=sorted(batches,key=lambda x:x['enqueue']);cursor=0.;out=[]
    for b in seq:
        if b['enqueue']>cursor:out.append((cursor,b['enqueue']))
        cursor=max(cursor,b['drained'])
    if cursor<wall:out.append((cursor,wall))
    return out

def available_windows(gaps,*,known,released,deadline):
    return [(max(a,known,released),min(b,deadline)) for a,b in gaps if min(b,deadline)>max(a,known,released)]

def union_duration(intervals):
    total=0.;left=right=None
    for a,b in sorted(intervals):
        if b<=a:continue
        if right is None:left,right=a,b
        elif a>right:total+=right-left;left,right=a,b
        else:right=max(right,b)
    return total+(0. if right is None else right-left)
