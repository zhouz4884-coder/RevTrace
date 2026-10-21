import csv,hashlib,json,statistics,subprocess,sys
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';O=B/'results/revtrace/phaseD_20261021';R=O/'R1_gpu';A=O/'R1_audit'
subprocess.run([sys.executable,str(P/'r0_audit_v2.py'),str(B),str(A),str(R)],check=True)
norm=list(csv.DictReader((A/'ROLLBACK_NORMALIZED.csv').open()));rows=[];history={};by={}
for c in sorted(R.iterdir()):
 if not (c/'result.json').exists():continue
 ev=[json.loads(x) for x in (c/'events.jsonl').read_text().splitlines()];cfg=json.loads((c/'config.json').read_text());result=json.loads((c/'result.json').read_text());cs=[e for e in ev if e['kind']=='commit']
 h=hashlib.sha256(json.dumps(sorted([[e['session_id'],e['version'],e['parent'],e['audio_start_sample'],e['audio_end_sample'],e['segment_tokens'],e['next_prompt_tokens']] for e in cs]),sort_keys=True).encode()).hexdigest();history[c.name]=h
 ns=[n for n in norm if n['cell']==c.name];repeat=int(c.name.rsplit('r',1)[1]);row={'cell':c.name,'rho':cfg['rho'],'hold':cfg['authority_result_delay_seconds'],'repeat':repeat,'commits':len(cs),'rollback_events':sum(int(n['rollback_events']) for n in ns),'erased_characters':sum(int(n['erased_characters']) for n in ns),'rollback_audio_seconds_sum':sum(float(n['rollback_audio_seconds_sum']) for n in ns),'withdrawn_audio_wall_area':sum(float(n['withdrawn_audio_wall_area']) for n in ns),'arrival_lag_area':sum(float(n['lag_time_area_until_last_publication']) for n in ns),'private_lead_area':sum(float(n['speculative_lead_area']) for n in ns),'xrt':result['audio_seconds_per_wall_second'],'canonical_history_sha256':h}
 row['rollback_per_commit']=row['rollback_events']/len(cs);rows.append(row);by[cfg['rho'],repeat,cfg['authority_result_delay_seconds']]=row
assert len(rows)==18
paired=[]
for rho in [1,3]:
 for repeat in range(3):
  base=by[rho,repeat,0]
  for hold in [.75,1.5]:
   r=by[rho,repeat,hold];paired.append({'rho':rho,'repeat':repeat,'hold':hold,'canonical_equal':r['canonical_history_sha256']==base['canonical_history_sha256'],'rollback_rate_delta':r['rollback_per_commit']-base['rollback_per_commit'],'lag_area_ratio':r['arrival_lag_area']/base['arrival_lag_area'],'lead_area_ratio':r['private_lead_area']/base['private_lead_area'] if base['private_lead_area'] else None,'withdrawn_area_delta':r['withdrawn_audio_wall_area']-base['withdrawn_audio_wall_area']})
for name,rs in [('R1_CELLS.csv',rows),('R1_PAIRS.csv',paired)]:
 with (A/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
record={'status':'COMPLETE_INDEPENDENT_EVENT_AUDIT','cells':18,'pairs':paired,'all_same_rho_canonical_equal':all(p['canonical_equal'] for p in paired),'law_claim':'NOT_ESTABLISHED_BY_RHO_COMPARISON; interpret actual intervention per repeat; no universal storm assertion','text_gap_independent_reason_to_continue_R2':True}
(A/'AUDIT_REPORT.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
