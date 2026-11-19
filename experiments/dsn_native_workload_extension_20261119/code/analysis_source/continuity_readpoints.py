"""Actual event-sourced Consumer read points; no model/runtime imports."""
from collections import defaultdict
import math, statistics

CLASSES=('avoidable','necessary','unknown')
def need(ok,message):
    if not ok:raise ValueError(message)
def finite(x,name):
    need(not isinstance(x,bool)and isinstance(x,(int,float))and math.isfinite(x),name)
    return float(x)
def width(intervals):
    total=0;left=right=None
    for lo,hi in sorted(intervals):
        if hi<=lo:continue
        if left is None:left,right=lo,hi
        elif lo<=right:right=max(right,hi)
        else:total+=right-left;left,right=lo,hi
    return total+(right-left if left is not None else 0)
def union_area(segments):
    groups=defaultdict(list)
    for s in segments:
        a,b=finite(s['start'],'segment start'),finite(s['end'],'segment end')
        lo,hi=s['low'],s['high']
        need(type(lo)is int and type(hi)is int and 0<=lo<=hi and a<=b,'invalid loss rectangle')
        if a<b and lo<hi:groups[s['source_id']].append(s)
    result=0.
    for ss in groups.values():
        times=sorted({t for s in ss for t in(s['start'],s['end'])})
        for a,b in zip(times,times[1:]):
            result+=(b-a)*width((s['low'],s['high'])for s in ss if s['start']<=a and s['end']>=b)/16000
    return result
def duration_statistics(values):
    a=sorted(values)
    if not a:return dict(n=0,min_seconds=None,median_seconds=None,mean_seconds=None,p95_linear_seconds=None,max_seconds=None)
    pos=(len(a)-1)*.95;i=int(pos);j=min(i+1,len(a)-1)
    return dict(n=len(a),min_seconds=a[0],median_seconds=statistics.median(a),mean_seconds=statistics.mean(a),p95_linear_seconds=a[i]+(a[j]-a[i])*(pos-i),max_seconds=a[-1])

def high_watermark_gap(rows,end):
    """Integrate actual per-source state deficit through explicit closeout."""
    last={};peak={};area=0.
    for row in rows:
        sid=row['source_id'];t=row['observed'];F=row['visible_frontier']
        if sid in last:
            before=last[sid]
            area+=(t-before['observed'])*max(0,peak[sid]-before['visible_frontier'])/16000
        peak[sid]=max(peak.get(sid,0),F);last[sid]=row
    for sid,row in last.items():area+=(end-row['observed'])*max(0,peak[sid]-row['visible_frontier'])/16000
    return area

def validate_rows(rows,source_id,origin,end,retain_views):
    last=origin
    for row in rows:
        t=finite(row['observed'],'actual observation clock')
        need(origin<=t<=end and t>=last,'Consumer clock outside original closed service interval')
        need(row['source_id']==source_id,'Consumer source mismatch')
        need(row['kind']in('canonical','private'),'unknown actual row kind')
        for key in ('visible_frontier','certified_frontier'):
            need(type(row[key])is int and row[key]>=0,'invalid actual frontier')
        need(type(row.get('consumer_retain_views'))is bool and row['consumer_retain_views']is retain_views,'actual S flag mismatch')
        last=t

def validate_windows(rows,events,windows,end):
    byindex={e['row_index']:e for e in events};need(len(byindex)==len(events),'duplicate canonical support index')
    for i,event in byindex.items():
        need(type(i)is int and 0<=i<len(rows),'canonical support index outside actual rows')
        r=rows[i];previous=next((x for x in reversed(rows[:i])if x['source_id']==r['source_id']),None)
        before=previous['visible_frontier']if previous else 0
        need(r['kind']=='canonical'and event['source_id']==r['source_id']and event['observed']==r['observed'],'canonical support event has wrong actual row')
        need(event['new_canonical_sha']==r['canonical_sha']and event['before_visible_frontier']==before and event['after_visible_frontier']==r['visible_frontier'],'canonical support event frontier/root differs')
        need(event['metadata_binding_checked']is True,'canonical support metadata was not bound')
    for w in windows:
        i=w['row_index'];need(type(i)is int and 0<=i<len(rows),'window row outside actual observations')
        row=rows[i];previous=next((r for r in reversed(rows[:i])if r['source_id']==row['source_id']),None)
        old=previous['visible_frontier']if previous else 0
        need(row['observed']==w['start']and old==w['before_visible_frontier']and row['visible_frontier']==w['after_visible_frontier'],'window is not bound to actual drop')
        need(row['visible_frontier']<old,'window lacks actual frontier decrease')
        event=byindex.get(i)
        cls={'compatible_boundary':'avoidable','refuted_boundary':'necessary','missing_boundary':'unknown'}.get(event['support_status'])if event else'unknown'
        need(w['classification']==cls,'support classification changed')
        need(w['source_id']==row['source_id']and w['owner_epoch']==row['owner_epoch']and w['canonical_sha']==row['canonical_sha'],'window identity changed')
        need(w['start']<=w['end']<=end and abs(w['end']-w['start']-w['observed_duration_seconds'])<1e-8,'window clock changed')
        need(abs((old-row['visible_frontier'])/16000-w['initial_removed_audio_seconds'])<1e-9,'window removed audio changed')
        if w['restored']:
            restore=[r for r in rows[i+1:]if r['source_id']==row['source_id']and r['observed']==w['end']]
            need(restore and restore[0]['visible_frontier']>=old,'restoration lacks actual observation')
        # The rectangle list must be the actual state's loss over this window,
        # not only an area-preserving rectangle with the wrong read-point span.
        own=[row]+[r for r in rows[i+1:]if r['source_id']==row['source_id']and r['observed']<w['end']]
        expected=[]
        for j,r in enumerate(own):
            stop=own[j+1]['observed']if j+1<len(own)else w['end']
            lo=max(row['visible_frontier'],r['visible_frontier'])
            if stop>r['observed']and lo<old:expected.append(dict(source_id=row['source_id'],start=r['observed'],end=stop,low=lo,high=old))
        need(w['segments']==expected,'loss rectangles differ from actual event-sourced state')
        need(abs(union_area(w['segments'])-w['observed_same_root_area_audio_seconds_x_wall_seconds'])<1e-8,'window rectangle area changed')
    return byindex

def credited_readpoints(frontiers,rows,windows,*,source_id,origin,end,initial_known=True,initial_visible=0):
    """Read at original offer+2, with final state persistent through FIFO closeout.

    Event state is right-continuous. Windows use [start,end) except an
    explicitly service-end-censored final segment includes that endpoint for
    this discrete read; spatial losses intersect each original audio interval.
    """
    origin=finite(origin,'original origin');end=finite(end,'explicit service closeout')
    need(end>=origin,'service closeout precedes origin')
    details=[];previous=0
    for f in frontiers:
        need(f['source_id']==source_id and type(f['frontier'])is int and f['frontier']>previous,'readpoint source/cadence order changed')
        F=f['frontier'];lo=previous;previous=F;w=(F-lo)/16000
        need(abs(f['audio_seconds']-w)<1e-9,'readpoint original interval weight changed')
        offer=finite(f['offer'],'original offer');read=offer+2.
        D,C=f['D'],f['C']
        if D is not None:need(finite(D,'original D')>=0,'negative original D')
        if C is not None:need(finite(C,'original C')>=0,'negative original C')
        eligible=D is not None and C is not None and D<=2. and C<=8.
        first=offer+D if D is not None else None
        item=dict(source_id=source_id,frontier=F,interval_start=lo,audio_seconds=w,offer=offer,first_D=D,first_C=C,original_first_credit=eligible,read_perf=read)
        if not eligible:
            item.update(status='not_first_credited',actual_visible_frontier=None,missing_audio_seconds=None)
        elif read>end:
            item.update(status='censored_after_service_end',actual_visible_frontier=None,missing_audio_seconds=None)
        elif not initial_known:
            item.update(status='censored_initial_state_unwitnessed',actual_visible_frontier=None,missing_audio_seconds=None)
        else:
            seen=[r for r in rows if r['source_id']==source_id and r['observed']<=read]
            visible=seen[-1]['visible_frontier']if seen else initial_visible
            missing_low=max(lo,visible);missing=max(0,F-missing_low)/16000
            byclass=defaultdict(list);matched=[]
            for window in windows:
                if window['source_id']!=source_id or first>window['start']:continue
                found=False
                for s in window['segments']:
                    at_time=s['start']<=read<s['end']
                    at_close=(read==end==s['end']and window['stop_reason']=='service_end')
                    if not(at_time or at_close):continue
                    a,b=max(missing_low,s['low']),min(F,s['high'])
                    if a<b:byclass[window['classification']].append((a,b));found=True
                if found:matched.append(window['row_index'])
            all_intervals=[x for xs in byclass.values()for x in xs]
            classified=width(all_intervals)/16000
            need(classified<=missing+1e-9,'classified loss exceeds actual missing audio')
            item.update(status='observed',actual_visible_frontier=visible,missing_audio_seconds=missing,
                missing_frontier_weight_audio_seconds=w if visible<F else 0.,
                same_root_classified_union_audio_seconds=classified,
                unclassified_beyond_root_windows_audio_seconds=max(0.,missing-classified),
                classifications={k:width(byclass[k])/16000 for k in CLASSES},matched_window_rows=sorted(set(matched)))
        details.append(item)
    eligible=[x for x in details if x['original_first_credit']]
    observed=[x for x in eligible if x['status']=='observed'];censored=[x for x in eligible if x['status']!='observed']
    total=math.fsum(x['audio_seconds']for x in eligible);censored_audio=math.fsum(x['audio_seconds']for x in censored)
    missing=math.fsum(x['missing_audio_seconds']for x in observed)
    summary=dict(first_credited_frontiers=len(eligible),first_credited_audio_seconds=total,
        readpoint_observed_frontiers=len(observed),readpoint_observed_credited_audio_seconds=math.fsum(x['audio_seconds']for x in observed),
        readpoint_censored_frontiers=len(censored),readpoint_censored_credited_audio_seconds=censored_audio,
        observed_missing_audio_seconds=missing,missing_audio_seconds_lower=missing,missing_audio_seconds_upper=missing+censored_audio,
        fully_observed_missing_audio_seconds=missing if not censored else None,
        observed_missing_frontier_weight_audio_seconds=math.fsum(x['missing_frontier_weight_audio_seconds']for x in observed),
        observed_missing_frontiers=sum(x['missing_audio_seconds']>0 for x in observed),
        same_root_classified_union_audio_seconds=math.fsum(x['same_root_classified_union_audio_seconds']for x in observed),
        unclassified_beyond_root_windows_audio_seconds=math.fsum(x['unclassified_beyond_root_windows_audio_seconds']for x in observed),
        classifications={k:math.fsum(x['classifications'][k]for x in observed)for k in CLASSES},
        state_scope='Actual event-sourced state persists through explicit complete FIFO SERVICE_END; reads beyond END or without initial witness are censored, never assumed zero.')
    return dict(summary=summary,frontiers=details)

def aggregate_readpoints(records):
    keys=('first_credited_frontiers','first_credited_audio_seconds','readpoint_observed_frontiers','readpoint_observed_credited_audio_seconds','readpoint_censored_frontiers','readpoint_censored_credited_audio_seconds','observed_missing_audio_seconds','missing_audio_seconds_lower','missing_audio_seconds_upper','observed_missing_frontier_weight_audio_seconds','observed_missing_frontiers','same_root_classified_union_audio_seconds','unclassified_beyond_root_windows_audio_seconds')
    out={k:sum(r[k]for r in records)for k in keys}
    out['fully_observed_missing_audio_seconds']=out['observed_missing_audio_seconds']if not out['readpoint_censored_frontiers']else None
    out['classifications']={k:math.fsum(r['classifications'][k]for r in records)for k in CLASSES}
    return out
