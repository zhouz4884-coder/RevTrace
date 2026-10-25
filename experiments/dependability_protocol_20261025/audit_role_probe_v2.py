"""Independent actual-token/source/consumer/cost audit; no production owner import.

Frozen substring target kept. A stricter whole-word supplement is disclosed;
neither a carried prefix nor an injectedZ is labelled newly generated neuralZ.
"""
from pathlib import Path
from collections import Counter
import argparse,csv,hashlib,json,math,re
from audit_n5 import read,lines,sha,tokens,chain,edits,normalized
TARGET='violet saturn alder';PATTERN=re.compile(r'\bviolet\s+saturn\s+alder\b',re.I)
def marker(text):return dict(frozen_substring=TARGET in text.casefold(),exact_whole_words=bool(PATTERN.search(text)))
def original_rows(D):
 result={};batches={}
 for p in D.glob('worker-*-receipts.jsonl'):
  for x in lines(p):
   m=x['message']
   if x['kind']=='row-complete':
    assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest']
    r=json.loads(m['payload_json']);assert m['binding']['job_id']==r['job_id']
    result[r['job_id']]=(m,r)
   else:
    assert x['kind']=='batch-drained';a=x['physical_accounting'];assert dict(m['row_digests'])==a['row_receipt_digests']
    for jid,d in m['row_digests']:assert result[jid][0]['payload_digest']==d
    batches[m['batch_id']]=x
 return result,batches
def audit(D,harness='f0eaae69323fbaa10b3892761a8ac2c149181013'):
 cfg=read(D/'config.json');plan=read(D/'CASE_PLAN.json');r=read(D/'result.json');provenance=read(D/'provenance.json')
 assert cfg['operator_harness_commit']==plan['harness_commit']==provenance['harness_commit']==harness
 assert cfg['runtime_commit']==provenance['runtime_commit']=='408d75624104e7e11af3f0f2832263c632b10ed8'
 assert r['contract_digest']==sha(cfg) and cfg['rho']==1 and cfg['fine_seconds']==2
 assert cfg['trusted_text_binding'] and cfg['consumer_policy']=='two_lane'
 assert 'NOT_arrival_serving' in cfg['evidence_type']
 assert [w['gpu'] for w in read(D/'workers.json')]==[0,1]
 calls=read(D/'PHYSICAL_CALLS.json')['calls'];assert len(calls)==r['actual_operator_requests']
 original,batches=original_rows(D);assert len(original)==len(calls)
 transformed={};controlled=read(D/'CONTROLLED_TRANSFORMS.json') if (D/'CONTROLLED_TRANSFORMS.json').exists() else None
 if plan['traffic']=='coherent-proposer':
  assert controlled and len(controlled['transforms'])==1
  t=controlled['transforms'][0];job=t['job'];old=t['original_message'];new=t['corrupted_message']
  assert job['role']=='proposal' and job['end_window']==3 and job['chunk_id']==2
  assert old==original[job['job_id']][0] and old['binding']==new['binding']
  a=json.loads(old['payload_json']);b=json.loads(new['payload_json'])
  allowed={'token_ids','state_tokens','text','generated_tokens','hit_token_limit','terminated_by_eos'}
  assert all(b.get(k)==v for k,v in a.items() if k not in allowed)
  assert hashlib.sha256(new['payload_json'].encode()).hexdigest()==new['payload_digest']
  transformed[job['job_id']]=(new,b)
 else:assert not controlled and not r['literal_payload_injected']
 jobs={c['job']['job_id']:c['job'] for c in calls};received={c['job']['job_id']:c['result'] for c in calls}
 used_batches=set();actual_phases=[];lease_end={};original_neural_Z={};unchecked=[]
 for c in calls:
  j=c['job'];jid=j['job_id'];role=j['role'];native_message,native=original[jid];m=native['model_input_audit'];b=native_message['binding']
  assert native['runtime_digest']==j['runtime_digest']==sha(cfg[role+'_runtime'])
  assert j['contract_digest']==r['contract_digest'] and b==j['_delivery']['binding']
  assert j['audio_end_sample']>j['audio_start_sample'] and j['audio_ready_perf']<=j['enqueue_perf']<=native['started_perf']
  assert native['execution_context_audit']['executed_prompt_tokens']==j['prompt_tokens'] and not native['execution_context_audit']['fault_override']
  assert m['declared_prompt_tokens']==j['prompt_tokens'] and m['waveform_sha256']==j['prefix_audio_sha256']==native['prefix_audio_sha256']
  assert m['dtype']==('float16' if role=='proposal' else 'float32') and m['batch_rows']==1
  Z=native['token_ids'];eos=m['eos_token_ids'];stops=[i for i,z in enumerate(Z) if z in eos]
  assert stops==[len(Z)-1] or (not stops and len(Z)==256)
  message,body=transformed.get(jid,(native_message,native));actual=c['result']
  for k,v in body.items():assert actual[k]==v,(D.name,jid,k)
  assert actual['_row_receipt']['payload_sha256']==message['payload_digest']
  batch=batches[b['batch_id']]['physical_accounting'];assert b['batch_id'] not in used_batches;used_batches.add(b['batch_id'])
  assert set(batch['job_ids'])=={jid}
  if role in lease_end:assert j['enqueue_perf']>=lease_end[role],'physical worker reused before original drain'
  lease_end[role]=batch['batch_drained_perf']
  for phase in batch['phases']:
   assert phase['physical_batch_rows']==1 and phase['executed_job_ids']==[jid] and phase['completed_perf']>phase['started_perf']
   actual_phases.append(dict(role=role,purpose=c['purpose'],**phase))
  if role=='authority':
   p=native['online_verification'];assert p['target_identity']==sha({k:j[k] for k in ['session_id','parent','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','contract_digest','runtime_digest']})
   assert p['executed_prompt_tokens']==j['prompt_tokens'] and p['actual_audio_sha256']==j['prefix_audio_sha256'] and not p['context_override_used'] and p['dtype']=='float32'
   if p['fallback_used']:
    assert p['fallback_generated'] and jid in p['fallback_executed_job_ids']
    assert any(q['phase']=='fresh-FP32-fallback' for q in batch['phases'])
   elif p['mode']=='strict':
    assert p['predicted_token_ids']==j['candidate_token_ids']==native['token_ids']
    assert any(q['phase']=='correct-context-strict' for q in batch['phases'])
   else:
    assert p['mode']=='unprotected' and p['unsafe_no_FP32_selection'] and not batch['phases'];unchecked.append(jid)
  if role=='proposal' or any(q['phase']=='fresh-FP32-fallback' for q in batch['phases']):original_neural_Z[jid]=native['token_ids']
 assert len(batches)==len(used_batches)
 owner={x['job']['job_id']:x for x in lines(D/'worker_records.jsonl')};events=lines(D/'events.jsonl');consumer=lines(D/'consumer.jsonl')
 oracles=[c for c in calls if c['purpose']=='DIAGNOSTIC_ONLY_NO_ADMISSION'];assert len(oracles)==2
 assert set(owner)==set(jobs)-{c['job']['job_id'] for c in oracles}
 assert oracles[0]['result']['token_ids']==oracles[1]['result']['token_ids'] and oracles[0]['result']['state_tokens']==oracles[1]['result']['state_tokens']
 expected_unchecked=1 if plan['method']=='renderer_only' else 0;assert len(unchecked)==expected_unchecked==r['unchecked_candidate_installs']
 state=dict(F=0,P=(),version=0);nodes=set();committed=[];transaction=set();actual_illegal=0;first_private=None;first_selected=None
 lookup={(v['source_kind'],v['server_time']):v for v in consumer};assert len(lookup)==len(consumer)
 for e in events:
  kind=e['kind']
  if kind=='commit':
   j=jobs[e['job_id']];out=owner[e['job_id']]['result'];assert j['role']=='authority' and e['parent']==state['version']
   assert j['prompt_tokens']==list(state['P']) and e['audio_start_sample']==state['F']<e['audio_end_sample']
   assert e['segment_id'] not in transaction;transaction.add(e['segment_id'])
   assert e['segment_tokens']==out['token_ids'] and e['next_prompt_tokens']==out['state_tokens']
   assert e['certificate']['display_sha256']==tokens(out['token_ids']) and e['certificate']['feedback_state_sha256']==tokens(out['state_tokens'])
   state=dict(F=e['audio_end_sample'],P=tuple(e['next_prompt_tokens']),version=e['version']);committed.append(e)
   if e['audio_end_sample']==96000:first_selected=out
  if kind=='display':nodes.add(e['job_id'])
  if kind not in ['display','canonical-display']:continue
  v=lookup.get((kind,e['displayed']))
  if v is None:continue
  assert v['certified_frontier']==state['F'] and v['canonical_version']==state['version'] and v['canonical_epoch']==1
  if v['valid_visible_frontier']>state['F']:
   candidates=[jid for jid in nodes if jobs[jid]['audio_end_sample']==v['valid_visible_frontier'] and owner[jid]['result']['text']==v['visible_text']]
   actual_illegal+=int(not any(chain(jid,state['F'],state['P'],jobs,{jid:x['result'] for jid,x in owner.items()},nodes,32000) for jid in candidates))
 assert actual_illegal==0 and first_selected is not None
 if plan['method']!='renderer_only':assert first_selected['token_ids']==oracles[0]['result']['token_ids'] and first_selected['state_tokens']==oracles[0]['result']['state_tokens']
 assert state['F']==r['final_frontier'] and list(state['P'])==r['final_state']['prompt_tokens']
 private=next(c for c in calls if c['purpose']=='future-private-at-8s-before-authority-install')
 assert private['job']['chunk_id']==3 and private['job']['audio_end_sample']==128000
 before=[c for c in calls if c['purpose']=='common-trusted-prelude'];assert len(before)==2
 # English word/CER definitions match the normal study, including all source text.
 ref=normalized(r['reference']);hyp=normalized(r['final_text']);a=re.findall(r"[a-z0-9']+",ref);b=re.findall(r"[a-z0-9']+",hyp)
 we=edits(a,b);wc=len(a);a=[x for x in ref if x.isalnum()];b=[x for x in hyp if x.isalnum()];ce=edits(a,b);cc=len(a)
 selected_equal=first_selected['token_ids']==oracles[0]['result']['token_ids']
 return dict(case=D.name,method=plan['method'],traffic=plan['traffic'],source_id=plan['source_id'],
  actual_source_and_transport_pass=True,actual_private_chain_consumer_violations=actual_illegal,
  unchecked_candidate_installs=len(unchecked),selected_6s_matches_actual_FP32_reference=selected_equal,
  private_future_processed_prefix_marker=marker(private['result']['model_input_audit']['rollback_prefix']),
  private_future_new_neural_Z_is_not_injected=private['job']['job_id'] in original_neural_Z,
  final_marker=marker(r['final_text']),word_errors=we,reference_words=wc,WER_percent=100*we/wc,English_CER_percent=100*ce/cc,
  physical_batches=len(batches),actual_neural_phases=len(actual_phases),
  actual_FP32_verification_calls=sum(q['phase']=='correct-context-strict' for q in actual_phases),
  actual_FP32_generation_calls=sum(q['phase']=='fresh-FP32-fallback' for q in actual_phases),
  diagnostic_neural_phases=sum(q['purpose']=='DIAGNOSTIC_ONLY_NO_ADMISSION' for q in actual_phases),
  all_neural_phase_seconds=sum(q['completed_perf']-q['started_perf'] for q in actual_phases),
  metadata_shadow_not_extra_GPU_case=r['metadata_only_shadow_on_same_coherent_candidate'],
  prelude_native_Z=[c['result']['token_ids'] for c in before],
  original_candidate_native_Z=original[next(c['job']['job_id'] for c in calls if c['purpose']=='candidate-at-6s')][1]['token_ids'],
  original_parent_P_before_injection=next(c['job']['prompt_tokens'] for c in calls if c['purpose']=='candidate-at-6s'),
  note='primary frozen substring plus stricter word-boundary supplement; CPU/asset and full WAL replay remain separate gates')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--stage',choices=['pilot','formal'],default='pilot');ap.add_argument('--source-manifest',type=Path,required=True)
 a=ap.parse_args();a.output.mkdir(exist_ok=False);stage=a.root/a.stage;source=read(a.source_manifest);harness=source['code_commit'];shas={r['path']:r['sha256'] for r in source['files']}
 done=read(stage/'SUMMARY.json');freeze=read(stage/'FREEZE.json');expected_count=8 if a.stage=='pilot' else 64
 assert done['cells']==done['expected']==len(freeze['cells'])==expected_count and freeze['harness_commit']==harness
 assert not (stage/'STOP.json').exists()
 expected=[f"{c['method']}-{c['traffic']}-{c['source_id']}-r{c['repeat']}" for c in freeze['cells']];assert done['completed']==expected
 rows=[]
 for name,c in zip(expected,freeze['cells']):
  p=read(stage/name/'provenance.json')
  for file,digest in p['script_sha256'].items():assert shas[file]==digest
  r=audit(stage/name,harness);r['repeat']=c['repeat'];rows.append(r)
 pairs=[]
 for method,source_id,repeat in sorted({(r['method'],r['source_id'],r['repeat']) for r in rows}):
  clean=next(r for r in rows if (r['method'],r['source_id'],r['repeat'],r['traffic'])==(method,source_id,repeat,'clean'))
  bad=next(r for r in rows if (r['method'],r['source_id'],r['repeat'],r['traffic'])==(method,source_id,repeat,'coherent-proposer'))
  matched=all(clean[k]==bad[k] for k in ['prelude_native_Z','original_candidate_native_Z','original_parent_P_before_injection'])
  pairs.append(dict(method=method,source_id=source_id,repeat=repeat,pre_injection_actual_input_and_native_Z_matched=matched,
   word_error_delta=bad['word_errors']-clean['word_errors'],substring_final=bad['final_marker']['frozen_substring'],whole_word_final=bad['final_marker']['exact_whole_words']))
 (a.output/'SUMMARY.json').write_text(json.dumps(dict(status='PASS_RECORDED_SOURCE_SELECTION_AND_ACTUAL_CONSUMER_PENDING_WAL_ASSETS',stage=a.stage,case_count=len(rows),harness_commit=harness,cases=rows,pairs=pairs,
  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),no_new_neural_GPU_calls=True,
  limits='frozen source pool; no natural prevalence, no permanent propagation, no online performance; weak negative policy not completeStandard'),indent=2)+'\n')
 print(json.dumps(dict(pairs=pairs,cases=len(rows))))
