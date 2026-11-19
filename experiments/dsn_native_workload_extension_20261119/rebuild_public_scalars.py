"""Rebuild primary/continuity/resource sums using PUBLIC files only, stdlib only."""
from pathlib import Path
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code/analysis_source'))
import continuity_readpoints as C
def read(name):return json.loads((ROOT/name).read_bytes())['payload']
def close(a,b,field):
 if a is None or b is None:assert a is b,(field,a,b)
 else:assert abs(a-b)<=1e-7*max(1,abs(a),abs(b)),(field,a,b)
def q99(values):
 a=sorted(math.inf if x is None else x for x in values);position=(len(a)-1)*.99;i=int(position);j=min(i+1,len(a)-1)
 return math.inf if math.isinf(a[j])else a[i]+(a[j]-a[i])*(position-i)
def main():
 index=read('public_scalars/CELLS_INDEX_PUBLIC.json');expected=read('public_scalars/FINAL_718_PUBLIC.json');totals={k:dict(offered_audio_s=0.,offered_frontiers=0,credit_audio_s=0.,worker_seconds=0.,both_board_J=0.,D2_misses=0,C8_misses=0,whole_run_passes=0,total_withdrawals=0,avoidable_withdrawals=0,necessary_withdrawals=0,unknown_withdrawals=0,total_gap_audio_seconds_x_wall_seconds=0.,same_root_avoidable_gap_audio_seconds_x_wall_seconds=0.)for k in expected['condition_totals']};rp_by={k:[]for k in totals};inputs=[];recounted=[]
 for entry in index['cells']:
  file='public_scalars/'+entry['public_cell'];data=read(file);identity=data['identity'];cond=identity['condition'];sid=identity['source_id'];fs=data['frontiers'];rows=data['consumer_rows'];windows=data['observed_loss_windows'];events=data['canonical_support_events'];origin=data['origin_perf'];end=data['service_end_perf'];t=totals[cond]
  C.validate_rows(rows,sid,origin,end,identity['consumer_retain_views']);C.validate_windows(rows,events,windows,end)
  for f in fs:
   for key,column in [('D','visible_frontier'),('C','certified_frontier')]:
    actual=next((r['observed']-f['offer']for r in rows if r['source_id']==sid and r['observed']>=f['offer']and r[column]>=f['frontier']),None);close(actual,f[key],identity['cell_id']+'/'+key)
  offered=math.fsum(f['audio_seconds']for f in fs);credit=math.fsum(f['audio_seconds']for f in fs if f['D']is not None and f['C']is not None and f['D']<=2 and f['C']<=8)
  dmiss=sum(f['D']is None or f['D']>2 for f in fs);cmiss=sum(f['C']is None or f['C']>8 for f in fs)
  whole=all(f['D']is not None and f['C']is not None for f in fs)and q99([f['D']for f in fs])<=2 and q99([f['C']for f in fs])<=8
  ledger=data['worker_ledger'];worker=math.fsum(j['worker_wall_seconds']for j in ledger['per_job']);close(worker,ledger['worker_seconds'],'worker per-job sum')
  acc=data['job_accounting'];assert acc['dispatches']==sum(acc['counts'].values())==acc['partition_count'];assert acc['pending_jobs']==0 and acc['disjoint']
  flat=[j for values in acc['terminal_job_ids'].values()for j in values];assert len(flat)==len(set(flat))==acc['dispatches']
  energy=data['energy']['origin_to_confirmed_physical_model_drain'];close(sum(energy['board_joules'].values()),energy['total_joules'],'both boards')
  gap=C.high_watermark_gap(rows,end);close(gap,data['continuity']['total_gap_audio_seconds_x_wall_seconds'],'actual high-water gap')
  for cls in C.CLASSES:
   own=[w for w in windows if w['classification']==cls];area=C.union_area([s for w in own for s in w['segments']]);close(area,data['continuity']['same_root_'+cls+'_gap_audio_seconds_x_wall_seconds'],cls+' window union')
  rp=C.credited_readpoints(fs,rows,windows,source_id=sid,origin=origin,end=end,initial_known=True,initial_visible=0);rp_by[cond].append(rp['summary'])
  for quality in data['quality']:close(quality['CER'],quality['character_edits']/quality['reference_characters'],'CER counts only')
  add=dict(offered_audio_s=offered,offered_frontiers=len(fs),credit_audio_s=credit,worker_seconds=worker,both_board_J=energy['total_joules'],D2_misses=dmiss,C8_misses=cmiss,whole_run_passes=int(whole),total_withdrawals=len(windows),total_gap_audio_seconds_x_wall_seconds=gap)
  for cls in C.CLASSES:add[cls+'_withdrawals']=sum(w['classification']==cls for w in windows)
  add['same_root_avoidable_gap_audio_seconds_x_wall_seconds']=C.union_area([s for w in windows if w['classification']=='avoidable'for s in w['segments']])
  for key,value in add.items():t[key]+=value
  recounted.append(dict(cell_id=identity['cell_id'],condition=cond,**add));inputs.append(dict(path=file,sha256=hashlib.sha256((ROOT/file).read_bytes()).hexdigest()))
 for cond,t in totals.items():
  target=expected['condition_totals'][cond]
  for key,value in t.items():close(value,target[key],cond+'/'+key)
  t['D2_readpoint']=C.aggregate_readpoints(rp_by[cond])
  for key,value in t['D2_readpoint'].items():
   if isinstance(value,dict):
    for k,v in value.items():close(v,target['D2_readpoint'][key][k],cond+'/'+key+'/'+k)
   else:close(value,target['D2_readpoint'][key],cond+'/'+key)
 # The full 718 table is an expected immutable derivative, not modified by this
 # script. Its original private SUMMARY SHA remains in FINAL_718_PUBLIC.json.
 result=dict(status='PASS_PUBLIC_ONLY_PRIMARY_GAPS_READPOINTS_RESOURCES_AND_QUALITY_COUNT_REBUILD',cells=len(recounted),
  condition_totals=totals,cells_recounted=recounted,inputs=inputs,neural_modules_loaded=[],
  scope='Rebuilds numeric geometry and count sums from public projections. State/text compatibility and edit-distance provenance remain private-source audits; their code and input hashes are supplied.')
 (ROOT/'PUBLIC_REBUILD_RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf8');print(json.dumps(dict(status=result['status'],cells=len(recounted))))
if __name__=='__main__':main()
