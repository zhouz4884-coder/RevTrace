"""Existing raw GPU evidence only: first legal visibility and batch completion."""
from collections import Counter,defaultdict
from pathlib import Path
import csv,hashlib,json,statistics,sys

B=Path(sys.argv[1]);O=B/'results/revtrace/online_admission_20261022'
D=O/'C2_RAW_DIAGNOSTIC_v1';D.mkdir(exist_ok=False)
index={r['path']:r for r in json.loads((O/'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())['files']}
def read(p):
 rel=p.relative_to(O).as_posix();raw=p.read_bytes();r=index[rel]
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return json.loads(raw)
def lines(p):
 rel=p.relative_to(O).as_posix();raw=p.read_bytes();r=index[rel]
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return [json.loads(x) for x in raw.splitlines()]
def write(name,rs):
 with (D/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def quant(xs,q):
 xs=sorted(xs);p=(len(xs)-1)*q;i=int(p)
 return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(p-i) if xs else None
fronts=[];batches=[];cells=[];faults=[]
try:
 for c in sorted((O/'formal_v1').iterdir()):
  if not c.is_dir() or not (c/'config.json').is_file():continue
  cfg=read(c/'config.json');method=cfg['online_study']['method']
  if method not in ['fine','dgft','standard']:continue
  es=lines(c/'events.jsonl');vs=lines(c/'consumer.jsonl');rs=lines(c/'worker_records.jsonl');ss=read(c/'sessions.json')
  t0=next(e['t0_perf'] for e in es if e['kind']=='run-start');byjob={r['job']['job_id']:r for r in rs}
  pubs=[e for e in es if e['kind'] in ['display','canonical-display']]
  pubindex={(e['session_id'],e['kind'],e['displayed']):e for e in pubs}
  rowbatch={};bs=defaultdict(list)
  for r in rs:
   z=r['result'];bs[r['job']['role'],z['started_perf'],z['completed_perf']].append(r)
  for bi,(key,group) in enumerate(bs.items()):
   role,start,end=key;mx=max(len(r['result']['token_ids']) for r in group)
   model_start=group[0]['result']['model_started_perf'];model_end=group[0]['result']['model_completed_perf']
   assert all(r['result']['model_started_perf']==model_start and r['result']['model_completed_perf']==model_end for r in group)
   for r in group:rowbatch[r['job']['job_id']]={'batch_index':bi,'physical_rows':len(group),'max_new_tokens':mx,
    'row_tokens':len(r['result']['token_ids']),'service_s':end-start,
    'ended_earlier_in_token_steps':r['result']['terminated_by_eos'] and len(r['result']['token_ids'])<mx}
   batches.append({'cell':c.name,'method':method,'role':role,'batch_index':bi,'physical_rows':len(group),
    'service_s':end-start,'model_s':model_end-model_start,'max_new_tokens':mx,
    'mean_new_tokens':statistics.mean(len(r['result']['token_ids']) for r in group),
    'rows_ending_before_batch_max':sum(r['result']['terminated_by_eos'] and len(r['result']['token_ids'])<mx for r in group),
    'all_rows_share_logged_completion':len({r['result']['completed_perf'] for r in group})==1,
    'token_step_early_stop_not_a_measured_saved_duration':True})
  cellfront=[]
  for s in ss:
   sid=s['session_id'];sv=[v for v in vs if v['session_id']==sid];sp=[p for p in pubs if p['session_id']==sid]
   sr=[r for r in rs if r['job']['session_id']==sid]
   injected=[r for r in sr if 'fault_actual_prompt_tokens' in r['job']]
   assert len(injected)==(1 if cfg['online_study']['traffic']=='F2' else 0)
   commits=[e for e in es if e['kind']=='commit' and e['session_id']==sid]
   for f in injected:
    j,z=f['job'],f['result'];later=[e for e in commits if t0+e['installed']>=z['completed_perf']]
    repaired=[r for r in sr if r['job']['role']=='proposal' and r['job']['enqueue_perf']>z['completed_perf']
              and r['job']['parent']>j['parent']]
    faults.append({'cell':c.name,'method':method,'source_id':s['source_id'],'fault_job_id':j['job_id'],
     'fault_target_audio_s':j['audio_end_sample']/16000,'fault_chunk':j['chunk_id'],
     'fault_parent':j['parent'],'fault_service_s':z['completed_perf']-z['started_perf'],
     'fault_audio_to_enqueue_s':j['enqueue_perf']-j['audio_ready_perf'],
     'fault_audio_to_received_s':z['received_perf']-j['audio_ready_perf'],
     'fault_new_tokens':len(z['token_ids']),
     'next_canonical_install_after_fault_done_s':t0+later[0]['installed']-z['completed_perf'] if later else None,
     'first_new_parent_proposal_enqueue_after_fault_done_s':min(r['job']['enqueue_perf'] for r in repaired)-z['completed_perf'] if repaired else None})
   total=round(s['duration']*16000);before=0
   for q in list(range(32000,total,32000))+[total]:
    rel=s['offset']+q/16000
    first=min((v for v in sv if v['valid_visible_frontier']>=q),key=lambda v:v['observed'])
    pe=pubindex[sid,first['source_kind'],first['server_time']];jr=byjob[pe['job_id']];j,z=jr['job'],jr['result']
    bat=rowbatch[j['job_id']]
    proposals=[p for p in sp if p['kind']=='display' and p['audio_end_sample']>=q and p['displayed']<=first['observed']]
    blocked=[]
    for p in proposals:
     match=[v for v in sv if v['source_kind']=='display' and v['server_time']==p['displayed']]
     if not match or all(v['valid_visible_frontier']<q for v in match):blocked.append(p)
    row={'cell':c.name,'method':method,'traffic':cfg['online_study']['traffic'],'load':c.name.split('-')[1],
     'source_id':s['source_id'],'frontier_sample':q,'release_s':rel,'audio_seconds':(q-before)/16000,
     'display_s':first['observed']-rel,'first_legal_view_kind':first['source_kind'],'first_job_id':j['job_id'],
     'target_lookahead_audio_s':j['audio_end_sample']/16000-q/16000,
     'job_audio_to_enqueue_s':j['enqueue_perf']-j['audio_ready_perf'],
     'enqueue_to_start_s':z['started_perf']-j['enqueue_perf'],'worker_service_s':z['completed_perf']-z['started_perf'],
     'completion_to_receive_s':z['received_perf']-z['completed_perf'],
     'receipt_to_consumer_s':first['observed_perf']-z['received_perf'],
     'raw_provisional_before_legal_view_count':len(proposals),'incompatible_or_stale_prior_provisional_count':len(blocked),
     'first_view_tentative_invalidated':first['tentative_invalidated'],
     'physical_batch_rows':bat['physical_rows'],'row_new_tokens':bat['row_tokens'],'batch_max_new_tokens':bat['max_new_tokens'],
     'ends_before_batch_max':bat['ended_earlier_in_token_steps']}
    assert abs(sum(row[k] for k in ['target_lookahead_audio_s','job_audio_to_enqueue_s','enqueue_to_start_s','worker_service_s','completion_to_receive_s','receipt_to_consumer_s'])-row['display_s'])<1e-6
    assert min(row[k] for k in ['target_lookahead_audio_s','job_audio_to_enqueue_s','enqueue_to_start_s','worker_service_s','completion_to_receive_s','receipt_to_consumer_s'])>=-1e-6
    fronts.append(row);cellfront.append(row);before=q
  misses=[r for r in cellfront if r['display_s']>2]
  cells.append({'cell':c.name,'method':method,'load':c.name.split('-')[1],'traffic':cfg['online_study']['traffic'],
   'frontiers':len(cellfront),'miss_frontiers':len(misses),'miss_audio_s':sum(r['audio_seconds'] for r in misses),
   'first_views_provisional':sum(r['first_legal_view_kind']=='display' for r in cellfront),
   'first_views_canonical':sum(r['first_legal_view_kind']=='canonical-display' for r in cellfront),
   'miss_first_views_provisional':sum(r['first_legal_view_kind']=='display' for r in misses),
   'miss_first_views_canonical':sum(r['first_legal_view_kind']=='canonical-display' for r in misses),
   'miss_with_prior_incompatible_provisional':sum(r['incompatible_or_stale_prior_provisional_count']>0 for r in misses),
   'miss_first_job_shorter_than_batch':sum(r['ends_before_batch_max'] for r in misses),
   'miss_shorter_batch_audio_s':sum(r['audio_seconds'] for r in misses if r['ends_before_batch_max']),
   'consumer_invalidated_views':sum(v['tentative_invalidated'] for v in vs),
   'private_retention_proofs':sum(e['kind']=='private-continuity-proof' for e in es),
   'private_retention_pass':sum(e['kind']=='private-continuity-proof' and e['eligible'] for e in es),
   'obsolete_proposals':sum(e['kind']=='proposal-obsolete' for e in es),
   'rebases':sum(e['kind']=='proposal-rebase' for e in es)})
  print('RAW_C2_AUDITED',c.name,flush=True)
 assert len(cells)==36
 write('FIRST_LEGAL_VIEW.csv',fronts);write('PHYSICAL_BATCH_LENGTHS.csv',batches)
 write('CELL_VISIBILITY.csv',cells);write('FAULT_RESPONSE.csv',faults)
 summary={'status':'PASS_HASHED_RAW_C2_VISIBILITY_AND_BATCH_AUDIT','cells':len(cells),
  'common_frontiers':len(fronts),'fault_events':len(faults),'all_first_view_decompositions_match':True,
  'raw_files_verified_against_frozen_index':True,'new_model_calls':0,'existing_result_bytes_modified':False,
  'scope':'posthoc observation; token-step completion opportunity is not measured saved time or a new serving result',
  'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (D/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
except BaseException as e:
 (D/'STOP.json').write_text(json.dumps({'error':repr(e),'original_raw_unchanged':True})+'\n');raise
