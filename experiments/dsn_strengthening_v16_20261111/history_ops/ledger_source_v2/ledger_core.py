"""Complete-job resource composition, observed overlap bounds, not causal savings."""
from collections import Counter,defaultdict
import hashlib,json
from pathlib import Path

def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def overlap(begin,end,cut):return max(0.0,min(end,cut)-begin)
def proxy(parent_install,model_begin,model_end,worker_end):return parent_install+(model_end-model_begin)-worker_end
def indexed(rows,key='job_id'):
 result={}
 for row in rows:
  if row[key] in result:raise ValueError('duplicate identity: '+str(row[key]))
  result[row[key]]=row
 return result
def read(spec,lines=False):
 raw=Path(spec['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==spec['sha256']
 return [json.loads(x) for x in raw.decode('utf8').splitlines() if x.strip()] if lines else json.loads(raw)

def analyze(cfg,out):
 jobs_out=[];cell_out=[];late=[]
 for cell in cfg['cells']:
  data={name:read(spec,name in ('events','native_jobs')) for name,spec in cell['files'].items()}
  original=data['config'];assert original['cell_id']==cell['cell_id'] and original['settings']['source_commit']==cfg['measured_neural_commit']
  assert data['summary']['source_commit']==cfg['measured_neural_commit'] and data['gate']['status']=='PASS_ACTUAL_NATIVE_SERVICE_EXECUTION'
  events=data['events'];dispatch=indexed([e for e in events if e['kind']=='dispatch'])
  assert list(dispatch.values())==data['dispatches']
  terminals=indexed([r for r in data['native_jobs'] if r['kind']=='completed'])
  installs=indexed([e for e in events if e['kind']=='canonical_install'])
  ledger=data.get('ledger',dict(promotions=[],discarded=[],abandoned=[]))
  abandoned=indexed(ledger['abandoned']);discarded=indexed(ledger['discarded']);promotions=indexed(ledger['promotions'])
  abandon_events=indexed([e for e in events if e['kind']=='abandoned'])
  assert set(abandoned)==set(abandon_events)
  assert not (set(terminals)&set(abandoned)) and set(installs)<=set(terminals)
  assert set(discarded)<=set(terminals)-set(installs)
  assert set(promotions)<=set(installs)
  for jid,r in terminals.items():
   d=dispatch[jid];rec=r['record'];assert r['source_id']==d['source_id'] and r['dispatch_epoch']==d['dispatch_epoch']
   assert d['start_sha']==rec['start_state']==digest(r['start']) and rec['end_state']==digest(r['end'])
   assert rec['model_start']<=rec['model_end']<=rec['worker_job_end_perf'] and rec['worker_job_begin_perf']<=rec['model_start']
   assert abs(rec['model_seconds']-(rec['model_end']-rec['model_start']))<1e-8
  sha_to_selected={terminals[j]['record']['end_state']:j for j in installs}
  fault={e['job_id'] for e in events if e['kind'] in ('failed','faulted') and e.get('job_id') in dispatch}
  suppressed={e['job_id'] for e in events if 'suppressed' in e['kind'] and e.get('job_id') in dispatch}
  completed_ready=set(terminals)-set(installs)-set(discarded)
  active=set(dispatch)-set(terminals)-set(abandoned)-fault-suppressed
  classes=dict(installed=set(installs),abandoned_before_C=set(abandoned),completed_discarded=set(discarded),
   completed_ready_uninstalled=completed_ready,active_without_terminal=active,suppressed_before_execution=suppressed,fault_or_other=fault)
  assigned=set()
  for ids in classes.values():assert not (assigned&ids);assigned|=ids
  assert assigned==set(dispatch) and set(terminals)|set(abandoned)<=set(dispatch)
  counts={k:len(v) for k,v in classes.items()};counts['dispatches']=len(dispatch)
  assert not active and not completed_ready and not fault and not suppressed,'preserve unresolved final state before interpreting resource ratio'
  for jid,d in dispatch.items():
   state=next(k for k,ids in classes.items() if jid in ids)
   r=terminals.get(jid);a=abandoned.get(jid)
   row=dict(cell_id=cell['cell_id'],source_id=d['source_id'],arm=cell['arm'],repeat=cell['repeat'],job_id=jid,terminal_state=state,
    dispatch_perf=d['dispatched_perf'],birth_canonical_sha=d['birth_canonical_sha'],frozen_start_sha=d['start_sha'])
   if r:
    rec=r['record'];row.update(worker_reported_wall_s=rec['worker_job_wall_seconds'],worker_interval_s=rec['worker_job_end_perf']-rec['worker_job_begin_perf'],
     original_infer_wall_s=rec['model_seconds'],worker_begin=rec['worker_job_begin_perf'],worker_end=rec['worker_job_end_perf'],
     infer_begin=rec['model_start'],infer_end=rec['model_end'],native_model_evaluated=rec['native_model_evaluated'])
   else:
    assert a['asr_prefix_executed'] is True and a['learned_C_executed'] is False and a['C_U_completed'] is False
    assert a['proof']==abandon_events[jid]['proof'] and d['start_sha']==digest(a['start'])==a['proof']['expected_cut_sha']
    row.update(worker_reported_wall_s=a['worker_job_end_perf']-a['worker_job_begin_perf'],worker_interval_s=a['worker_job_end_perf']-a['worker_job_begin_perf'],
     original_infer_wall_s=None,ASR_prefix_executed=True,learned_C_executed=False,
     timer_missing_reason='abandon exception bypasses completed infer record; ASR already executed, cannot replace missing infer timer by0')
   if jid in promotions:
    p=promotions[jid];assert p['birth_canonical_sha']==d['birth_canonical_sha'] and p['actual_parent_sha']==d['start_sha']
    assert p['birth_epoch']==d['dispatch_epoch'] and p['source_id']==d['source_id']
    parent_id=sha_to_selected[p['actual_parent_sha']];parent=terminals[parent_id];parent_received=parent['received_perf'];parent_install=installs[parent_id]['observed']
    assert r['start']==parent['end'] and parent_received<=parent_install
    row.update(cross_version=p['birth_canonical_sha']!=p['actual_parent_sha'],promotion=True,parent_job_id=parent_id,
     parent_terminal_received=parent_received,parent_install_receipt=parent_install,
     worker_before_parent_lower_s=overlap(row['worker_begin'],row['worker_end'],parent_received),
     worker_before_parent_upper_s=overlap(row['worker_begin'],row['worker_end'],parent_install),
     infer_before_parent_lower_s=overlap(row['infer_begin'],row['infer_end'],parent_received),
     infer_before_parent_upper_s=overlap(row['infer_begin'],row['infer_end'],parent_install),
     immediate_fixed_infer_restart_proxy_s=proxy(parent_install,row['infer_begin'],row['infer_end'],row['worker_end']),
     parent_receipt_inside_infer=row['infer_begin']<=parent_received<=row['infer_end'],
     parent_install_inside_infer=row['infer_begin']<=parent_install<=row['infer_end'])
   if jid in discarded:
    proof=discarded[jid]['proof'];assert proof['expected_cut_sha']==d['start_sha'] and proof['kind']=='actual_canonical_disagrees_with_complete_start'
    parent_id=sha_to_selected[proof['actual_cut_sha']];parent=terminals[parent_id]
    assert parent['end']['frontier']==proof['witness_frontier']==r['start']['frontier'] and r['start']!=parent['end']
    asr=next(e for e in events if e['kind']=='asr_early' and e['job_id']==jid)
    hint=next(e for e in events if e['kind']=='known_invalid_C_skip_hint' and e['job_id']==jid)
    detail=dict(cell_id=cell['cell_id'],source_id=d['source_id'],repeat=cell['repeat'],job_id=jid,parent_job_id=parent_id,
     before_C_checkpoint_strictly_before_asr_emission=asr['produced_perf'],child_infer_begin=rec['model_start'],child_infer_end=rec['model_end'],
     parent_infer_end=parent['record']['model_end'],parent_terminal_received=parent['received_perf'],
     parent_install_receipt=installs[parent_id]['observed'],hint_observed=hint['observed'],
     parent_result_still_unfinished_at_checkpoint_upper_bound=parent['record']['model_end']>asr['produced_perf'],
     minimum_parent_result_lateness_s=parent['record']['model_end']-asr['produced_perf'],proof=proof)
    late.append(detail)
   jobs_out.append(row)
  cell_out.append(dict(cell_id=cell['cell_id'],arm=cell['arm'],source_id=cell['source_id'],repeat=cell['repeat'],terminal_conservation=counts,
   event_kinds=dict(Counter(e['kind'] for e in events)),native_job_row_kinds=dict(Counter(r['kind'] for r in data['native_jobs']))))
 categories={}
 selections=dict(promoted=[r for r in jobs_out if r.get('promotion')],abandoned=[r for r in jobs_out if r['terminal_state']=='abandoned_before_C'],
  discarded=[r for r in jobs_out if r['terminal_state']=='completed_discarded'])
 for name,rows in selections.items():
  categories[name]=dict(calls=len(rows),worker_reported_wall_s=sum(r['worker_reported_wall_s'] for r in rows),
   original_infer_wall_observed_s=sum(r['original_infer_wall_s'] for r in rows if r['original_infer_wall_s'] is not None),
   infer_timer_missing_calls=sum(r['original_infer_wall_s'] is None for r in rows))
 promoted=selections['promoted'];overlaps={k:sum(r[k] for r in promoted) for k in ('worker_before_parent_lower_s','worker_before_parent_upper_s','infer_before_parent_lower_s','infer_before_parent_upper_s','immediate_fixed_infer_restart_proxy_s')}
 for name,value in [('JOBS',jobs_out),('CELLS',cell_out),('LATE_DISCARD_TIMELINES',late)]:
  (out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
 return dict(status='PASS_FULL_JOB_BINDINGS_TERMINAL_CONSERVATION_AND_TIMER_SCOPES',cells=len(cell_out),categories=categories,
  promoted_overlap_bounds=overlaps,promoted_parent_receipt_inside_infer=sum(r['parent_receipt_inside_infer'] for r in promoted),
  promoted_parent_install_inside_infer=sum(r['parent_install_inside_infer'] for r in promoted),
  full_retained_to_invalid_worker_composition_ratio=categories['promoted']['worker_reported_wall_s']/(categories['abandoned']['worker_reported_wall_s']+categories['discarded']['worker_reported_wall_s']),
  terminal_totals={arm:dict(sum_counts) for arm in sorted({r['arm'] for r in cell_out}) for sum_counts in [sum((Counter(r['terminal_conservation']) for r in cell_out if r['arm']==arm),Counter())]},
  late_discard_checkpoint_findings=late,
  scope='Offline actual full-call composition and parent-receipt/install interval bounds; infer timers are synchronized engine.infer wall, abandoned ASR infer timers unknown; no causal delay saved or policy equivalence claim',new_model_calls=0)
