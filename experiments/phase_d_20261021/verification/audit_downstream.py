"""Independent end-to-end consumer/common-frontier audit; no scheduler calls."""
import csv,hashlib,json,math,re,statistics,sys,unicodedata
from collections import defaultdict
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';O=B/'results/revtrace/phaseD_20261021';S=P/'d1_v1';sys.path[:0]=[str(S/'src'),str(S/'scripts'),str(B/'projects/revtrace_phaseN_20261021')]
partial=sys.argv[2] if len(sys.argv)>2 else None
stage_only=bool(partial and partial.endswith('/*'))
from revtrace.dgft import digest_tokens
from transformers import AutoProcessor
from qwen_asr import parse_asr_output
tok=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).tokenizer
manifest=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text());reference={r['source_id']:r['reference'] for r in manifest['sessions']};new_ids=set(reference)
original=json.loads((B/'datasets/tc_live_20260906/manifest.json').read_text());reference.update({r['source_id']:r['reference'] for r in original['sessions']})
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def render(job,Z):
 raw=tok.decode(job['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
 if job['chunk_id']>=2 and raw:
  ids=tok.encode(raw);k=5
  while True:
   prefix=tok.decode(ids[:max(0,len(ids)-k)])
   if '\ufffd' not in prefix or k>=len(ids):break
   k+=1
 raw=prefix+tok.decode(Z,skip_special_tokens=True,clean_up_tokenization_spaces=False);_,text=parse_asr_output(raw,user_language=job['language'])
 return tok.encode(raw),text
def distance(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  out=[i]
  for j,y in enumerate(b,1):out.append(min(out[-1]+1,row[j]+1,row[j-1]+(x!=y)))
  row=out
 return row[-1]
def words(t):return re.findall(r"[a-z0-9']+",unicodedata.normalize('NFKC',t).lower())
def chars(t):return [c for c in unicodedata.normalize('NFKC',t).lower() if c.isalnum()]
def q99(xs):
 if not xs or any(x is None for x in xs):return None
 xs=sorted(xs);i=(len(xs)-1)*.99;lo=int(i);return xs[lo]+(xs[min(lo+1,len(xs)-1)]-xs[lo])*(i-lo)
def csvout(p,rs):
 if not rs:return
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
cells=[];source_rows=[];grids=[];errors=[];histories={};rawindex=[]
for stage in ['R2_pilot','R2_cost','R4_scout','R4_formal','R2_continuity','R2_strong_async','R2_transfer','R4_strict']:
 if partial and partial.split('/')[0]!=stage:continue
 for c in sorted((O/stage).iterdir()):
  if partial and not stage_only and partial!=stage+'/'+c.name:continue
  if not (c/'result.json').exists():continue
  cfg=json.loads((c/'config.json').read_text());res=json.loads((c/'result.json').read_text());ss=json.loads((c/'sessions.json').read_text());es=[json.loads(l) for l in (c/'events.jsonl').read_text().splitlines()];vs=[json.loads(l) for l in (c/'consumer.jsonl').read_text().splitlines()]
  records={}
  for line in (c/'worker_records.jsonl').open():
   x=json.loads(line);records[x['job']['job_id']]=x
  commits=[e for e in es if e['kind']=='commit'];pubs={(e['session_id'],e['version']):e for e in es if e['kind']=='canonical-display'}
  final_carrier=bool(cfg['authority_runtime'].get('render_contract'))
  if final_carrier:
   for worker in json.loads((c/'workers.json').read_text()):
    assert worker['warmup_policy']=='synthetic-zero-audio-not-a-serving-input'
    assert worker['warmup_audio_sha256']==hashlib.sha256(bytes(32000*4)).hexdigest()
  wal=Path(json.loads((c/'provenance.json').read_text())['durable_journal_path']);data=wal.read_bytes();pos=0;seq=0;previous='';wal_events={}
  while pos<len(data):
   n=int.from_bytes(data[pos:pos+4],'big');payload=data[pos+4:pos+4+n];h=hashlib.sha256(payload).digest();assert h==data[pos+4+n:pos+4+n+32];r=json.loads(payload);assert r['sequence']==seq and r['previous_sha256']==previous;seq+=1;previous=h.hex();pos+=n+36
   if r['kind']=='commit':wal_events[r['session_id'],r['parent_checkpoint_id']+1]=r['event']
  expected={};lastF=defaultdict(int);lastP=defaultdict(list)
  for e in commits:
   sid=e['session_id'];rr=records[e['job_id']];j,r=rr['job'],rr['result'];Pnew,text=render(j,e['segment_tokens']);key=sid,e['version']
   assert e['audio_start_sample']==lastF[sid] and j['prompt_tokens']==lastP[sid];lastF[sid]=e['audio_end_sample'];lastP[sid]=e['next_prompt_tokens']
   assert Pnew==e['next_prompt_tokens']==r['state_tokens'] and text==r['text']==pubs[key]['text']==wal_events[key]['committed_text']
   cert=e['certificate'];assert cert['display_sha256']==digest_tokens(e['segment_tokens']) and cert['feedback_state_sha256']==digest_tokens(Pnew) and cert['prompt_sha256']==digest_tokens(j['prompt_tokens'])
   if cfg['trusted_text_binding']:
    proof=wal_events[key]['text_binding'];assert proof['text_sha256']==hashlib.sha256(text.encode()).hexdigest();assert proof['render_inputs']['token_ids']==e['segment_tokens']
   expected[key]=(text,e['audio_end_sample']);assert pubs[key]['displayed']>=e['installed']
  # Rebuild each positive coordinator continuity witness independently.
  seq_by_enqueue={e['job_id']:i for i,e in enumerate(es) if e['kind']=='enqueue'}
  seq_by_received={e['job_id']:i for i,e in enumerate(es) if e['kind']=='executor-complete'}
  for i,e in enumerate(es):
   if e['kind']!='private-continuity-proof' or not e['eligible']:continue
   sid=e['session_id'];ver=e['canonical_version'];cmt=next(c for c in commits if c['session_id']==sid and c['version']==ver);path=e['witness'];assert path
   first=records[path[0]];assert first['job']['audio_end_sample']==cmt['audio_end_sample'] and first['result']['state_tokens']==cmt['next_prompt_tokens'] and first['job']['branch_generation']==e['branch_generation']
   last=first
   for jid in path[1:]:
    node=records[jid];assert node['job']['chunk_id']==last['job']['end_window'] and node['job']['prompt_tokens']==last['result']['state_tokens'];assert node['job']['branch_generation']==e['branch_generation'];last=node
   assert last['job']['end_window']==e['branch_chunk']
   pending=[r for jid,r in records.items() if r['job']['role']=='proposal' and r['job']['session_id']==sid and seq_by_enqueue[jid]<i<seq_by_received[jid]]
   assert len(pending)<=1
   for node in pending:assert node['job']['chunk_id']==last['job']['end_window'] and node['job']['prompt_tokens']==last['result']['state_tokens'] and node['job']['audio_end_sample']>cmt['audio_end_sample']
  for v in vs:
   if v['canonical_version']:
    text,F=expected[v['session_id'],v['canonical_version']];assert v['certified_text']==text and v['certified_frontier']==F
    if final_carrier:
     pub=pubs[v['session_id'],v['canonical_version']];assert v['canonical_epoch']==pub['contract_epoch']
     assert v['certified_transaction']==pub['transaction_id'] and v['contract_digest']==pub['contract_digest']
     assert v['certified_Z_sha256']==pub['canonical_Z_sha256'] and v['certified_P_sha256']==pub['canonical_projection_sha256']
     assert v['certified_text_sha256']==hashlib.sha256(text.encode()).hexdigest()
   assert v['observed']>=v['server_time']-1e-6 and not v['joined_suffix']
   if final_carrier:assert v['observed_perf']>=v['consumer_received_perf'] and v['view_application_seconds']>=0
  for sid in [s['session_id'] for s in ss]:
   values=[v['canonical_version'] for v in vs if v['session_id']==sid];assert values==sorted(values)
  # Independent forward reachability for every retained whole provisional view.
  for v in vs:
   if not v['compatible_provisional_retained']:continue
   sid=v['session_id'];ver=v['canonical_version'];F=v['certified_frontier'];P0=next(e['next_prompt_tokens'] for e in commits if e['session_id']==sid and e['version']==ver)
   reachable={(round(F/32000),digest_tokens(P0),None)};accepted=[]
   prior=[e for e in es if e['kind']=='display' and e['session_id']==sid and e['displayed']<=v['server_time']+1e-8 and e['audio_end_sample']>F]
   for e in sorted(prior,key=lambda e:e['audio_end_sample']):
    x=records[e['job_id']];j,r=x['job'],x['result'];gen=j['branch_generation']
    if any(k==j['chunk_id'] and h==digest_tokens(j['prompt_tokens']) and (g is None or g==gen) for k,h,g in reachable):
     reachable.add((j['end_window'],digest_tokens(r['state_tokens']),gen));accepted.append(e)
   assert any(e['audio_end_sample']==v['valid_visible_frontier'] and e['text']==v['visible_text'] for e in accepted),'Unproved provisional retention'
  qs=[];we=wn=ce=cn=0;english_ce=english_cn=0;seen_sources=set();temporary_terminal=[];reference_deviations=[]
  for s in ss:
   sid=s['session_id'];total=round(s['duration']*16000);prev=0
   sv=[v for v in vs if v['session_id']==sid];text=sv[-1]['certified_text'];ref=reference[s['source_id']];w=distance(words(ref),words(text)) if s['language']=='English' else None;n=len(words(ref)) if s['language']=='English' else 0;z=distance(chars(ref),chars(text));nz=len(chars(ref))
   if s['source_id'] not in seen_sources:
    if s['language']=='English':we+=w;wn+=n;english_ce+=z;english_cn+=nz
    else:ce+=z;cn+=nz
    seen_sources.add(s['source_id'])
   tmp=next((v for v in sv if v['source_kind']=='display' and v['valid_visible_frontier']>=total and v['certified_frontier']<total),None)
   tw=distance(words(ref),words(tmp['visible_text'])) if tmp and s['language']=='English' else None
   temporary_terminal.append({'source_id':s['source_id'],'available':tmp is not None,'word_errors':tw,'reference_words':n})
   source_rows.append({'stage':stage,'cell':c.name,'source_id':s['source_id'],'language':s['language'],'cluster':s['source_id'].split('-')[0] if s['source_id'] in new_ids else s['source_id'],'WER_errors':w,'reference_words':n,'CER_errors':z,'reference_chars':nz,'temporary_terminal_available':tmp is not None,'temporary_terminal_word_errors':tw,'final_canonical_text':text})
   for q in list(range(32000,total,32000))+[total]:
    t0=s['offset']+q/16000;ds=[v['observed'] for v in sv if v['valid_visible_frontier']>=q];cs=[e['installed'] for e in commits if e['session_id']==sid and e['audio_end_sample']>=q];qs.append({'display':min(ds)-t0 if ds else None,'commit':min(cs)-t0 if cs else None,'audio_seconds':(q-prev)/16000});prev=q
  wall=max(res['wall_seconds_including_arrival_and_drain'],max((v['observed'] for v in vs),default=0));pd=q99([q['display'] for q in qs]);pc=q99([q['commit'] for q in qs])
  for dd in [2,5,8]:
   for dc in [4,8,12,16]:
    good=sum(q['audio_seconds'] for q in qs if q['display'] is not None and q['commit'] is not None and q['display']<=dd and q['commit']<=dc);grids.append({'stage':stage,'cell':c.name,'display_deadline':dd,'commit_deadline':dc,'delivered_goodput_audio_s_per_wall_s':good/wall,'dual_P99_pass':pd is not None and pc is not None and pd<=dd and pc<=dc,'frontier_count_including_unfinished':len(qs)})
  h=hashlib.sha256(json.dumps(sorted([[e['session_id'],e['version'],e['audio_start_sample'],e['audio_end_sample'],e['segment_tokens'],e['next_prompt_tokens']] for e in commits])).encode()).hexdigest();histories[stage+'/'+c.name]=h
  renders=[e['host_cpu_wall_seconds'] for e in es if e['kind']=='render-checked'];duration=sum(s['duration'] for s in ss);wholeCPU={};cpu=c.parent/(c.name+'.CPU_IO.txt')
  if cpu.exists():
   for line in cpu.read_text().splitlines():
    if ': ' in line:
     k,val=line.strip().rsplit(': ',1)
     if k in ['User time (seconds)','System time (seconds)','Maximum resident set size (kbytes)','File system inputs','File system outputs']:wholeCPU[k]=float(val)
  row={'stage':stage,'cell':c.name,'rho':cfg['rho'],'arrival':cfg['arrival'],'sessions':len(ss),'independent_audio_sources':len(seen_sources),'independent_speakers':len({s['source_id'].split('-')[0] for s in ss}) if all(s['source_id'] in new_ids for s in ss) else None,'consumer':cfg.get('consumer_policy'),'async_implementation':cfg.get('async_implementation'),'reconciliation':cfg['proposal_reconciliation'],'barrier':cfg['proposal_barrier'],'binding':cfg['trusted_text_binding'],'retention_enabled':cfg.get('retain_verified_private_prefix',False),'xRT_server':res['audio_seconds_per_wall_second'],'xRT_to_final_consumer':duration/wall,'display_P99_consumer':pd,'commit_P99':pc,'dual_2_8_pass':pd is not None and pc is not None and pd<=2 and pc<=8,'GPU_J_per_audio_s':res['energy_joules_per_audio_second'],'WER':we/wn if wn else None,'CER':ce/cn if cn else english_ce/english_cn,'CER_scope':'Chinese' if cn else 'English characters','canonical_publications':len(commits),'server_rollback_events':sum(e.get('audio_rollback_samples',0)>0 for e in es if e['kind']=='canonical-display'),'consumer_rollback_events':sum(v['audio_rollback_samples']>0 for v in vs),'consumer_erased_characters':sum(v['erased_characters'] for v in vs),'retained_compatible_whole_views':sum(v['compatible_provisional_retained'] for v in vs),'coordinator_positive_continuity_witnesses':sum(e['kind']=='private-continuity-proof' and e.get('eligible',False) for e in es),'invalidations':sum(v['tentative_invalidated'] for v in vs),'render_wall_seconds_sum':sum(renders),'render_wall_p99':q99(renders),'consumer_CPU_seconds':res['consumer']['consumer_cpu_seconds'],'consumer_queue_max':res['consumer']['queue_max_depth'],'whole_cell_user_CPU_including_init':wholeCPU.get('User time (seconds)'),'whole_cell_system_CPU_including_init':wholeCPU.get('System time (seconds)'),'max_RSS_kbytes_including_init':wholeCPU.get('Maximum resident set size (kbytes)'),'whole_cell_filesystem_outputs':wholeCPU.get('File system outputs'),'WAL_bytes':wal.stat().st_size,'proposal_cap_events':sum(e['kind']=='executor-complete' and e.get('role')=='proposal' and e.get('hit_token_limit',False) for e in es),'authority_cap_events':sum(e['kind']=='executor-complete' and e.get('role')=='authority' and e.get('hit_token_limit',False) for e in es),'terminal_provisional_available_slots':sum(t['available'] for t in temporary_terminal),'terminal_provisional_total_slots':len(ss),'token_limit_events':res['token_limit_events'],'canonical_history_sha256':h}
  area=0.;lastview={};agearea=agewindow=agemax=0.;canon_age={}
  for v in vs:
   sid=v['session_id'];t=v['observed'];prior=lastview.get(sid,{'time':0.,'ever':0,'current':0});area+=(t-prior['time'])*max(0,prior['ever']-prior['current'])/16000
   if sid in canon_age:
    seen_at,last_at=canon_age[sid];agearea+=((t-seen_at)**2-(last_at-seen_at)**2)/2;agewindow+=t-last_at;agemax=max(agemax,t-seen_at);canon_age[sid]=(seen_at,t)
   if v['source_kind']=='canonical-display':canon_age[sid]=(t,t)
   lastview[sid]={'time':t,'ever':max(prior['ever'],v['valid_visible_frontier']),'current':v['valid_visible_frontier']}
  for sid,(seen_at,last_at) in canon_age.items():agearea+=((wall-seen_at)**2-(last_at-seen_at)**2)/2;agewindow+=wall-last_at;agemax=max(agemax,wall-seen_at)
  row.update(consumer_withdrawn_audio_wall_area=area,consumer_canonical_triggered_rollbacks=sum(v['source_kind']=='canonical-display' and v['audio_rollback_samples']>0 for v in vs),consumer_private_triggered_rollbacks=sum(v['source_kind']=='display' and v['audio_rollback_samples']>0 for v in vs),certified_view_age_mean_after_first_publication=agearea/agewindow if agewindow else None,certified_view_age_max_after_first_publication=agemax,canonical_correction_to_consumer_p99=q99([v['observed']-v['server_time'] for v in vs if v['source_kind']=='canonical-display']),baseline_valid=not(stage=='R4_formal' and cfg['consumer_policy'].startswith('localagreement')),strict_task_audio_warmup_isolation=final_carrier,coverage_note='partial stable words have no audio alignment; frontier is certified-F lower bound, not native LA SLO failure proof' if cfg['consumer_policy'].startswith('localagreement') else 'declared full-hypothesis/certified view input frontier; not recognition completeness')
  cells.append(row)
  print('audited',stage,c.name,flush=True)
A=O/('partial_independent_stage' if stage_only else 'partial_independent' if partial else 'independent');A.mkdir(exist_ok=True)
if stage_only:assert len(cells)==24 and partial=='R2_continuity/*','Expected the complete24-cell R2 stage'
elif partial:assert len(cells)==1,'Expected exactly one immutable completed cell'
else:
 expected_counts={'R2_pilot':2,'R2_cost':6,'R4_scout':10,'R4_formal':54,'R2_continuity':24,'R2_strong_async':6,'R2_transfer':6,'R4_strict':54}
 assert {s:sum(c['stage']==s for c in cells) for s in expected_counts}==expected_counts,'Missing/duplicate cell in formal scope'
csvout(A/'SERVICE_CELLS.csv',cells);csvout(A/'SOURCE_QUALITY.csv',source_rows);csvout(A/'DUAL_DEADLINE_GRID.csv',grids)
groups=defaultdict(list)
for c in cells:
 if c['stage'] in ['R4_formal','R4_strict','R2_continuity','R2_strong_async','R2_transfer']:groups[c['stage'] if c['stage'] not in ['R2_continuity','R2_strong_async'] else 'R2_matched',c['rho'],c['sessions'],c['arrival']].append(c)
agreements=[]
for key,rs in groups.items():agreements.append({'stage_group':key[0],'rho':key[1],'sessions':key[2],'arrival':key[3],'cells':len(rs),'unique_canonical_histories':len({r['canonical_history_sha256'] for r in rs}),'all_equal':len({r['canonical_history_sha256'] for r in rs})==1})
csvout(A/'CANONICAL_HISTORY_COMPARISONS.csv',agreements)
record={'status':'PASS_PARTIAL_COMPLETED_CELL_INDEPENDENT_AUDIT' if partial else 'PASS_INDEPENDENT_RENDER_WAL_CONSUMER_AND_COST_AUDIT','cells':len(cells),'partial_scope':partial,'not_a_complete_experiment_decision':bool(partial),'canonical_history_groups':agreements,'manuscript_edits':False,'no_suffix_joined':True,'source_quality_cluster':'speaker/source; repeated cells not independent audio','timing_scope':'consumer view-application complete time in final carrier, local FIFO. Legacy preliminary carrier used dequeue time and validation-complete owner receipt. Whole-cell GNU CPU includes model initialization.'}
(A/'AUDIT_REPORT.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
