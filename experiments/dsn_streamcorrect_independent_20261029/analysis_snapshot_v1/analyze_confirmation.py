"""Independent saved-output CPU recount; no runtime/model imports or network."""
from __future__ import annotations
import argparse,collections,datetime,hashlib,json,math,os,pathlib,platform,subprocess,sys,traceback

RUNTIME='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
REFERENCE_RUNTIME=RUNTIME
ARMS=('two_full_early','two_full_spec_early')
STATE_FIELDS={'audio_segments','tokens','context','last_attend_frame','detected_language','initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript'}
def need(x,message):
 if not x:raise ValueError(message)
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def eq(a,b):return canonical(a)==canonical(b)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def finite(x):return x if math.isfinite(x) else None
def quantile(xs,q):
 xs=sorted(xs)
 if not xs:return math.inf
 position=(len(xs)-1)*q;i=int(position);j=min(i+1,len(xs)-1)
 return math.inf if math.isinf(xs[j]) else xs[i]+(xs[j]-xs[i])*(position-i)
def normalize(state,commit):
 need(set(state)==STATE_FIELDS,'missing/extra complete state field');s=json.loads(canonical(state))
 tag=s['contract']['stage_execution']
 need(eq(tag,dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype='float32',source_commit=commit)),'complete execution tag differs')
 return s

def recount(sources,rows,origin):
 frontiers=[]
 for source in sources:
  sid=source['source_id'];observed=[r for r in rows if r['source_id']==sid];need(observed,'no actual Consumer rows')
  need(all(a['observed']<=b['observed'] for a,b in zip(observed,observed[1:])),'Consumer time reversed');past=0
  for F in list(range(8000,source['frames'],8000))+[source['frames']]:
   offered=origin+F/16000
   d=next((r['observed']-offered for r in observed if r['observed']>=offered and r['visible_frontier']>=F),math.inf)
   c=next((r['observed']-offered for r in observed if r['observed']>=offered and r['certified_frontier']>=F),math.inf)
   frontiers.append(dict(source_id=sid,F=F,samples=F-past,audio_seconds=(F-past)/16000,D=finite(d),C=finite(c),dual_met=d<=2 and c<=8,EOS=F==source['frames']));past=F
 ds=[r['D'] if r['D'] is not None else math.inf for r in frontiers];cs=[r['C'] if r['C'] is not None else math.inf for r in frontiers]
 return dict(offered_frontiers=len(frontiers),offered_audio_seconds=sum(r['audio_seconds'] for r in frontiers),
  credit=sum(r['samples'] for r in frontiers if r['dual_met'])/16000,credit_samples=sum(r['samples'] for r in frontiers if r['dual_met']),D99=finite(quantile(ds,.99)),C99=finite(quantile(cs,.99)),C50=finite(quantile(cs,.5)),D50=finite(quantile(ds,.5)),
  D2_misses=sum(x>2 for x in ds),C8_misses=sum(x>8 for x in cs),missing_D=sum(math.isinf(x) for x in ds),missing_C=sum(math.isinf(x) for x in cs),
  whole_run_D2_C8_pass=quantile(ds,.99)<=2 and quantile(cs,.99)<=8,frontiers=frontiers)

def fidelity(sources,histories,wal,jobs,events,reference):
 jobs={r['job_id']:r for r in jobs};installs=[e for e in events if e['kind']=='canonical_install'];checked=0
 for source in sources:
  sid=source['source_id'];refs=[r for r in reference if r['source_id']==sid];actual=histories[sid];wals=[w for w in wal if w['source_id']==sid];chosen=[e for e in installs if e['source_id']==sid]
  need(len(actual)==len(wals)==len(chosen)==len(refs),'full task call count differs')
  previous=None
  for a,w,event,ref in zip(actual,wals,chosen,refs):
   job=jobs[event['job_id']];record=job['record'];need(a['F']==ref['end']==record['end'],'full task frontier differs')
   need(a['state_sha256']==digest(a['state'])==record['end_state'],'actual complete state hash differs')
   need(eq(a['state'],w['state']) and eq(a['state'],job['end']),'actual job/WAL/history disagree')
   need(eq(normalize(a['state'],RUNTIME),normalize(ref['original_full_cut'],REFERENCE_RUNTIME)),'complete original state differs')
   need(eq(a['token_ids'],ref['original_full_result']['token_ids']) and eq(record['token_ids'],a['token_ids']),'original returned IDs differ')
   need(eq(w['selected'],ref['original_full_result']['selected_correction']) and eq(record['selected_correction'],w['selected']),'complete original C differs')
   need(record['start_state']==digest(job['start']),'actual start binding differs')
   refstart=ref['original_full_start_cut']
   if previous is None:need(refstart['frontier']==0,'original reference did not start at genesis')
   else:need(eq(refstart,previous),'original reference feedback chain changed')
   need(eq(normalize(job['start'],RUNTIME),normalize(refstart,REFERENCE_RUNTIME)),'complete original input differs')
   previous=ref['original_full_cut'];checked+=1
 return checked

def mechanisms(jobs,events,ledger,dispatches,histories):
 byjob={r['job_id']:r for r in jobs};bydispatch={r['job_id']:r for r in dispatches};hist={r['F']:r for rows in histories.values() for r in rows}
 installed={byjob[e['job_id']]['record']['end']:e['observed'] for e in events if e['kind']=='canonical_install'}
 parentjobs={byjob[e['job_id']]['record']['end']:byjob[e['job_id']] for e in events if e['kind']=='canonical_install'}
 early={e['job_id']:e for e in events if e['kind']=='asr_early'};promotions=[];skips=[]
 for promotion in ledger.get('promotions',[]):
  job=byjob[promotion['job_id']];r=job['record'];parent=parentjobs[r['start']];p=parent['record'];t=installed[r['start']]
  need(promotion['birth_canonical_sha']==bydispatch[promotion['job_id']]['birth_canonical_sha'],'promotion rewrote birth')
  need(eq(job['start'],hist[r['start']]['state']),'promoted full input not actual Canon parent')
  promotions.append(dict(job_id=promotion['job_id'],start=r['start'],end=r['end'],birth_preserved=True,complete_input_equals_actual_parent=True,
   worker_active=r['worker_job_begin_perf']<t<r['worker_job_end_perf'],model_path_active=r['model_start']<t<r['model_end'],
   different_gpu=job['gpu']!=parent['gpu'],model_overlap=max(0,min(r['model_end'],p['model_end'])-max(r['model_start'],p['model_start'])),
   identity_end_differs=promotion['job_id'] in early and not eq(early[promotion['job_id']]['projection']['end'],job['end'])))
 for a in ledger.get('abandoned',[]):
  proof=a['proof'];need(proof['kind']=='actual_canonical_disagrees_with_complete_start','unexpected skip proof in fixed no-reset scope')
  need(proof['witness_frontier']==a['start']['frontier'] and proof['expected_cut_sha']==digest(a['start']),'skip not bound to actual full start')
  need(proof['actual_cut_sha']==hist[proof['witness_frontier']]['state_sha256'] and proof['actual_cut_sha']!=proof['expected_cut_sha'],'skip witness is not actual differing Canon')
  need(not a['learned_C_executed'] and not a['C_U_completed'] and not a['feedback_cut_emitted'] and 'end' not in a,'abandoned work emitted C/U cut')
  skips.append(dict(job_id=a['job_id'],start=a['start']['frontier'],target=a['target_end'],actual_direct_start_witness=True,no_C_U_or_cut=True))
 return dict(promotions=promotions,skips=skips,owned_promotions=len(promotions),physical_worker_active=sum(x['worker_active'] for x in promotions),
  actual_model_path_active=sum(x['model_path_active'] for x in promotions),actual_model_overlaps_parent=sum(x['model_overlap']>0 for x in promotions),
  promoted_with_own_end_prediction_different=sum(x['identity_end_differs'] for x in promotions),known_invalid_C_skips=len(skips),
  discarded_full_results=len(ledger.get('discarded',[])),completed_full_C_with_nonNone_selection=sum(r['record'].get('selected_correction') is not None for r in jobs),
  completed_full_buffer_reuse=sum(e['kind']=='canonical_install' and e.get('completed_buffer_reuse',False) for e in events),
  actual_completed_ASR=sum(r['record']['native_model_evaluated'] and not r['record'].get('candidate_handoff',False) for r in jobs),abandoned_ASR_prefixes=len(skips))

def pair_rows(cells):
 grouped=collections.defaultdict(dict)
 for c in cells:
  k=(c['source_id'],c['repeat']);need(c['arm'] not in grouped[k],'duplicate paired arm');grouped[k][c['arm']]=c
 pairs=[]
 for (sid,repeat),arms in sorted(grouped.items()):
  need(set(arms)==set(ARMS),'missing paired arm');base=arms[ARMS[0]];candidate=arms[ARMS[1]]
  need(base['primary_gpu']==candidate['primary_gpu'],'GPU role unmatched within pair')
  need(eq(base['settings'],candidate['settings']),'paired neural/input settings changed')
  need(abs(base['metrics']['offered_audio_seconds']-candidate['metrics']['offered_audio_seconds'])<1e-9,'offered denominator changed')
  need(abs(base['position']-candidate['position'])==1,'paired frozen execution order separated')
  bm=base['metrics'];cm=candidate['metrics'];transitions=collections.Counter()
  for a,b in zip(bm['frontiers'],cm['frontiers']):
   need(a['F']==b['F'] and a['audio_seconds']==b['audio_seconds'],'offered frontier mismatch')
   transitions[('hit' if a['dual_met'] else 'miss')+'->'+('hit' if b['dual_met'] else 'miss')]+=1
  pairs.append(dict(source_id=sid,repeat=repeat,primary_gpu=base['primary_gpu'],first_arm=base['arm'] if base['position']<candidate['position'] else candidate['arm'],
   offered_audio_seconds=bm['offered_audio_seconds'],conservative_credit=bm['credit'],fullspec_credit=cm['credit'],conservative_credit_samples=bm['credit_samples'],fullspec_credit_samples=cm['credit_samples'],credit_difference_samples=cm['credit_samples']-bm['credit_samples'],credit_difference=(cm['credit_samples']-bm['credit_samples'])/16000,
   C50_difference=None if bm['C50'] is None or cm['C50'] is None else cm['C50']-bm['C50'],D99_difference=None if bm['D99'] is None or cm['D99'] is None else cm['D99']-bm['D99'],
   conservative_D99=bm['D99'],fullspec_D99=cm['D99'],conservative_C99=bm['C99'],fullspec_C99=cm['C99'],
   conservative_joules=base['energy'],fullspec_joules=candidate['energy'],energy_reduction_fraction=(base['energy']-candidate['energy'])/base['energy'],
   deadline_transitions=dict(transitions),quality_equal=eq(base['quality'],candidate['quality'])))
 return pairs

def independent_sources(receipt,selection,appraisal,method):
 ids=[s['source_id'] for s in receipt['sources']];speakers=[s['speaker_id'] for s in receipt['sources']]
 need(len(ids)==len(set(ids))==len(speakers)==len(set(speakers))==4,'exactly four distinct acoustic source/speaker units required')
 need(ids==[g['initial_source_id'] for g in selection['selected']]==appraisal['source_ids'],'locked source order changed')
 need(speakers==[g['speaker_id'] for g in selection['selected']]==appraisal['speaker_ids'],'locked speaker order changed')
 need(not set(speakers)&set(selection['excluded_speakers']),'old development speaker leaked')
 need(method['method_source_commit']==receipt['method_source_commit']==appraisal['method_source_commit']==RUNTIME,'method changed after metadata selection')
 need(method['created_utc']<selection['selection_created_utc'],'method not frozen before new metadata')
 need(receipt['metadata_only_before_neural'] and selection['metadata_only_before_neural'],'selection not metadata first')
 need(all(s['technical_fallback_index']==0 for s in receipt['sources']),'initial locked sources not retained in final dataset')
 return dict(source_ids=ids,speaker_ids=speakers,acoustic_units=4,fresh_repeats_per_arm_source=2,within_source_fresh_pairs=8)

def direction(pairs,source_ids):
 totals={sid:0 for sid in source_ids};counts=collections.Counter()
 for p in pairs:
  need(p['source_id'] in totals,'unexpected acoustic source');totals[p['source_id']]+=p['credit_difference_samples'];counts[p['source_id']]+=1
 need(set(counts)==set(source_ids) and all(counts[sid]==2 for sid in source_ids),'two timing repeats do not create more acoustic units')
 positive=sum(x>0 for x in totals.values());total=sum(totals.values())
 return dict(total_paired_credit_difference_samples=total,total_paired_credit_difference_seconds=total/16000,
  source_two_repeat_differences_samples=totals,positive_acoustic_sources=positive,acoustic_sources=4,
  directional_confirmation=total>0 and positive>=3,preregistered_rule='total sample difference>0 AND >=3/4 speakers have positive two-repeat sum; not eight independent acoustic samples')

def quality_recount(source,histories,captured):
 text=histories[source['source_id']][-1]['state']['transcript'];norm=lambda t:''.join(c for c in t if not c.isspace())
 ref=norm(source['reference']);hyp=norm(text);previous=list(range(len(hyp)+1))
 for i,a in enumerate(ref,1):
  row=[i]
  for j,b in enumerate(hyp,1):row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
  previous=row
 actual=dict(source_id=source['source_id'],text=text,reference_characters=len(ref),character_edits=previous[-1])
 need(eq(captured,[actual]),'saved official-reference CER differs from independent full-text recount')
 return dict(**actual,CER=previous[-1]/len(ref) if ref else None,normalization='Unicode whitespace only, same frozen native contract; not a reproduction of author paper scoring protocol')

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 root=pathlib.Path(__file__).resolve().parent;config=json.loads(a.config.read_bytes());manifest=json.loads(a.manifest.read_bytes());commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 need(commit==manifest['source_commit']==config['analysis_source_commit'],'analysis source differs');need(not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip(),'analysis source dirty')
 need(set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines())=={r['path'] for r in manifest['files']},'manifest incomplete')
 for r in manifest['files']:need((root/r['path']).stat().st_size==r['bytes'] and sha(root/r['path'])==r['sha256'],'source bytes differ')
 a.out.mkdir(exist_ok=False)
 def put(n,x):(a.out/n).write_bytes(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False).encode())
 put('CONFIG.json',config);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),stdlib_CPU_only=True,model_imported=False,gpu_launched=False))
 put('RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=commit,source_manifest_sha256=sha(a.manifest),frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out/'CELLS.json'),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='independent CPU recount of bounded copies; remote raw paths remain in collection receipt'))
 inputs={}
 def load(path,jsonl=False):
  path=pathlib.Path(path);raw=path.read_bytes();inputs[str(path)]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  return [json.loads(z) for z in raw.splitlines() if z.strip()] if jsonl else json.loads(raw)
 try:
  controls=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root),'-p','test_*.py','-v'],cwd=root,capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES=''))
  (a.out/'CPU_CONTROLS.log').write_text(controls.stdout+controls.stderr,encoding='utf8');need(controls.returncode==0 and 'skipped=' not in controls.stderr,'CPU controls failed')
  bank=pathlib.Path(config['collection_root']);need(sha(bank/'COLLECTION_MANIFEST.json')==config['collection_manifest_sha256'],'collection receipt changed');receipt=load(bank/'COLLECTION_MANIFEST.json')
  need(receipt['all_bytes_equal'] and receipt['source_commit']==RUNTIME,'collection not byte-matched complete bdfa')
  for row in receipt['files']:need((bank/row['path']).stat().st_size==row['bytes'] and sha(bank/row['path'])==row['sha256'],'bounded input differs: '+row['path'])
  plan=load(config['campaign_plan']);need(sha(config['campaign_plan'])==config['campaign_plan_sha256'] and plan['source_commit']==RUNTIME,'frozen campaign differs')
  need(eq(plan,load(bank/'campaign/CONFIG.json')),'actual campaign plan differs');gate=load(bank/'campaign/GATE.json');need(gate['completed_cells']==gate['planned_cells']==16 and gate['all_full_task_fidelity_pass'],'campaign scope incomplete')
  reference=load(config['reference_details']);need(sha(config['reference_details'])==plan['reference_details_sha256'],'original full reference bytes differ')
  frozen={}
  for key in ('source_receipt','metadata_selection','method_freeze','appraisal','reference_gate'):
   frozen[key]=load(config[key]);need(sha(config[key])==config[key+'_sha256'],'frozen input differs: '+key)
  acoustic=independent_sources(frozen['source_receipt'],frozen['metadata_selection'],frozen['appraisal'],frozen['method_freeze'])
  need(len(reference)==config['expected_reference_calls']==68,'all68 original reference steps required')
  need(frozen['reference_gate']['status']=='PASS_ALL_LOCKED_NEW_SPEAKER_ORIGINAL_FULL_REFERENCE_CALLS' and frozen['reference_gate']['reference_details_sha256']==plan['reference_details_sha256'],'new original reference gate differs')
  need(frozen['reference_gate']['imported_model_runtime_commit']==RUNTIME,'new reference is not same complete frozen method')
  cells=[]
  for position,cell in enumerate(plan['cells']):
   d=bank/cell['cell_id'];cfg=load(d/'CONFIG.json');frozen=pathlib.Path(config['frozen_config_dir'])/pathlib.PurePosixPath(cell['config']).name
   need(sha(frozen)==cell['config_sha256'] and eq(load(frozen),cfg),'actual config changed');need(cfg['settings']['source_commit']==RUNTIME and len(cfg['settings']['sources'])==1,'unexpected source scope')
   sources=cfg['settings']['sources'];sid=sources[0]['source_id'];need(eq(sources[0],next(s for s in frozen['source_receipt']['sources'] if s['source_id']==sid)),'actual source object differs from locked receipt')
   rows=load(d/'consumer.jsonl',True);origin=load(d/'ORIGIN.json')['origin_perf'];jobs=load(d/'native_jobs.jsonl',True);events=load(d/'events.jsonl',True);hist=load(d/'CANONICAL_HISTORIES.json');wal=load(d/'canonical_wal.jsonl',True)
   checked=fidelity(sources,hist,wal,jobs,events,reference);metrics=recount(sources,rows,origin);actual=load(d/'PRIMARY_METRICS.json')
   for k,name in [('credit','dual_deadline_audio_credit_seconds'),('D99','primary_linear_all_offered_D99'),('C99','primary_linear_all_offered_C99'),('C50','primary_linear_all_offered_C50')]:
    need(metrics[k] is None and actual[name] is None or metrics[k] is not None and actual[name] is not None and abs(metrics[k]-actual[name])<1e-8,'original primary recount differs: '+name)
   summary=load(d/'SUMMARY.json');quality=quality_recount(sources[0],hist,summary['quality']);energy=load(d/'ENERGY.json')['service']['total_joules'];need(abs(summary['energy']['service']['total_joules']-energy)<1e-8,'energy summary differs')
   mechanism=mechanisms(jobs,events,load(d/'FULLSPEC_LEDGER.json') if cfg['arm']==ARMS[1] else {},load(d/'DISPATCHES.json'),hist)
   cells.append(dict(cell_id=cell['cell_id'],position=position,source_id=sid,repeat=cfg['repeat'],arm=cfg['arm'],primary_gpu=cfg['settings']['primary_gpu'],settings=cfg['settings'],metrics=metrics,quality=quality,energy=energy,full_fidelity_steps=checked,mechanisms=mechanism,
    consumer_Canon_with_ahead_private_view=sum(r['kind']=='canonical' and r['private_job'] is not None and r['visible_frontier']>r['certified_frontier'] for r in rows),content=load(d/'CONTENT.json')))
  need(len(cells)==16 and len({c['source_id'] for c in cells})==4,'expected 16 cells/four sources');pairs=pair_rows(cells);need(len(pairs)==8,'expected eight source/repeat pairs')
  need(sum(c['full_fidelity_steps'] for c in cells)==config['expected_full_fidelity_steps']==272,'all272 complete canonical results required')
  acoustic_summary=[]
  for sid in acoustic['source_ids']:
   cc=[c for c in cells if c['source_id']==sid];pp=sorted((p for p in pairs if p['source_id']==sid),key=lambda p:p['repeat'])
   need(len(cc)==4 and all(eq(c['quality'],cc[0]['quality']) for c in cc),'four repeated quality records differ for one acoustic source')
   acoustic_summary.append(dict(source_id=sid,speaker_id=next(s['speaker_id'] for s in frozen['source_receipt']['sources'] if s['source_id']==sid),
    quality_once_for_acoustic_source=cc[0]['quality'],repeat_credit_differences_samples=[p['credit_difference_samples'] for p in pp],
    two_repeat_credit_difference_samples=sum(p['credit_difference_samples'] for p in pp),
    two_repeat_credit_difference_seconds=sum(p['credit_difference_samples'] for p in pp)/16000,
    both_timing_pairs_positive=all(p['credit_difference_samples']>0 for p in pp),
    both_timing_pairs_nonnegative=all(p['credit_difference_samples']>=0 for p in pp)))
  for sid in {p['source_id'] for p in pairs}:need({p['repeat'] for p in pairs if p['source_id']==sid}=={0,1} and {p['primary_gpu'] for p in pairs if p['source_id']==sid}=={0,1},'same-source repeat/GPU counterbalance differs')
  aggregates={}
  for arm in ARMS:
   cc=[c for c in cells if c['arm']==arm];frontiers=[r for c in cc for r in c['metrics']['frontiers']]
   aggregates[arm]=dict(cells=len(cc),offered_frontiers=len(frontiers),offered_audio_seconds=sum(c['metrics']['offered_audio_seconds'] for c in cc),credit_samples=sum(c['metrics']['credit_samples'] for c in cc),credit=sum(c['metrics']['credit_samples'] for c in cc)/16000,service_joules=sum(c['energy'] for c in cc),whole_run_D2_C8_pass=sum(c['metrics']['whole_run_D2_C8_pass'] for c in cc),
    D2_misses=sum(c['metrics']['D2_misses'] for c in cc),C8_misses=sum(c['metrics']['C8_misses'] for c in cc),EOS_D2_misses=sum(r['EOS'] and (r['D'] is None or r['D']>2) for r in frontiers),nonEOS_D2_misses=sum(not r['EOS'] and (r['D'] is None or r['D']>2) for r in frontiers),
    full_fidelity_steps=sum(c['full_fidelity_steps'] for c in cc),reference_characters=sum(c['quality']['reference_characters'] for c in cc),character_edits=sum(c['quality']['character_edits'] for c in cc),C50_values=[c['metrics']['C50'] for c in cc],D99_values=[c['metrics']['D99'] for c in cc],C99_values=[c['metrics']['C99'] for c in cc],
    Canon_with_ahead_private_view=sum(c['consumer_Canon_with_ahead_private_view'] for c in cc),
    mechanism_counts={k:sum(c['mechanisms'][k] for c in cc) for k in ('owned_promotions','physical_worker_active','actual_model_path_active','actual_model_overlaps_parent','promoted_with_own_end_prediction_different','known_invalid_C_skips','discarded_full_results','completed_full_C_with_nonNone_selection','completed_full_buffer_reuse','actual_completed_ASR','abandoned_ASR_prefixes')})
  summary=dict(status='PASS_COMPLETE_16_CELL_INDEPENDENT_PAIRED_RECOUNT',analysis_source_commit=commit,runtime_source_commit=RUNTIME,cells=16,pairs=8,sources=4,all_original_full_C_ID_state_quality_preserved=all(p['quality_equal'] for p in pairs),aggregates=aggregates,acoustic_units=acoustic,preregistered_direction=direction(pairs,acoustic['source_ids']),
   paired_credit_wins=sum(p['credit_difference_samples']>0 for p in pairs),paired_credit_ties=sum(p['credit_difference_samples']==0 for p in pairs),paired_credit_losses=sum(p['credit_difference_samples']<0 for p in pairs),
   paired_C50_improvements=sum(p['C50_difference'] is not None and p['C50_difference']<0 for p in pairs),paired_energy_improvements=sum(p['energy_reduction_fraction']>0 for p in pairs),
   unique_acoustic_reference_characters=sum(s['quality_once_for_acoustic_source']['reference_characters'] for s in acoustic_summary),
   unique_acoustic_character_edits=sum(s['quality_once_for_acoustic_source']['character_edits'] for s in acoustic_summary),
   all_negative_points_and_EOS_preserved=True,speaker_disjoint_independent_confirmation=True,scope='four metadata-first speaker-disjoint acoustic sources with two paired fresh-process repeats and GPU role swap; no analysis model calls and no inference from eight pairs/frontiers as independent acoustic samples')
  for path,record in inputs.items():need(sha(path)==record['sha256'],'input mutated during recount: '+path)
  put('CELLS.json',cells);put('PAIRS.json',pairs);put('ACOUSTIC_SOURCE_SUMMARY.json',acoustic_summary);put('INPUT_MANIFEST.json',inputs);put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(summary,indent=2));return 0
 except BaseException:
  put('INPUT_MANIFEST.json',inputs);(a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');put('GATE.json',dict(status='FAIL_CONFIRMATION_CPU_RECOUNT_PRESERVED',analysis_source_commit=commit));raise

if __name__=='__main__':raise SystemExit(main())
