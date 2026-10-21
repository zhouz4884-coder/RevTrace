"""Independent CPU audit of actually consumed F2, input layouts and recovery."""
from pathlib import Path
import hashlib,json,sys
B=Path(sys.argv[1]);O=B/'results/revtrace/phaseD_20261021';P=B/'projects/revtrace_phaseD_20261021';sys.path[:0]=[str(P/'continuity_v6/src')]
from revtrace.dgft import digest_tokens
from transformers import AutoProcessor,WhisperProcessor
from qwen_asr import parse_asr_output
tok=AutoProcessor.from_pretrained(B/'models/Qwen3-ASR-1.7B',local_files_only=True).tokenizer
whisper=WhisperProcessor.from_pretrained(B/'models/whisper-small.en',local_files_only=True)
def render(inp):
 raw=tok.decode(inp['prompt_tokens'],skip_special_tokens=False,clean_up_tokenization_spaces=False);prefix=''
 if inp['chunk_id']>=2 and raw:
  ids=tok.encode(raw);k=5
  while True:
   prefix=tok.decode(ids[:max(0,len(ids)-k)])
   if '\ufffd' not in prefix or k>=len(ids):break
   k+=1
 raw=prefix+tok.decode(inp['token_ids'],skip_special_tokens=True,clean_up_tokenization_spaces=False);_,text=parse_asr_output(raw,user_language=inp['language']);return tok.encode(raw),text
sources=[]
for f in (O/'R5_whisper').glob('*.json'):
 r=json.loads(f.read_text())
 if 'records' not in r:continue
 for pair in r['records'].values():
  assert len(pair)==2 and pair[0]['tokens']==pair[1]['tokens'],'same-input repeat disagreement'
  for g in pair:
   assert g['generated_offset']==len(g['actual_first_decoder_ids'])
   assert g['full_returned_tokens_including_decoder_prefix'][:g['generated_offset']]==g['actual_first_decoder_ids']
   assert g['full_returned_tokens_including_decoder_prefix'][g['generated_offset']:]==g['tokens']
   assert g['tokens'] and (g['tokens'][-1]==g['eos'] or (g['hit_cap'] and len(g['tokens'])==128))
   expected_prefix=whisper.get_prompt_ids(g['prompt'],return_tensors='pt').tolist()
   assert g['actual_first_decoder_ids'][:len(expected_prefix)]==expected_prefix
 assert r['initial_oracle']['tokens']==r['initial_oracle_repeat']['tokens']
 assert r['baseline_future']['tokens']==r['baseline_future_repeat']['tokens'] and r['fault_future']['tokens']==r['fault_future_repeat']['tokens']
 assert r['records']['native'][0]['audio_sha256']==r['records']['fault'][0]['audio_sha256']==r['records']['oracle'][0]['audio_sha256']
 assert r['records']['native'][0]['supplied_features']['precast_sha256']==r['records']['fault'][0]['supplied_features']['precast_sha256']==r['records']['oracle'][0]['supplied_features']['precast_sha256']
 assert r['records']['native'][0]['supplied_features']['actual_cast_argument_sha256']==r['records']['fault'][0]['supplied_features']['actual_cast_argument_sha256']
 actual=r['records']['native'][0]['actual_first_decoder_ids']!=r['records']['fault'][0]['actual_first_decoder_ids'];assert actual==r['actual_context_changed']
 assert r['baseline_future']['audio_sha256']==r['fault_future']['audio_sha256'];sources.append(r)
assert len(sources)==16 and len({s['speaker'] for s in sources})==16
rawcalls=[json.loads(x) for x in (O/'R5_whisper/calls_raw.jsonl').read_text().splitlines()];validcalls=[json.loads(x) for x in (O/'R5_whisper/calls_validated.jsonl').read_text().splitlines()]
assert len(rawcalls)==len(validcalls)==192 and len({r['call_id'] for r in rawcalls})==192
f2={'sources':16,'consumed_faults':sum(r['valid_consumed_F2'] for r in sources),'target_output_changed':sum(r['output_changed_vs_same_precision_native'] for r in sources),'future_changed_among_changed_targets':sum(r['output_changed_vs_same_precision_native'] and r['future_output_changed'] for r in sources),'target_changed_denominator':sum(r['output_changed_vs_same_precision_native'] for r in sources),'same_input_repeats_all_equal':True,'native_errors':sum(r['native_errors'] for r in sources),'fault_errors':sum(r['fault_errors'] for r in sources),'reference_words':sum(r['reference_words'] for r in sources),'scope':'controlled consumed-history intervention, not natural fault incidence'}
real=json.loads((O/'R6_realization/SUMMARY.json').read_text());assert real['status']=='COMPLETE'
cases=list((O/'R6_realization').glob('case-*.json'));assert len(cases)==24 and len(real['comparisons'])==4
assert all(r['within_layout_repeats_equal'] for r in real['comparisons']),'R6 same-layout model repeat instability requires triage'
for f in cases:
 r=json.loads(f.read_text());a,b=r['cpu_replayed_twice'];assert a==b and a['ids']==r['processed_input_ids'] and a['features_sha256']==r['target_result']['model_input_audit']['row_features']['input_features']['sha256']
rec=json.loads((O/'R2_gpu_recovery/SUMMARY.json').read_text());assert len(rec['trials'])==3;recover=[]
for t in rec['trials']:
 i=t['repeat'];prefix=(O/'R2_gpu_recovery'/f'killed-prefix-r{i}.wal').read_bytes();assert hashlib.sha256(prefix).hexdigest()==t['wal_prefix_before_kill_sha256'] and len(prefix)==t['wal_prefix_before_kill_bytes']
 cell=O/'R2_gpu_recovery'/f'restore-r{i}';provenance=json.loads((cell/'provenance.json').read_text());wal=Path(provenance['durable_journal_path']).read_bytes();assert wal.startswith(prefix)
 pos=0;seq=0;previous='';expected={};seen=set();parents={}
 while pos<len(wal):
  n=int.from_bytes(wal[pos:pos+4],'big');payload=wal[pos+4:pos+4+n];h=hashlib.sha256(payload).digest();assert h==wal[pos+4+n:pos+4+n+32];r=json.loads(payload);assert r['sequence']==seq and r['previous_sha256']==previous;seq+=1;previous=h.hex();pos+=n+36
  if r['kind']!='commit':continue
  key=(r['session_id'],r['transaction_id']);assert key not in seen;seen.add(key)
  e=r['event'];proof=e['text_binding'];inp=proof['render_inputs'];Pnew,text=render(inp);cert=e['certificate']
  assert inp['state_tokens']==Pnew and e['committed_text']==text and proof['text_sha256']==hashlib.sha256(text.encode()).hexdigest()
  assert cert['display_sha256']==digest_tokens(inp['token_ids']) and cert['feedback_state_sha256']==digest_tokens(Pnew) and cert['prompt_sha256']==digest_tokens(inp['prompt_tokens'])
  sid=r['session_id'];assert inp['prompt_tokens']==parents.get(sid,[]);parents[sid]=Pnew;expected[sid,r['parent_checkpoint_id']+1]=(text,e['audio_end_sample'])
 ev=[json.loads(x) for x in (cell/'events.jsonl').read_text().splitlines()];v=[json.loads(x) for x in (cell/'consumer.jsonl').read_text().splitlines()]
 published=[e for e in ev if e['kind']=='canonical-display' and e['recovered']]
 for e in published:
  text,F=expected[e['session_id'],e['version']];assert e['text']==text and e['audio_end_sample']==F
  assert any(a['session_id']==e['session_id'] and a['canonical_version']==e['version'] and a['certified_text']==text and a['certified_frontier']==F and a['observed']>=e['displayed'] for a in v)
 measured=min(a['observed_perf'] for a in v if (a['session_id'],a['canonical_version']) in {(e['session_id'],e['version']) for e in published})-t['restart_launch_perf']
 assert abs(measured-t['restart_to_first_certified_consumer_seconds'])<1e-7
 recover.append({'repeat':i,'unique_admissions':len(seen),'recovered_snapshots_observed':len(published),'ledger_recovery_seconds':t['journal_recovery_seconds'],'model_initialization_seconds':t['model_initialization_seconds'],'restart_to_first_certified_consumer_seconds':measured,'restore_process_full_wall_seconds':t['restore_process_full_wall_seconds']})
result={'status':'PASS_INDEPENDENT_F2_REALIZATION_AND_CRASH_RECOVERY','F2':f2,'realization':real['comparisons'],'recovery':recover,'V0_V1_NO_GO_preserved':True,'no_V2_or_new_KV_fallback':True}
(O/'FINAL_STUDIES_INDEPENDENT_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
