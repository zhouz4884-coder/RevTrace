"""Explicit public scalar extraction. No private JSON/state is copied wholesale."""
from pathlib import Path
import argparse,csv,hashlib,json,math,re,shutil,subprocess
E=Path(__file__).resolve().parents[1];OUT=E/'publication';INPUTS={};OMITTED=[]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def private(p):
 p=Path(p);name=str(p.relative_to(E)).replace('\\','/') if p.is_relative_to(E) else p.name
 return dict(private_input=name,bytes=p.stat().st_size,sha256=sha(p),payload_included=False)
def read(p):
 p=Path(p);INPUTS[str(p)]=private(p);return json.loads(p.read_bytes())
def write(name,obj):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def packet(name,p,payload,role='DERIVED_PUBLIC_SCALAR_NOT_RAW'):
 write(name,dict(schema=role,derived_from=private(p),payload=payload))
IDS={'source_id','speaker_id','raw_source_id','raw_speaker_id','cell_id','job_id','private_job','boundary_job_id','condition','arm','strategy','kind','stage','status','classification','stop_reason','support_status','source_commit','actual_NN_source_commit','runtime_execution_commit','generator_source_commit','version','publication_id','transition_id','schema','cohort','reference_kind','original_split'}
STRLIST={'conditions','source_ids','speaker_ids','neural_modules_imported','neural_modules_loaded'}
SENSITIVE={'text','final_text','reference','transcript','audio_buffer','token_ids','prefix_token_ids','initial_tokens','tokens','state','state_payload','cut','original_full_cut','original_full_start_cut','original_reference_start_state','view_reconciliation','reference_binding','genesis','waveform','samples','data_b64','payload_b64'}
def tree(x,key='',path=''):
 """Only called on named aggregate/scalar objects, never raw state/config."""
 if x is None or isinstance(x,bool):return x
 if isinstance(x,(int,float)):
  assert math.isfinite(x),path;return x
 if isinstance(x,str):
  if (key in IDS and re.fullmatch(r'[A-Za-z0-9_.:/@-]+',x))or re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',x):return x
  OMITTED.append(path);return None
 if isinstance(x,list):
  if not x:return []
  if key in ('worker_pids','actual_READY_pids')and all(type(v)is int and 0<v<2**32 for v in x):return list(x)
  if key=='actual_duration_range_s'and len(x)==2 and all(isinstance(v,(int,float))and math.isfinite(v)for v in x):return list(x)
  if all(isinstance(v,str)for v in x):
   if key in STRLIST:return [v for v in x if re.fullmatch(r'[A-Za-z0-9_.:/@-]+',v)]
   OMITTED.append(path);return None
  assert all(isinstance(v,dict)for v in x),('non-whitelisted numeric/payload array',path)
  return [tree(v,key,path+'[]')for v in x]
 assert isinstance(x,dict),path
 out={}
 for k,v in x.items():
  if k in SENSITIVE:OMITTED.append(path+'.'+k);continue
  if isinstance(v,str)and k not in IDS and not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',v):OMITTED.append(path+'.'+k);continue
  out[k]=tree(v,k,path+'.'+k)
 return out
def fields(x,names):return {k:x[k]for k in names if k in x}
SOURCE='source_id speaker_id raw_source_id raw_speaker_id frames duration duration_seconds audio_sha256 audio_bytes original_split no_concat no_trim no_resample'.split()
HEADER='sample_rate channels sample_width frames PCM_sha256'.split()
def source(x):
 z=fields(x,SOURCE);z['header']=fields(x.get('header',{}),HEADER)
 if 'archive_member'in x:z['archive_member_identity']=fields(x['archive_member'],['bytes','sha256'])
 return z
FRONT='source_id frontier is_EOS offer audio_seconds D C D2 C8'.split()
ROWS='kind source_id observed visible_frontier certified_frontier canonical_sha owner_epoch journal_sequence publication_id private_job recovery_replay transition_id consumer_retain_views'.split()
EVENT='after_tip_sha after_visible_frontier before_nonempty_visible_ahead before_root_sha before_tip_sha before_visible_frontier boundary_job_id compatible journal_sequence metadata_binding_checked new_canonical_frontier new_canonical_sha observed owner_epoch preserved_complete_tip retained_steps row_index source_id support_status'.split()
WINDOW='cell_id condition repeat after_visible_frontier before_visible_frontier boundary_truncated canonical_sha classification end initial_removed_audio_seconds observed_duration_seconds observed_same_root_area_audio_seconds_x_wall_seconds owner_epoch restored right_censored row_index source_id start stop_reason'.split()
READPOINT='cell_id condition repeat source_id frontier interval_start audio_seconds offer first_D first_C original_first_credit read_perf status actual_visible_frontier missing_audio_seconds missing_frontier_weight_audio_seconds same_root_classified_union_audio_seconds unclassified_beyond_root_windows_audio_seconds classifications matched_window_rows'.split()
def window(x):return dict(fields(x,WINDOW),segments=[fields(s,['source_id','start','end','low','high'])for s in x['segments']])
def lineage(x):
 z=fields(x,['status','source_commit','actual_NN_source_commit','completed_trials','counts','conditions','new_bank_scope','controls','model_calls','GPU_calls','neural_modules_loaded'])
 z['cells']=[fields(c,['cell_id','source_id','speaker_id','condition','repeat','status','counts'])for c in x.get('cells',[])]
 return tree(z)
def main():
 assert not OUT.exists(),'new candidate required; do not overwrite';OUT.mkdir()
 campaign=E/'gpu_results/SERVICE_LONG_NATURAL_V1';planpath=E/'plans/SERVICE_LONG_NATURAL_V1_PLAN.json';plan=read(planpath);campaign_summary=read(campaign/'SUMMARY.json')
 finalpath=E/'review/FINAL_RECOUNT_V1/SUMMARY.json';final=read(finalpath);assert len(campaign_summary['cells'])==final['trials']==24
 source_packet=[source(s)for s in plan['sources']]
 descriptor=dict(status='DERIVED_PUBLIC_NOT_EXECUTED_CONFIG',sources=source_packet,
  executed_plan=private(planpath),conditions=plan['conditions'],expected_trials=plan['expected_trials'],expected_source_count=plan['expected_source_count'],
  cadence=fields(plan['cadence'],['sample_rate_hz','input_release_seconds','full_step_samples']),original_D2_seconds=plan['original_D2_seconds'],original_C8_seconds=plan['original_C8_seconds'],
  warmup=fields(plan['warmup'],['source_id','fixed_start','fixed_end','discard_output','reset_service_genesis','original_reference_start_state_sha256']),
  source_identities={k:fields(plan[k],['source_commit','source_manifest_sha256','complete_files','clean'])for k in('driver','actual_NN','view_audit','production_support')},
  fixed_flags=fields(plan,['all_offered_including_partial_EOS','factorial_interaction_not_estimated','resource_drift_reject_or_retry','opportunity_nonzero_required','no_performance_quality_or_opportunity_gate']),
  scientific_protocol=private(E/'plans/SCIENTIFIC_PROTOCOL_V1.json'))
 packet('protocol/EXECUTED_PLAN_PUBLIC_DESCRIPTOR.json',planpath,descriptor,'DERIVED_PUBLIC_NOT_EXECUTED_CONFIG')
 protocol=read(E/'plans/SCIENTIFIC_PROTOCOL_V1.json')
 public_protocol=dict(experiment_id=protocol['experiment_id'],frozen_utc=protocol['frozen_utc'],conditions=protocol['conditions'],timing_repeats=protocol['timing_repeats'],
  source_selection=dict(corpus='MAGICDATA68',official_page='https://www.openslr.org/68/',official_test_URL=protocol['source_selection']['official_test_URL'],expected_archive_bytes=2201936013,
   minimum_frames=192000,maximum_frames=320000,target_frames=256000,maximum_speakers=4,speaker_order='lexicographic',tie_break='absolute_frame_distance_then_source_id',metadata_first=True,no_trim=True,no_concat=True,no_resample=True),
  contract=protocol['contract'],random_seed=protocol['randomization']['seed'],strategy_order='seeded_shuffle_then_reverse',primary_GPU_roles='repeat0_GPU0_repeat1_GPU1',
  all_outcomes_retained=True,zero_opportunity_retained=True,no_positive_effect_gate=True,no_complete_RxS_interaction=True)
 packet('protocol/SCIENTIFIC_PROTOCOL_PUBLIC_DESCRIPTOR.json',E/'plans/SCIENTIFIC_PROTOCOL_V1.json',public_protocol,'DERIVED_PUBLIC_NOT_EXECUTED_CONFIG')
 cells=[]
 for cell in campaign_summary['cells']:
  cid=cell['cell_id'];root=campaign/'cells'/cid;cfgp=root/'CONFIG.json';cfg=read(cfgp);summ=read(root/'SUMMARY.json');origin=read(root/'ORIGIN.json');end=read(root/'SERVICE_END.json')
  consumer_path=root/'consumer.jsonl';consumer=[json.loads(line)for line in consumer_path.read_bytes().splitlines()if line.strip()];INPUTS[str(consumer_path)]=private(consumer_path)
  rows=[fields(r,ROWS)for r in consumer]
  events=read(root/'view_audit/CANONICAL_SUPPORT_EVENTS.json');windows=read(root/'view_audit/OBSERVED_LOSS_WINDOWS.json')
  ledger=read(root/'WORKER_TIMER_LEDGER.json');accounting=read(root/'JOB_ACCOUNTING.json');view=read(root/'INDEPENDENT_VIEW_AUDIT.json')
  identity=fields(cell,['cell_id','source_id','speaker_id','condition','strategy','repeat','consumer_retain_views','version'])
  index=next(c for c in plan['cells']if c['cell_id']==cid);identity.update(primary_gpu=index['primary_gpu'],frozen_position=index['position'])
  led=fields(ledger,['status','worker_seconds','observed_infer_seconds','total_infer_seconds','missing_worker_timers','missing_infer_timers','unique_jobs','duplicate_terminals'])
  led['per_job']=[fields(j,['job_id','kind','source_id','worker_wall_seconds','observed_infer_wall_seconds'])for j in ledger['per_job']]
  acc=fields(accounting,['status','dispatches','counts','partition_count','disjoint','closed_drain_requested','closed_drain_terminal_sum','pending_jobs','promotion_events','unique_promoted_jobs','selected_promoted_jobs','promotions_are_not_terminal_category','Owner_admitted_ready_reuse','ready_reuse_positive_is_hard_gate','zero_ready_reuse_requires_timing_audit','zero_ready_reuse_establishes_policy_equivalence','UIR'])
  acc['error_count']=len(accounting.get('errors',[]));acc['terminal_job_ids']={k:list(v)for k,v in accounting['jobs'].items()}
  payload=dict(identity=identity,executed_config=private(cfgp),config_public_descriptor=dict(status='DERIVED_PUBLIC_NOT_EXECUTED_CONFIG',
    **fields(cfg,['arm','stage','cohort','repeat','position','maximum_service_seconds','maximum_owner_restarts','require_reference','condition','consumer_retain_views']),
    settings=fields(cfg['settings'],['backend','corrector_dtype','primary_gpu','max_ahead_frames','record_state_telemetry','record_resources'])),
   origin_perf=origin['origin_perf'],service_end_perf=end['service_end_perf'],frontiers=[fields(f,FRONT)for f in cell['primary']['frontiers']],
   consumer_rows=rows,canonical_support_events=[fields(v,EVENT)for v in events],observed_loss_windows=[window(w)for w in windows],
   continuity=tree(view['continuity']),consumer_support=tree(view['consumer_support']),
   worker_ledger=led,job_accounting=acc,energy=tree(cell['common_external_energy']),
   quality=[fields(q,['source_id','reference_characters','character_edits','CER'])for q in summ['quality']],
   integrity=tree(fields(summ['integrity'],['durable_frames_verified','complete_original_parent_cadence_records_verified','durable_canonical_steps','expected_canonical_steps','all_original_obligations_eventually_processed','accepted_frontiers','pending_accepted_uncertified_samples','unprocessed_all_offered_samples','observed_acknowledged_input_loss_samples','original_reference','local_reject_records','local_reject_canonical_mutations','owner_error_records','unexpected_owner_error_records'])),
   original_inputs=[private(p)for p in [cfgp,root/'SUMMARY.json',root/'ORIGIN.json',root/'SERVICE_END.json',consumer_path,root/'WORKER_TIMER_LEDGER.json',root/'JOB_ACCOUNTING.json',root/'INDEPENDENT_VIEW_AUDIT.json',root/'view_audit/CANONICAL_SUPPORT_EVENTS.json',root/'view_audit/OBSERVED_LOSS_WINDOWS.json']])
  packet('public_scalars/cells/'+cid+'.json',root/'EXTERNAL_FACTORIAL_AUDIT.json',payload)
  cells.append(dict(identity,public_cell='cells/'+cid+'.json',original_config_sha256=sha(cfgp),original_summary_sha256=sha(root/'SUMMARY.json')))
 packet('public_scalars/CELLS_INDEX_PUBLIC.json',campaign/'SUMMARY.json',dict(cells=cells,planned_trials=24,completed_trials=24,failed_attempts_count=len(campaign_summary['failed_attempts'])))
 # Only named aggregate objects are traversed; no raw state/config is supplied.
 aggregate_keys=[k for k in final if k not in('input_manifest','energy_window_bindings')]
 public_final=tree({k:final[k]for k in aggregate_keys});public_final['energy_window_bindings']=tree(final['energy_window_bindings'])
 public_final['input_manifest']=[dict(private_input=(str(k).replace(str(E),'E').replace('\\','/')),bytes=v['bytes'],sha256=v['sha256'],payload_included=False)for k,v in final['input_manifest'].items()]
 packet('public_scalars/FINAL_718_PUBLIC.json',finalpath,public_final)
 for filename,target,convert in [('D2_READPOINT_DETAILS.json','D2_READPOINT_DETAILS_PUBLIC.json',lambda a:[fields(r,READPOINT)for r in a]),('OBSERVED_LOSS_WINDOWS.json','LOSS_WINDOWS_PUBLIC.json',lambda a:[window(r)for r in a]),('QUALITY.json','QUALITY_PUBLIC.json',tree)]:
  p=E/'review/FINAL_RECOUNT_V1'/filename;packet('public_scalars/'+target,p,convert(read(p)))
 for phase in('LINEAGE_OLD80_V2','LINEAGE_NEW24_V1'):
  p=E/'cpu_results'/phase/'SUMMARY.json';packet('public_scalars/'+phase+'_PUBLIC.json',p,lineage(read(p)))
 independent=E/'review/INDEPENDENT_RESULT_INTERPRETATION.json'
 packet('public_scalars/INDEPENDENT_INTERPRETATION_PUBLIC.json',independent,tree(read(independent)))
 # Reference states, audio and labels stay private. The proof descriptor carries
 # their original hashes and only the completed original/refinement ledger.
 ref=E/'gpu_results/REFERENCE_LONG_V1';rp=ref/'SUMMARY.json';rx=read(rp)
 refdesc=tree(fields(rx,['status','actual_NN_source_commit','generator_source_commit','reference_only','actual_serving_runs','original_continuous_no_between_step_restore','restored_repeats_per_edge','ledger','expected_sources','completed_sources','expected_original_steps','all_original_full_state_C_IDs_equal']))
 refdesc['private_state_identities']=[private(ref/n)for n in('REFERENCE_DETAILS.json','GENESIS.json','REFERENCE_RECEIPT.json')]
 packet('protocol/REFERENCE_EXECUTION_PUBLIC_DESCRIPTOR.json',rp,refdesc)
 cpus={}
 for folder in sorted((E/'cpu_results').iterdir()):
  if not folder.is_dir():continue
  obj={}
  for name in('SUMMARY.json','GATE.json'):
   p=folder/name
   if not p.exists():continue
   x=read(p);allow=fields(x,['status','experiment_id','source_commit','code_commit','actual_NN_source_commit','summary_sha256','tests','controls','model_calls','GPU_calls','completed_trials','expected_trials','passed','failed','skipped','checks','models','files','verified_bytes'])
   # Never publish arbitrary per-model/fixture arrays from a CPU gate.
   for k in('checks','models','files'):
    if k in allow:allow[k+'_count']=len(allow.pop(k)) if isinstance(x[k],(list,dict))else x[k]
   obj[name]=dict(derived_from=private(p),scalars=tree(allow))
  if obj:cpus[folder.name]=obj
 write('protocol/CPU_CONTROL_PUBLIC_DESCRIPTORS.json',dict(schema='DERIVED_PUBLIC_CPU_GATE_DESCRIPTORS',payload=cpus))
 closure={}
 for p in sorted((E/'launch_ops').glob('*/RESOURCE_CLOSURE.json')):
  closure[str(p.parent.name)]=dict(derived_from=private(p),scalars=tree(read(p)))
 write('protocol/RESOURCE_CLOSURES_PUBLIC.json',dict(schema='DERIVED_PUBLIC_RESOURCE_CLOSURES',payload=closure))
 # Current frozen code plus all source-only history bundles. No .git is copied.
 roles=['prep_source','driver_source','analysis_source','lineage_audit_source','lineage_audit_source_v2','memory_transport_source','transport_source','readiness_source_v1']
 source_index=[]
 for role in roles:
  root=E/role
  if not(root/'.git').is_dir():continue
  git=lambda *a:subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
  assert not git('status','--porcelain','--untracked-files=all'),role
  paths=git('ls-files').splitlines();objects=git('rev-list','--objects','--all').splitlines()
  for item in objects:
   bits=item.split(' ',1)
   if len(bits)==2:
    name=bits[1]
    if not name:continue
    if not(Path(name).suffix in('.py','.md','.json')or Path(name).name in('.gitignore','.gitattributes')):assert git('cat-file','-t',bits[0])=='tree',(role,name)
  for name in paths:
   p=root/name;target=OUT/'code'/role/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  source_index.append(dict(role=role,source_commit=git('rev-parse','HEAD'),files=len(paths),history_objects_checked=len(objects)))
 for dirname in('source_manifests','source_bundles'):
  for p in sorted((E/dirname).iterdir()):
   assert p.is_file()and p.suffix in('.json','.bundle');target=OUT/dirname/p.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(p,target)
 write('SOURCE_CODE_INDEX.json',dict(schema='PUBLIC_SOURCE_ONLY_CODE_AND_HISTORY',sources=source_index))
 old='46f66eda0d32bb4c207dd9d57734a85ad0f19da5';base='https://github.com/zhouz4884-coder/RevTrace/blob/'+old+'/experiments/dsn_native_joint_retention_20261118/'
 deps=[]
 for label,commit,path in [('NN67','11453433c154aeffbff703c4c8dc9697421430e1','RUNTIME_SOURCE_V1.bundle'),('audit20','0571d51d85542e1eaf000be8082585a66e5978be','AUDIT_SOURCE_V1.bundle'),('readiness3','3fb','READINESS_SOURCE.bundle'),('support18','a13fa0a335529dc188f7e738877a3acd027ce4a7','PRODUCTION_SUPPORT_SOURCE.bundle')]:
  oldpath=E.parent/'dsn_native_joint_retention_20261118/packages'/path
  deps.append(dict(role=label,source_commit_or_prefix=commit,bundle_URL=base+'packages/'+path,bundle_sha256=sha(oldpath),existing_public_archive_commit=old))
 write('DEPENDENCIES.json',dict(schema='PUBLIC_EXISTING_COMPLETE_SOURCE_DEPENDENCIES',dependencies=deps))
 # Tables are regenerated from already-extracted scalars, never copied CSV.
 def table(name,rows,keys):
  p=OUT/'tables'/name;p.parent.mkdir(exist_ok=True)
  with p.open('w',encoding='utf8',newline='')as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:r.get(k)for k in keys}for r in rows])
 keys=['source_id','speaker_id','condition','offered_audio_s','offered_frontiers','credit_audio_s','coverage_percent','whole_run_passes','worker_seconds','both_board_J','D2_misses','C8_misses','avoidable_withdrawals','necessary_withdrawals','same_root_avoidable_gap_audio_seconds_x_wall_seconds']
 table('PER_SOURCE_PUBLIC.csv',public_final['source_condition_totals'],keys)
 table('CONDITION_TOTALS_PUBLIC.csv',[dict(condition=c,**r)for c,r in public_final['condition_totals'].items()],[k for k in keys if k not in('source_id','speaker_id')])
 table('ALL24_PUBLIC.csv',[dict(c,offered_audio_s=next(x for x in campaign_summary['cells']if x['cell_id']==c['cell_id'])['primary']['offered_audio_seconds'],credit_audio_s=next(x for x in campaign_summary['cells']if x['cell_id']==c['cell_id'])['primary']['dual_deadline_audio_credit_seconds'])for c in cells],['cell_id','source_id','speaker_id','condition','repeat','offered_audio_s','credit_audio_s','original_config_sha256','original_summary_sha256'])
 # Root's research report is a new public derivative with rewritten live links.
 report=E/'FINAL_REPORT.zh.md';body=report.read_text(encoding='utf8');mapping={'review/EXPERIMENT_DECISION.zh.md':'protocol/SCIENTIFIC_PROTOCOL_PUBLIC_DESCRIPTOR.json','review/FINAL_RECOUNT_V1/REPORT.zh.md':'public_scalars/FINAL_718_PUBLIC.json','FINAL_SUMMARY_PRIVATE.json':'public_scalars/FINAL_718_PUBLIC.json','FINAL_ALL24_CELLS.csv':'tables/ALL24_PUBLIC.csv','FINAL_PER_SOURCE.csv':'tables/PER_SOURCE_PUBLIC.csv','review/FINAL_RECOUNT_V1/QUALITY.json':'public_scalars/QUALITY_PUBLIC.json','review/FINAL_RECOUNT_V1/D2_READPOINT_DETAILS.json':'public_scalars/D2_READPOINT_DETAILS_PUBLIC.json','review/FINAL_RECOUNT_V1/OBSERVED_LOSS_WINDOWS.json':'public_scalars/LOSS_WINDOWS_PUBLIC.json','review/LINEAGE_OLD80_FINDINGS_V2.zh.md':'public_scalars/LINEAGE_OLD80_V2_PUBLIC.json','review/LINEAGE_NEW24_FINDINGS_V1.zh.md':'public_scalars/LINEAGE_NEW24_V1_PUBLIC.json'}
 def link(match):
  target=match.group(2)
  if target.startswith(('http://','https://')):return match.group(0)
  assert target in mapping,('unmapped report link',target);return '['+match.group(1)+']('+mapping[target]+')'
 mapping['review/INDEPENDENT_RESULT_INTERPRETATION.zh.md']='public_scalars/INDEPENDENT_INTERPRETATION_PUBLIC.json'
 body=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,body)
 (OUT/'REPORT_PUBLIC.zh.md').write_text('公开派生版（非原字节报告）。原始本地报告SHA256：`'+sha(report)+'`。所有下列本地链接已替换为公开标量派生与描述文件；私有原报告保持不变。\n\n'+body,encoding='utf8')
 exclusions=[private(p)for p in [E/'cpu_results/DATA_SELECTION_V2/ORIGINAL_SELECTION_BANK.json',E/'cpu_results/DATA_SELECTION_V2/SELECTED_TRANSCRIPTS.json',ref/'REFERENCE_DETAILS.json',ref/'GENESIS.json',ref/'REFERENCE_RECEIPT.json',finalpath,E/'review/FINAL_RECOUNT_V1/QUALITY.json',report]]
 exclusions.extend(private(p)for p in sorted((campaign/'cells').glob('*/GENESIS.json')))
 write('EXCLUDED_PRIVATE_INPUTS.json',dict(schema='PRIVATE_PAYLOAD_EXCLUSION_BOUNDARY_NOT_DOWNLOAD_MANIFEST',
  excluded_categories=['Original or encoded audio/WAV/model weights/cache','All official TRANS and human reference text','All model output text and token ID sequences','Complete state/cut/genesis/reference details, including embedded waveform buffers','Raw Consumer/WAL/owner/native job logs, private execution configs, PDFs/manuscripts'],
  identified_private_files=exclusions,private_recount_input_manifest=public_final['input_manifest'],
  guarantee='Raw private originals and local mirrors are retained unchanged on8TB/private storage. These hashes identify omitted inputs, not public downloadable payloads.'))
 write('PUBLIC_EXTRACTION_AUDIT.json',dict(schema='PUBLIC_EXTRACTION_AUDIT',original_final_summary=private(finalpath),original_report=private(report),
  omitted_freeform_or_payload_fields=sorted(set(OMITTED)),private_files_read=len(INPUTS),copied_corpus_files=0,copied_manuscript_files=0,executed_config_files_copied=0,
  output_origin='New dictionaries built from explicitly listed scalar structures; code/manifests/source-only bundles copied separately.'))
 # Deny full corpus strings in every candidate UTF8 payload; print no text.
 secrets=[]
 selected=read(E/'cpu_results/DATA_SELECTION_V2/ORIGINAL_SELECTION_BANK.json');secrets += [s['reference']for s in selected['sources']]
 secrets += [x['final_text']for x in final['original_native_quality']['per_source']]
 for p in OUT.rglob('*'):
  if not p.is_file()or p.suffix=='.bundle':continue
  raw=p.read_bytes()
  for text in secrets:
   if text and len(text)>8:assert text.encode('utf8')not in raw,('private corpus string leak',str(p.relative_to(OUT)))
 print(json.dumps(dict(status='BUILT_PUBLIC_SCALAR_PACKET_PENDING_REBUILD_QA',path=str(OUT),cells=len(cells),sources=len(source_packet))))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--private-evidence-root',type=Path,default=E);parser.add_argument('--output',type=Path)
 args=parser.parse_args();E=args.private_evidence_root.resolve();OUT=args.output.resolve()if args.output else E/'publication';main()
