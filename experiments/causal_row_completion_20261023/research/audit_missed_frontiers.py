"""Exact old-event joins with unknown old Row-final clocks left null."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,sys
B=Path(sys.argv[1]);OLD=B/'results/revtrace/online_admission_20261022'
O=B/'results/revtrace/row_completion_20261023';D=O/'missed_frontiers_v1';D.mkdir(exist_ok=False)
index={r['path']:r for r in json.loads((OLD/'delivery_evidence_v1/RAW_EVIDENCE_INDEX.json').read_text())['files']}
def read(p,lines=False):
 raw=p.read_bytes();r=index[p.relative_to(OLD).as_posix()]
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 return [json.loads(x) for x in raw.splitlines()] if lines else json.loads(raw)
rows=[];cells=0
for C in sorted((OLD/'formal_v1').iterdir()):
 if not C.is_dir() or not (C/'config.json').exists():continue
 cfg=read(C/'config.json');method=cfg['online_study']['method']
 if method not in ['fine','dgft','standard']:continue
 cells+=1;es=read(C/'events.jsonl',True);vs=read(C/'consumer.jsonl',True)
 rs=read(C/'worker_records.jsonl',True);ss=read(C/'sessions.json');byid={r['job']['job_id']:r for r in rs}
 t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
 commits={(e['session_id'],e['version']):e for e in es if e['kind']=='commit'}
 render={e['job_id']:e for e in es if e['kind']=='render-checked'}
 publications={(e['session_id'],e['kind'],e['displayed']):e for e in es if e['kind'] in ['display','canonical-display']}
 wal={}
 for e in es:
  if e['kind'] in ['wal-owner-start','wal-owner-complete']:
   for jid in e['job_ids']:wal.setdefault(jid,{})[e['kind']]=e['time']
 for s in ss:
  sid=s['session_id'];sv=[v for v in vs if v['session_id']==sid];cs=[e for (session,_),e in commits.items() if session==sid]
  total=round(s['duration']*16000);before=0
  for q in list(range(32000,total,32000))+[total]:
   release=s['offset']+q/16000
   first=min((v for v in sv if v['valid_visible_frontier']>=q),key=lambda v:v['observed'])
   committed=min(e['installed'] for e in cs if e['audio_end_sample']>=q)
   dp=first['observed']-release;cp=committed-release
   if dp<=2 and cp<=8:before=q;continue
   pub=publications[sid,first['source_kind'],first['server_time']];r=byid[pub['job_id']];j,z=r['job'],r['result']
   current=commits.get((sid,first['canonical_version']));birth=commits.get((sid,j['parent']))
   rd=render[j['job_id']];w=wal.get(j['job_id'],{})
   row={'cell':C.name,'method':method,'load':C.name.split('-')[1],'traffic':cfg['online_study']['traffic'],
     'source_id':s['source_id'],'frontier_sample':q,'audio_seconds':(q-before)/16000,'release_s':release,
     'display_delay_s':dp,'commit_delay_s':cp,'first_view_kind':first['source_kind'],'job_id':j['job_id'],
     'birth_parent':j['parent'],'birth_parent_ready_s':birth['installed'] if birth else 0.,
     'consumer_canonical_parent':first['canonical_version'],'consumer_parent_ready_s':current['installed'] if current else 0.,
     'job_target_audio_release_s':j['audio_ready_perf']-t0,'enqueue_s':j['enqueue_perf']-t0,
     'worker_started_s':z['started_perf']-t0,'GPU_model_started_s':z.get('model_started_perf',0)-t0 if z.get('model_started_perf') else None,
     'row_complete_s_UNKNOWN':None,'GPU_model_batch_completed_s':z.get('model_completed_perf',0)-t0 if z.get('model_completed_perf') else None,
     'old_batch_result_complete_s':z['completed_perf']-t0,'worker_message_send_s_UNKNOWN':None,
     'owner_received_s':z['received_perf']-t0,'render_checked_event_upper_s':rd['time'],
     'render_host_wall_s':rd['host_cpu_wall_seconds'],'WAL_owner_started_s':w.get('wal-owner-start'),
     'WAL_owner_completed_s':w.get('wal-owner-complete'),'WAL_install_s':committed if j['role']=='authority' else None,
     'consumer_applied_s':first['observed'],'individual_terminal_not_inferred_from_token_count':True,
     'parent_wait_batch_wait_WAL_may_overlap_not_additive_causes':True}
   rows.append(row);before=q
assert cells==36
with (D/'MISSED_FRONTIERS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
out={'status':'PASS_ALL36_OLD_MISSED_FRONTIER_EVENT_JOINS','cells':cells,'missed_frontiers':len(rows),
 'historical_row_terminal_and_worker_send_clocks_left_unknown':True,'new_GPU_calls':0,
 'not_a_proportional_or_additive_causal_explanation':True,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(D/'SUMMARY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
