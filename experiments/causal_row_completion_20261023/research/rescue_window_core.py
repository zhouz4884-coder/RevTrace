"""Conservative interval intersections, not a replacement-schedule simulator."""
def subtract(windows,blocked):
    result=list(windows)
    for x,y in sorted(blocked):
        if y<=x:continue
        new=[]
        for a,b in result:
            if y<=a or x>=b:new.append((a,b));continue
            if a<x:new.append((a,min(b,x)))
            if y<b:new.append((max(a,y),b))
        result=new
    return [(a,b) for a,b in result if b>a]
