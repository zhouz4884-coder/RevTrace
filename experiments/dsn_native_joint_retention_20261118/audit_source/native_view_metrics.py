"""Recorded audio-frontier continuity metrics; no alternative execution schedule.

All-withdrawal area uses H3's high-watermark deficit. Classified loss areas
are deliberately bounded by the next actual canonical/epoch boundary.
"""
from collections import Counter,defaultdict
import math

STATUSES=('compatible_boundary','refuted_boundary','missing_boundary')

def _time(value):
    if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value):
        raise ValueError('missing/nonfinite actual observation clock')
    return float(value)

def _frontier(value):
    if type(value)is not int or value<0:raise ValueError('invalid actual visible frontier')
    return value

def union_segment_area(segments,sample_rate=16000):
    """Union time x audio rectangles by source, including partially restored drops.

    A segment's missing sample interval is [low, high). Distinct sources add;
    overlapping or nested loss rectangles on one source never double count.
    """
    if type(sample_rate)is not int or sample_rate<=0:raise ValueError('invalid sample rate')
    groups=defaultdict(list)
    for segment in segments:
        start,end=_time(segment['start']),_time(segment['end'])
        low,high=_frontier(segment['low']),_frontier(segment['high'])
        if end<start or high<low:raise ValueError('negative loss rectangle')
        if end>start and high>low:groups[segment['source_id']].append((start,end,low,high))
    total=0.
    for rectangles in groups.values():
        times=sorted({x for r in rectangles for x in r[:2]})
        for begin,end in zip(times,times[1:]):
            intervals=sorted((lo,hi)for a,b,lo,hi in rectangles if a<=begin and b>=end)
            width=0;left=right=None
            for lo,hi in intervals:
                if left is None:left,right=lo,hi
                elif lo<=right:right=max(right,hi)
                else:width+=right-left;left,right=lo,hi
            if left is not None:width+=right-left
            total+=width/sample_rate*(end-begin)
    return total

def loss_window(rows,index,*,end_perf,classification,sample_rate=16000):
    """Observed missing part of this drop, ending at recovery or a support boundary."""
    row=rows[index];sid=row['source_id'];start=_time(row['observed'])
    finish=_time(end_perf)
    old=_frontier(row['_previous_visible_frontier']);new=_frontier(row['visible_frontier'])
    if new>=old:raise ValueError('window requested without actual withdrawal')
    root=row['canonical_sha'];epoch=row['owner_epoch'];previous_time=start;current=new
    segments=[];stop='service_end';restored=False;boundary=False;end=finish
    for future in rows[index+1:]:
        if future['source_id']!=sid:continue
        now=_time(future['observed'])
        if now<previous_time or now>finish:raise ValueError('loss-window clock outside actual service interval')
        lo=max(new,current)
        if lo<old and now>previous_time:segments.append(dict(source_id=sid,start=previous_time,end=now,low=lo,high=old))
        next_f=_frontier(future['visible_frontier'])
        epoch_changed=future['owner_epoch']!=epoch
        root_changed=future['canonical_sha']!=root
        canonical=future['kind']=='canonical'
        if next_f>=old:
            restored=True;end=now
            stop='restored_at_canonical_or_epoch_boundary'if canonical or epoch_changed or root_changed else'restored_within_same_root'
            break
        if canonical or epoch_changed or root_changed:
            boundary=True;end=now
            stop='owner_epoch_boundary'if epoch_changed else'next_canonical_boundary'
            break
        current=next_f;previous_time=now
    else:
        if finish<previous_time:raise ValueError('service end precedes actual Consumer observation')
        lo=max(new,current)
        if lo<old and finish>previous_time:segments.append(dict(source_id=sid,start=previous_time,end=finish,low=lo,high=old))
    return dict(source_id=sid,row_index=index,classification=classification,owner_epoch=epoch,
        canonical_sha=root,start=start,end=end,observed_duration_seconds=end-start,
        initial_removed_audio_seconds=(old-new)/sample_rate,
        before_visible_frontier=old,after_visible_frontier=new,restored=restored,
        right_censored=not restored,boundary_truncated=boundary,stop_reason=stop,
        observed_same_root_area_audio_seconds_x_wall_seconds=union_segment_area(segments,sample_rate),
        segments=segments)

def continuity_metrics(rows,canonical_events,*,end_perf,sample_rate=16000):
    """Combine independently bound canonical events with the actual row clocks."""
    end=_time(end_perf)
    if type(sample_rate)is not int or sample_rate<=0:raise ValueError('invalid sample rate')
    canonical_by_index={}
    for event in canonical_events:
        i=event['row_index']
        if i in canonical_by_index:raise ValueError('duplicate canonical audit row')
        if event['support_status']not in STATUSES:raise ValueError('unknown support-witness status')
        canonical_by_index[i]=event
    copied=[];last={};high={};counts=Counter();amount=Counter();total_area=0.;windows=[]
    for index,original in enumerate(rows):
        row=dict(original);sid=row['source_id'];now=_time(row['observed']);f=_frontier(row['visible_frontier'])
        if now>end:raise ValueError('actual Consumer observation is beyond service end')
        previous=last.get(sid);before=previous['visible_frontier']if previous else 0
        if previous:
            if now<previous['observed']:raise ValueError('actual source clock regressed')
            total_area+=max(0,high[sid]-before)/sample_rate*(now-previous['observed'])
        row['_previous_visible_frontier']=before;copied.append(row)
        high[sid]=max(high.get(sid,0),f);last[sid]=row
        if row['kind']not in ('canonical','private'):raise ValueError('unknown actual Consumer row kind')
        event=canonical_by_index.get(index)
        if row['kind']=='canonical':
            counts['canonical_applications']+=1
            if event is not None:
                if event['source_id']!=sid or event['observed']!=row['observed']:raise ValueError('canonical event attached to wrong actual row')
                for key,value in [('before_visible_frontier',before),('after_visible_frontier',f)]:
                    if key in event and event[key]!=value:raise ValueError('canonical event changed actual frontier')
                if event.get('before_nonempty_visible_ahead'):
                    counts['nonempty_ahead_canonical_applications']+=1
                    key={'compatible_boundary':'compatible_ahead_applications','refuted_boundary':'refuted_ahead_applications','missing_boundary':'missing_witness_ahead_applications'}[event['support_status']]
                    counts[key]+=1
                    if event['support_status']=='compatible_boundary':counts['compatible_ahead_preserved'if event['preserved_complete_tip']else'compatible_ahead_changed']+=1
        elif event is not None:raise ValueError('canonical witness attached to private row')
        if f<before:
            cls=('avoidable'if event is not None and event['support_status']=='compatible_boundary'else
                 'necessary'if event is not None and event['support_status']=='refuted_boundary'else'unknown')
            counts['total_withdrawals']+=1;counts[cls+'_withdrawals']+=1
            amount['removed_audio_seconds']+=(before-f)/sample_rate;amount[cls+'_removed_audio_seconds']+=(before-f)/sample_rate
            row['_loss_classification']=cls
    for sid,row in last.items():total_area+=max(0,high[sid]-row['visible_frontier'])/sample_rate*(end-row['observed'])
    if any(i>=len(rows)or i<0 for i in canonical_by_index):raise ValueError('canonical witness index outside actual rows')
    for index,row in enumerate(copied):
        if '_loss_classification'in row:windows.append(loss_window(copied,index,end_perf=end,classification=row['_loss_classification'],sample_rate=sample_rate))
    continuity={name:counts[name]for name in ('canonical_applications','nonempty_ahead_canonical_applications','compatible_ahead_applications','compatible_ahead_preserved','compatible_ahead_changed','refuted_ahead_applications','missing_witness_ahead_applications','total_withdrawals','avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals')}
    continuity.update({name:amount[name]for name in ('removed_audio_seconds','avoidable_removed_audio_seconds','necessary_removed_audio_seconds','unknown_removed_audio_seconds')})
    continuity.update(actual_consumer_rows=len(rows),source_count=len(last),total_gap_audio_seconds_x_wall_seconds=total_area,
        service_end_perf=end,gap_right_censored_windows=sum(w['right_censored']for w in windows),
        gap_boundary_truncated_windows=sum(w['boundary_truncated']for w in windows),
        gap_restored_windows=sum(w['restored']for w in windows),
        maximum_observed_same_root_gap_seconds=max((w['observed_duration_seconds']for w in windows),default=0.))
    for cls in ('avoidable','necessary','unknown'):
        area=union_segment_area([segment for w in windows if w['classification']==cls for segment in w['segments']],sample_rate)
        continuity[cls+'_gap_audio_seconds_x_wall_seconds']=area
        continuity['same_root_'+cls+'_gap_audio_seconds_x_wall_seconds']=area
    continuity['observed_loss_window_union_area_audio_seconds_x_wall_seconds']=union_segment_area([s for w in windows for s in w['segments']],sample_rate)
    continuity['gap_scope']={
        'total':'H3-compatible high-watermark frontier deficit through the explicit observed service end; includes necessary/unknown withdrawals.',
        'classified':'Union of actual loss windows within one canonical root and Owner epoch. Next canonical/epoch boundaries truncate continuation unless frontier coverage is actually restored there.',
        'avoidable':'Complete-path-compatible canonical clear; observed same-root area only, not a reconstructed full cross-root legally-supported G.',
        'restoration':'Actual visible audio frontier reaches the pre-drop frontier; this does not assert byte-identical text restoration.',
        'removed_audio_seconds':'Cumulative adjacent frontier drops; not a deduplicated fraction of offered input.',
        'non_additive':'Classified root-bounded areas do not partition full high-watermark area; separately classified window areas may overlap.'}
    assert continuity['total_withdrawals']==sum(continuity[k+'_withdrawals']for k in ('avoidable','necessary','unknown'))
    return dict(continuity=continuity,loss_windows=windows)
