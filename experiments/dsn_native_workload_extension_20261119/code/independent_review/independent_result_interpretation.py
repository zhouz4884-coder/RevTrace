"""Read-only independent raw-Consumer recheck; no runtime/recount imports."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,math,statistics,sys

E=Path(__file__).resolve().parents[1]
CAM=E/'gpu_results/SERVICE_LONG_NATURAL_V1'
OUT=Path(__file__).resolve().parent
CONDITIONS=('conservative_s1','r1s0','r1s1')
INPUTS={}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path,lines=False):
 raw=Path(path).read_bytes();INPUTS[Path(path).relative_to(E).as_posix()]=dict(bytes=len(raw),sha256=sha(raw))
 return [json.loads(x)for x in raw.splitlines()if x.strip()]if lines else json.loads(raw)
def close(a,b):assert math.isclose(a,b,abs_tol=1e-8,rel_tol=1e-10),(a,b)
def cutsha(cut):return sha(json.dumps(cut,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8'))
def normalize(text):return ''.join(c for c in text if not c.isspace())
def edits(a,b):
 previous=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  now=[i]
  for j,y in enumerate(b,1):now.append(min(previous[j]+1,now[-1]+1,previous[j-1]+(x!=y)))
  previous=now
 return previous[-1]
def area(segments):
 total=0.
 for sid in {s['source_id']for s in segments}:
  own=[s for s in segments if s['source_id']==sid]
  times=sorted({s[k]for s in own for k in('start','end')})
  for a,b in zip(times,times[1:]):
   intervals=sorted((s['low'],s['high'])for s in own if s['start']<=a and b<=s['end'])
   union=[]
   for lo,hi in intervals:
    if union and lo<=union[-1][1]:union[-1]=(union[-1][0],max(hi,union[-1][1]))
    else:union.append((lo,hi))
   total+=(b-a)*sum(hi-lo for lo,hi in union)/16000
 return total
def durations(values):
 return dict(n=len(values),min_ms=1000*min(values),median_ms=1000*statistics.median(values),max_ms=1000*max(values))if values else dict(n=0,min_ms=None,median_ms=None,max_ms=None)

def run():
 formal=read(E/'review/FINAL_RECOUNT_V1/SUMMARY.json');fgate=read(E/'review/FINAL_RECOUNT_V1/GATE.json')
 assert fgate['status']==formal['status']=='PASS_COMPLETE_NATURAL_WORKLOAD_THREE_POLICY_RECOUNT'
 campaign=read(CAM/'SUMMARY.json');plan=read(CAM/'CONFIG.json')
 assert campaign['completed_trials']==campaign['planned_trials']==24 and len(campaign['cells'])==24
 assert not campaign['failed_attempts']
 sources={s['source_id']:s for s in plan['sources']};assert len(sources)==4
 reference=read(E/'gpu_results/REFERENCE_LONG_V1/REFERENCE_DETAILS.json')
 refs={(r['source_id'],r['end']):r['original_full_cut']for r in reference}
 cell_data={};all_windows=[];all_points=[];quality={};records=[];flips=[]
 for c in campaign['cells']:
  cid=c['cell_id'];root=CAM/'cells'/cid;sid=c['source_id'];spec=sources[sid]
  cfg=read(root/'CONFIG.json');native=read(root/'SUMMARY.json');external=read(root/'EXTERNAL_FACTORIAL_AUDIT.json')
  assert external==c and cfg['settings']['sources']==[spec]
  origin=read(root/'ORIGIN.json')['origin_perf'];end=read(root/'SERVICE_END.json')['service_end_perf']
  rows=read(root/'consumer.jsonl',True);view=read(root/'INDEPENDENT_VIEW_AUDIT.json')
  windows=read(root/'view_audit/OBSERVED_LOSS_WINDOWS.json');events=read(root/'view_audit/CANONICAL_SUPPORT_EVENTS.json')
  binding=next(r for r in view['input_files']if r['path']=='consumer.jsonl')
  assert {k:binding[k]for k in('bytes','sha256')}==INPUTS[(root/'consumer.jsonl').relative_to(E).as_posix()]
  byrow={v['row_index']:v for v in events};assert len(byrow)==len(events)
  for i,r in enumerate(rows):
   assert origin<=r['observed']<=end and(i==0 or rows[i-1]['observed']<=r['observed'])
   assert r['source_id']==sid
   if r['kind']=='canonical':
    meta=r['view_reconciliation'];event=byrow[i]
    assert event['metadata_binding_checked']and event['support_status']==meta['support_status']
    # The service frontier may stay0 while text is empty; the installed full
    # cut's input boundary is explicitly carried by the support event.
    assert event['new_canonical_sha']==r['canonical_sha']==cutsha(refs[sid,event['new_canonical_frontier']])
  frontiers=[];previous=0;cross=Counter();cross_audio=Counter();missing=[]
  for f in c['primary']['frontiers']:
   F=f['frontier'];offer=origin+F/16000;weight=(F-previous)/16000;previous=F
   close(offer,f['offer']);close(weight,f['audio_seconds'])
   D=next((r['observed']-offer for r in rows if r['observed']>=offer and r['visible_frontier']>=F),None)
   C=next((r['observed']-offer for r in rows if r['observed']>=offer and r['certified_frontier']>=F),None)
   assert(D is None)==(f['D']is None)and(C is None)==(f['C']is None)
   if D is not None:close(D,f['D'])
   if C is not None:close(C,f['C'])
   dfail=D is None or D>2;cfail=C is None or C>8
   group='both_miss'if dfail and cfail else'D2_only'if dfail else'C8_only'if cfail else'none'
   cross[group]+=1;cross_audio[group]+=weight
   ff=dict(frontier=F,interval_start=F-round(weight*16000),offer=offer,D=D,C=C,audio_seconds=weight,credit=not(dfail or cfail));frontiers.append(ff)
   if ff['credit']:
    t=offer+2;assert t<=end
    state=next((r for r in reversed(rows)if r['observed']<=t),None);assert state is not None
    low=max(ff['interval_start'],state['visible_frontier']);amount=max(0,F-low)/16000
    if amount:
     active=[w for w in windows if offer+D<=w['start']and any(s['start']<=t<s['end']and max(low,s['low'])<min(F,s['high'])for s in w['segments'])]
     assert len(active)==1
     point=dict(cell_id=cid,condition=c['condition'],repeat=c['repeat'],source_id=sid,frontier=F,offer=offer,first_D=D,first_C=C,read_perf=t,
       actual_visible_frontier=state['visible_frontier'],missing_audio_seconds=amount,classification=active[0]['classification'],window_row_index=active[0]['row_index'])
     missing.append(point);all_points.append(point)
  close(sum(f['audio_seconds']for f in frontiers if f['credit']),c['primary']['dual_deadline_audio_credit_seconds'])
  actual_gap=0.;peak=0
  for i,r in enumerate(rows):
   peak=max(peak,r['visible_frontier']);stop=rows[i+1]['observed']if i+1<len(rows)else end
   actual_gap+=(stop-r['observed'])*max(0,peak-r['visible_frontier'])/16000
  close(actual_gap,view['continuity']['total_gap_audio_seconds_x_wall_seconds'])
  for w in windows:
   i=w['row_index'];r=rows[i];before=rows[i-1];event=byrow[i]
   assert before['visible_frontier']==w['before_visible_frontier']and r['visible_frontier']==w['after_visible_frontier']
   expected={'compatible_boundary':'avoidable','refuted_boundary':'necessary','missing_boundary':'unknown'}[event['support_status']]
   assert w['classification']==expected and w['start']==r['observed']and w['restored']and not w['right_censored']and not w['boundary_truncated']
   restore_index,restore=next((j,x)for j,x in enumerate(rows[i+1:],i+1)if x['visible_frontier']>=before['visible_frontier'])
   assert restore['observed']==w['end'];close(w['end']-w['start'],w['observed_duration_seconds'])
   close(area(w['segments']),w['observed_same_root_area_audio_seconds_x_wall_seconds'])
   all_windows.append(dict(cell_id=cid,condition=c['condition'],repeat=c['repeat'],**w))
  q=native['quality'][0];target=normalize(spec['reference']);actual=normalize(q['final_text']);n=len(target);nedit=edits(target,actual)
  assert q['reference_characters']==n and q['character_edits']==nedit;close(q['CER'],nedit/n)
  assert q['final_text']==refs[sid,spec['frames']]['transcript']
  qq=dict(reference_characters=n,character_edits=nedit,CER=nedit/n,original_final_text_sha256=sha(q['final_text'].encode('utf8')))
  if sid in quality:assert quality[sid]==qq
  quality[sid]=qq
  record=dict(cell_id=cid,source_id=sid,condition=c['condition'],repeat=c['repeat'],offered_audio_s=spec['frames']/16000,offered_frontiers=len(frontiers),
   credit_audio_s=cross_audio['none'],D2_misses=cross['D2_only']+cross['both_miss'],C8_misses=cross['C8_only']+cross['both_miss'],
   worker_seconds=c['worker_ledger']['worker_seconds'],both_board_J=c['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'],
   dispatches=c['job_accounting']['dispatches'],total_gap=actual_gap,
   **{cls+'_withdrawals':sum(w['classification']==cls for w in windows)for cls in('avoidable','necessary','unknown')},
   **{cls+'_gap':area([s for w in windows if w['classification']==cls for s in w['segments']])for cls in('avoidable','necessary','unknown')},
   compatible=view['continuity']['compatible_ahead_applications'],compatible_preserved=view['continuity']['compatible_ahead_preserved'],
   cross={k:cross[k]for k in('D2_only','C8_only','both_miss','none')},cross_audio={k:cross_audio[k]for k in('D2_only','C8_only','both_miss','none')})
  records.append(record);cell_data[sid,c['repeat'],c['condition']]=dict(cell=c,rows=rows,events=events,windows=windows,origin=origin,frontiers=frontiers)
 totals={}
 numeric=[k for k in records[0]if k not in('cell_id','source_id','condition','repeat','cross','cross_audio')]
 for cond in CONDITIONS:
  own=[r for r in records if r['condition']==cond];t={k:sum(r[k]for r in own)for k in numeric};t['coverage_percent']=100*t['credit_audio_s']/t['offered_audio_s']
  t['cross']={k:sum(r['cross'][k]for r in own)for k in own[0]['cross']};t['cross_audio']={k:sum(r['cross_audio'][k]for r in own)for k in own[0]['cross_audio']}
  for key in('credit_audio_s','worker_seconds','both_board_J','offered_audio_s','offered_frontiers'):close(t[key],formal['condition_totals'][cond][key])
  for key in('avoidable_withdrawals','necessary_withdrawals','unknown_withdrawals'):assert t[key]==formal['condition_totals'][cond][key]
  close(t['total_gap'],formal['condition_totals'][cond]['total_gap_audio_seconds_x_wall_seconds'])
  t['restoration_ms']={cls:durations([w['observed_duration_seconds']for w in all_windows if w['condition']==cond and w['classification']==cls])for cls in('avoidable','necessary')}
  totals[cond]=t
 source_table=[]
 for sid in sorted(sources):
  row=dict(source_id=sid)
  for cond in CONDITIONS:
   own=[r for r in records if r['source_id']==sid and r['condition']==cond]
   row[cond]={k:sum(r[k]for r in own)for k in('credit_audio_s','D2_misses','C8_misses','avoidable_withdrawals','necessary_withdrawals','compatible')}
  source_table.append(row)
  for rep in(0,1):
   a=cell_data[sid,rep,'r1s0'];b=cell_data[sid,rep,'r1s1']
   for x,y in zip(a['frontiers'],b['frontiers']):
    if x['credit']!=y['credit']:flips.append(dict(source_id=sid,repeat=rep,frontier=x['frontier'],S0_D=x['D'],S1_D=y['D'],S0_C=x['C'],S1_C=y['C'],S1_minus_S0_credit_audio_s=(int(y['credit'])-int(x['credit']))*x['audio_seconds']))
 sid='MD68_38_5721_20170915091418';positive=[]
 for rep in(0,1):
  row=dict(repeat=rep)
  for cond in('r1s0','r1s1'):
   data=cell_data[sid,rep,cond];event=next(e for e in data['events']if e['new_canonical_frontier']==40000);i=event['row_index'];current=data['rows'][i];meta=current['view_reconciliation'];before=data['rows'][i-1]
   assert event['support_status']=='compatible_boundary'and meta['boundary_end_sha']==meta['actual_new_canonical_sha']==cutsha(refs[sid,40000])
   assert meta['before_root_sha']==cutsha(refs[sid,32000])and event['before_visible_frontier']==48000
   evidence=dict(cell_id=data['cell']['cell_id'],canonical_row_zero_based=i,canonical_perf=current['observed'],canonical_since_origin_s=current['observed']-data['origin'],
    previous_visible_frontier=before['visible_frontier'],after_visible_frontier=current['visible_frontier'],boundary_complete_state_sha256=meta['boundary_end_sha'],
    before_root_sha=meta['before_root_sha'],before_tip_sha=meta['before_tip_sha'],boundary_job_id=meta['boundary_job_id'],metadata_binding_checked=event['metadata_binding_checked'])
   if cond=='r1s0':
    window=next(w for w in data['windows']if w['row_index']==i);restore=next(r for r in data['rows'][i+1:]if r['visible_frontier']>=48000)
    assert before['private_job']==restore['private_job']and before['text']==current['text']==restore['text']
    evidence.update(removed_audio_seconds=.5,restored_perf=restore['observed'],restored_since_origin_s=restore['observed']-data['origin'],restoration_ms=1000*(restore['observed']-current['observed']),restoration_kind=restore['kind'],same_original_private_job=restore['private_job'],text_unchanged=True)
   else:assert current['visible_frontier']==48000 and current['private_job']==before['private_job']
   row[cond]=evidence
  assert all(row['r1s0'][k]==row['r1s1'][k]for k in('before_root_sha','before_tip_sha','boundary_complete_state_sha256','boundary_job_id'))
  positive.append(row)
 assert len(all_points)==1;point=all_points[0];assert point['classification']=='necessary'
 sid=point['source_id'];negative=dict(D2_missing=point,paired_same_refuted_boundary=[])
 for cond in('r1s0','r1s1'):
  d=cell_data[sid,1,cond];event=next(e for e in d['events']if e['new_canonical_frontier']==136000);r=d['rows'][event['row_index']];m=r['view_reconciliation'];readpoint=d['origin']+144000/16000+2
  assert event['support_status']=='refuted_boundary'and m['boundary_end_sha']!=m['actual_new_canonical_sha']==cutsha(refs[sid,136000])
  negative['paired_same_refuted_boundary'].append(dict(condition=cond,before_root_sha=m['before_root_sha'],before_tip_sha=m['before_tip_sha'],
   predicted_boundary_sha=m['boundary_end_sha'],actual_canonical_sha=m['actual_new_canonical_sha'],canonical_perf=r['observed'],D2_read_perf=readpoint,
   read_minus_clear_ms=1000*(readpoint-r['observed']),frontier_at_D2=next(r for r in reversed(d['rows'])if r['observed']<=readpoint)['visible_frontier']))
 old_lineage=read(E/'cpu_results/LINEAGE_OLD80_V2/SUMMARY.json');new_lineage=read(E/'cpu_results/LINEAGE_NEW24_V1/SUMMARY.json')
 assert new_lineage['completed_trials']==24 and new_lineage['counts']['all_dispatched_jobs']==sum(t['dispatches']for t in totals.values())==963
 quality_tot=dict(reference_characters=sum(q['reference_characters']for q in quality.values()),character_edits=sum(q['character_edits']for q in quality.values()),sources=4,all_six_outputs_per_source_equal_original_full_reference=True)
 quality_tot['CER']=quality_tot['character_edits']/quality_tot['reference_characters']
 result=dict(status='PASS_INDEPENDENT_READ_ONLY_RAW_CONSUMER_INTERPRETATION',posthoc_review_not_new_frozen_experiment=True,new_model_calls=0,GPU_calls=0,
  trials=24,sources=4,actual_duration_range_s=[min(s['duration']for s in sources.values()),max(s['duration']for s in sources.values())],
  totals=totals,source_table=source_table,quality=dict(pooled=quality_tot,per_source=quality),all_loss_windows=len(all_windows),all_restored=True,right_censored=0,boundary_truncated=0,
  positive_complete_state_witness=dict(source_id='MD68_38_5721_20170915091418',canonical_frontier=40000,visible_ahead_frontier=48000,paired_fresh_run_observations=positive),
  necessary_D2_timing_counterexample=negative,first_credit_flips=flips,
  lineage=dict(source_commit=new_lineage['source_commit'],new24_counts=new_lineage['counts'],new_per_condition={c:new_lineage['conditions'][c]for c in CONDITIONS},
   old_conservative_own_forecast_changed=old_lineage['conditions']['conservative_s1']['own_input_confirmed_and_own_forecast_changed_jobs'],old_conservative_dispatches=old_lineage['conditions']['conservative_s1']['all_dispatched_jobs']),
  interpretation=dict(primary_new_positive='Original C8 violation reduction plus selective elimination of compatible-view loss on independent original MD68 inputs.',
   C8_only_misses=0,additional_A2_credit_from_C8_only_fixes=0,
   S_first_credit_difference_audio_s=totals['r1s1']['credit_audio_s']-totals['r1s0']['credit_audio_s'],S_avoidable_D2_missing_audio_s=0.,
   no_multiple_second_native_avoidable_window_observed=True,no_RxS_interaction_estimated=True,
   total_gap_difference_is_not_same_as_avoidable_gap_difference=True,no_new_workload_energy_saving_vs_conservative=True))
 for name,value in(('INDEPENDENT_RESULT_INTERPRETATION.json',result),('INDEPENDENT_RESULT_INTERPRETATION.INPUTS.json',INPUTS)):
  with(OUT/name).open('x',encoding='utf8')as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
 print(json.dumps(dict(status=result['status'],trials=24,inputs=len(INPUTS),missing_points=len(all_points),windows=len(all_windows),quality=quality_tot)))

if __name__=='__main__':run()
