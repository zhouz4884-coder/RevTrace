"""Read-only full collected long telemetry recount; no neural/source changes."""
import collections,datetime,hashlib,json,pathlib
F=pathlib.Path(__file__).resolve().parents[1];D=F/'LONG_REFERENCE_RESULTS_v2'
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
manifest=read(D/'COLLECTION_MANIFEST.json');known={r['path']:r for r in manifest['files']};summary=read(D/'SUMMARY.json')
assert summary['status']=='PASS_CONTINUOUS_ORIGINAL_AND_ALL_RESTORED_NATIVE_EDGES'
assert summary['source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47' and summary['reference_full_calls']==summary['restored_full_calls']==875
def derived(s):
 T=s['current_token_count'];C=s['context_token_count'];P=s['context_prefix_token_count'];M=s['max_text_len'];K=s['max_context_tokens'];nonempty=s['context_text_codepoints']>0
 assert sum(s['token_group_lengths'])==T and len(s['token_group_lengths'])==s['token_group_count']
 assert s['total_decoder_input_tokens']==T+C
 soft=C>K or T+C>M-20;assert soft is s['context_trim_triggered']
 L=T+C+P if nonempty else T
 bucket='<=428' if L<=428 else '429..447' if L<448 else '>=448'
 return dict(T=T,C=C,P=P,M=M,K=K,context_nonempty=nonempty,soft=soft,L=L,bucket=bucket,groups=s['token_group_count'])
results=[];inputs=[]
for path in sorted(D.rglob('STATE_BOUNDARIES.jsonl')):
 rel=path.relative_to(D).as_posix();assert sha(path)==known[rel]['sha256'] and path.stat().st_size==known[rel]['bytes'];inputs.append(dict(path=rel,bytes=path.stat().st_size,sha256=sha(path)));rows=[json.loads(x) for x in path.read_bytes().splitlines() if x.strip()];by=collections.defaultdict(list)
 for row in rows:
  name='continuous' if row['job_id'].startswith('continuous_') else 'restore' if row['job_id'].startswith('restore_') else None
  assert name is not None;by[name].append(row)
 source=path.parent.name
 for mode,rr in by.items():
  trim=[r for r in rr if r['boundary']=='context_trim'];insert=[r for r in rr if r['boundary']=='audio_insert'];after=[derived(r['after']) for r in trim];before=[derived(r['before']) for r in trim]
  for r,s in zip(trim,after):assert r['bound_still_exceeded'] is s['soft']
  assert {s['M'] for s in after}=={448} and {s['K'] for s in after}=={448}
  counts=collections.Counter((s['bucket'],'nonempty' if s['context_nonempty'] else 'empty','soft_true' if s['soft'] else 'soft_false') for s in after)
  interesting=[]
  for predicate,label in [(lambda s:s['soft'],'first_after_soft_true'),(lambda s:s['L']>=448,'first_after_L_at_least448'),(lambda s:s['soft'] and s['C']==0 and s['T']>428,'first_current_window_alone_exceeds_soft')]:
   match=next(((r,s) for r,s in zip(trim,after) if predicate(s)),None)
   if match:interesting.append(dict(label=label,job_id=match[0]['job_id'],end_frontier=match[0]['end_frontier'],audio_seconds=match[0]['end_frontier']/16000,derived=match[1]))
  output=dict(source_id=source,pass_kind=mode,actual_insert_observations=len(insert),actual_buffer_shifts=sum(bool(r['buffer_shift']) for r in insert),actual_context_trim_calls=len(trim),actual_context_change_observations=sum(bool(r['context_changed']) for r in trim),before_soft_true=sum(s['soft'] for s in before),after_soft_true=sum(s['soft'] for s in after),after_soft_false=sum(not s['soft'] for s in after),after_initial_decoder_sequence_bins=dict(collections.Counter(s['bucket'] for s in after)),after_context_nonempty=sum(s['context_nonempty'] for s in after),after_context_empty=sum(not s['context_nonempty'] for s in after),after_soft_true_and_current_window_alone_exceeds428=sum(s['soft'] and s['T']>428 for s in after),after_soft_true_and_empty_context=sum(s['soft'] and not s['context_nonempty'] for s in after),after_L_at_least448_and_empty_context=sum(s['L']>=448 and not s['context_nonempty'] for s in after),after_L_at_least448_and_nonempty_context=sum(s['L']>=448 and s['context_nonempty'] for s in after),cross_bins=[dict(L_bin=k[0],context=k[1],soft=k[2],count=n) for k,n in sorted(counts.items())],token_group_count_distribution=dict(sorted(collections.Counter(s['groups'] for s in after).items())),context_prefix_counts=sorted({s['P'] for s in after}),ranges={key:dict(min=min(s[key] for s in after),max=max(s[key] for s in after)) for key in ('T','C','L','groups')},first_events=interesting,scope='Post-original-trim snapshot implies _current_tokens initial sequence length for the immediately following code path. Actual decoder forward/position-index execution is not observed by this counter; author while guard may skip it.')
  results.append(output)
for sid in {r['source_id'] for r in results}:
 a=next(r for r in results if r['source_id']==sid and r['pass_kind']=='continuous');b=next(r for r in results if r['source_id']==sid and r['pass_kind']=='restore')
 assert {k:v for k,v in a.items() if k not in ('pass_kind','first_events')}=={k:v for k,v in b.items() if k not in ('pass_kind','first_events')}
out=dict(schema='native-context-full-collected-telemetry-definition-v2',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),analysis_script_sha256=sha(__file__),actual_neural_source_commit=summary['source_commit'],reference_gate_sha256=sha(D/'GATE.json'),collection_manifest_sha256=sha(D/'COLLECTION_MANIFEST.json'),observed_source_coverage=dict(original_continuous_steps=875,restored_edges=875,all_full_state_C_IDs_equal=True),new_model_calls=0,remote_operations=0,source_or_CURRENT_changed=False,inputs=inputs,passes=results,definitions=dict(T='sum token-group shape[1], beam is not multiplied',C='re-encoded context text token count, excluding context prefix',P='context prefix count',observer_soft_total='T+C',derived_initial_current_tokens='T+C+P if context text nonempty else T',soft_predicate='C>448 or T+C>428',actual_original_decoder_guard='current_tokens.shape[1]<448, with completed initiallyFalse'),limitations='No decoder hook/progress tensor was added. L>=448 is the guard condition under which this original while can skip initial decoding, not proof of an out-of-range positional embedding access. Counts are finite observed model state/soft-policy observations, not protocol live-entry bounds.')
p=F/'NATIVE_CONTEXT_COUNT_COUNTER_v2.json';assert not p.exists();p.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
print(json.dumps([{k:r[k] for k in ('source_id','pass_kind','actual_buffer_shifts','actual_context_change_observations','after_soft_true','after_initial_decoder_sequence_bins','after_context_nonempty','after_context_empty','after_soft_true_and_empty_context','after_L_at_least448_and_empty_context','ranges')} for r in results],indent=2))

