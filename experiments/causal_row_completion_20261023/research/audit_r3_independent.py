"""Independently join actual calls; no new generation or infinite recovery claim."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,re,sys,unicodedata

B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'r3_gpu_v2'
A=O/'r3_independent_v1';A.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def edit(a,b):
 table=[[0]*(len(b)+1) for _ in range(len(a)+1)]
 for i in range(len(a)+1):table[i][0]=i
 for j in range(len(b)+1):table[0][j]=j
 for i in range(1,len(a)+1):
  for j in range(1,len(b)+1):table[i][j]=min(table[i-1][j]+1,table[i][j-1]+1,table[i-1][j-1]+(a[i-1]!=b[j-1]))
 return table[-1][-1]
def q(reference,hyp):
 norm=lambda s:unicodedata.normalize('NFKC',s).lower()
 rw=re.findall(r"[a-z0-9']+",norm(reference));hw=re.findall(r"[a-z0-9']+",norm(hyp))
 rc=[c for c in norm(reference) if c.isalnum()];hc=[c for c in norm(hyp) if c.isalnum()]
 return {'word_errors':edit(rw,hw),'reference_words':len(rw),'char_errors':edit(rc,hc),'reference_chars':len(rc)}
def first_and_rediverge(values):
 first=next((i+1 for i,x in enumerate(values) if x),None)
 return {'first_equal_K':first,'right_censored':first is None,'redivergence':[i+1 for i,x in enumerate(values) if first is not None and i+1>first and not x]}
try:
 summary=read(D/'SUMMARY.json');assert summary['status']=='COMPLETE_R3_NATIVE_TRAJECTORIES' and summary['cases']==32
 manifest=read(O/'r3_source_v1/MANIFEST.json');sources={s['source_id']:s for s in manifest['sessions']}
 calls={int(p.name.split('-')[0]):read(p) for p in (D/'calls').glob('*.json')}
 assert len(calls)==summary['model_calls']==652
 window_rows=[];case_rows=[];cases={};rawindex=[]
 for p in D.glob('*.json'):
  if not p.name.startswith(('Qwen-','Whisper-')):continue
  c=read(p);family=c['family'];sid=c['source_id'];rep=c['repeat'];cases[family,sid,rep]=c
  fault=6 if family=='Qwen' else 2;inputeq=[];root_actual_change=None;lastP=[[],[]];lastY=['','']
  for w in c['windows']:
   k=w['window'];pair=[calls[x] for x in w['calls']];z=[p['result'] for p in pair]
   if family=='Qwen':
    assert [x['state_tokens'] for x in z]==w['P'] and [x['token_ids'] for x in z]==w['Z'] and [x['text'] for x in z]==w['Y']
    for arm in [0,1]:
     j=pair[arm]['job'];assert j['prompt_tokens']==lastP[arm]
     expected=j.get('fault_actual_prompt_tokens',lastP[arm]);assert z[arm]['execution_context_audit']['executed_prompt_tokens']==expected
     assert z[arm]['started_perf']<=z[arm]['completed_perf']
    equal_ids=z[0]['model_input_audit']['unpadded_input_ids']==z[1]['model_input_audit']['unpadded_input_ids']
    equal_features=z[0]['model_input_audit']['row_features']==z[1]['model_input_audit']['row_features']
   else:
    assert [x['P'] for x in z]==w['P'] and [x['new_Z_excludes_copied_prefix'] for x in z]==w['Z'] and [x['Y'] for x in z]==w['Y']
    for arm in [0,1]:
     assert z[arm]['declared_history_before']==lastY[arm]
     if not (k==fault and arm==1):assert z[arm]['actual_conditioning_history']==lastY[arm]
     full=z[arm]['full_returned_tokens'];prefix=z[arm]['actual_first_decoder_ids']
     assert full[:len(prefix)]==prefix and full[len(prefix):]==w['Z'][arm]
    equal_ids=z[0]['actual_first_decoder_ids']==z[1]['actual_first_decoder_ids']
    equal_features=z[0]['actual_cast_feature_sha256']==z[1]['actual_cast_feature_sha256']
   assert w['P_equal']==(w['P'][0]==w['P'][1]) and w['Z_equal']==(w['Z'][0]==w['Z'][1]) and w['Y_equal']==(w['Y'][0]==w['Y'][1])
   assert equal_ids==w['actual_input_IDs_equal']
   if k<fault:assert equal_ids and equal_features and w['P_equal'] and w['Z_equal'] and w['Y_equal']
   if k==fault:root_actual_change=not equal_ids
   if k>fault:inputeq.append(equal_ids and equal_features)
   window_rows.append({'family':family,'source_id':sid,'repeat':rep,'window':k,
     'future_k':k-fault,'audio_end_s':w['audio_end_s'],'P_supplied_equal':w['P_equal'],
     'new_Z_equal':w['Z_equal'],'full_visible_Y_equal':w['Y_equal'],
     'actual_processed_IDs_equal':equal_ids,'actual_audio_features_equal':equal_features,
     'caps_clean':w['caps'][0],'caps_fault':w['caps'][1],'quality_scope':w['quality_scope'],
     'partial_full_reference_word_error_delta':w['quality'][1]['word_errors']-w['quality'][0]['word_errors']})
   lastP=w['P'];lastY=w['Y']
  post=[w for w in c['windows'] if w['window']>fault]
  definitions={kind:first_and_rediverge([w[kind+'_equal'] for w in post]) for kind in ['P','Z','Y']}
  for kind in ['P','Z','Y']:
   assert definitions[kind]['first_equal_K']==c['summary'][kind]['first_equal_K']
   assert definitions[kind]['redivergence']==c['summary'][kind]['redivergence_windows']
  qualities=[q(sources[sid]['reference'],text) for text in lastY]
  assert qualities==c['final_quality']
  root=next(w for w in c['windows'] if w['window']==fault)
  item={'family':family,'source_id':sid,'repeat':rep,'root_actual_IDs_changed':root_actual_change,
    'root_P_changed':not root['P_equal'],'root_new_Z_changed':not root['Z_equal'],
    'future_windows':len(post),'K_P':definitions['P']['first_equal_K'],'P_right_censored':definitions['P']['right_censored'],
    'P_redivergences':definitions['P']['redivergence'],'K_Z':definitions['Z']['first_equal_K'],
    'Z_right_censored':definitions['Z']['right_censored'],'Z_redivergences':definitions['Z']['redivergence'],
    'K_Y':definitions['Y']['first_equal_K'],'Y_right_censored':definitions['Y']['right_censored'],
    'Y_redivergences':definitions['Y']['redivergence'],'effective_input_first_equal_K':first_and_rediverge(inputeq)['first_equal_K'],
    'final_word_errors_clean':qualities[0]['word_errors'],'final_word_errors_fault':qualities[1]['word_errors'],
    'reference_words':qualities[0]['reference_words'],'final_char_errors_clean':qualities[0]['char_errors'],
    'final_char_errors_fault':qualities[1]['char_errors'],'reference_chars':qualities[0]['reference_chars'],
    'caps_clean':c['caps'][0],'caps_fault':c['caps'][1],'censor_reason':'source_end',
    'P_is_declared_supplied_projection_not_proof_effective_input_unequal':True}
  case_rows.append(item)
 assert len(case_rows)==32
 repeats=[]
 for family in ['Qwen','Whisper']:
  for sid in sources:
   a,b=cases[family,sid,0],cases[family,sid,1]
   assert len(a['windows'])==len(b['windows'])
   eq=all(all(x[k]==y[k] for k in ['P','Z','Y']) for x,y in zip(a['windows'],b['windows']))
   repeats.append(eq)
 assert all(repeats)
 groups=[]
 for family in ['Qwen','Whisper']:
  a=[r for r in case_rows if r['family']==family and r['repeat']==0]
  groups.append({'family':family,'independent_sources':len(a),'repeat_count_not_extra_subjects':2,
    'actual_context_changed':sum(r['root_actual_IDs_changed'] for r in a),'root_P_changed':sum(r['root_P_changed'] for r in a),
    'P_first_equal_observed':sum(r['K_P'] is not None for r in a),'Z_first_equal_observed':sum(r['K_Z'] is not None for r in a),
    'Y_first_equal_observed':sum(r['K_Y'] is not None for r in a),
    'quality_worse_equal_better':[sum((r['final_word_errors_fault']>r['final_word_errors_clean']) for r in a),
        sum(r['final_word_errors_fault']==r['final_word_errors_clean'] for r in a),sum(r['final_word_errors_fault']<r['final_word_errors_clean'] for r in a)],
    'word_errors_clean':sum(r['final_word_errors_clean'] for r in a),'word_errors_fault':sum(r['final_word_errors_fault'] for r in a),
    'reference_words':sum(r['reference_words'] for r in a),'caps_clean':sum(r['caps_clean'] for r in a),'caps_fault':sum(r['caps_fault'] for r in a)})
 for name,data in [('R3_WINDOWS.csv',window_rows),('R3_CASES.csv',case_rows)]:
  with (A/name).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 for p in sorted(D.rglob('*')):
  if p.is_file():rawindex.append({'path':p.relative_to(D).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 save(A/'RAW_INDEX.json',{'files':rawindex,'all_originals_retained':True})
 out={'status':'PASS_INDEPENDENT_R3_CALL_TRAJECTORY_ENDPOINT_AUDIT','calls':len(calls),'cases':32,'unique_subjects':8,
    'groups':groups,'all_full_repeats_equal':True,'effective_input_vs_supplied_P_separated':True,
    'intermediate_full_reference_delta_not_prefix_accuracy':True,'no_permanent_recovery_or_irrecoverability_claim':True,
    'new_model_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 save(A/'SUMMARY.json',out);print(json.dumps(out))
except BaseException as e:
 save(A/'STOP.json',{'error':repr(e),'all_original_data_retained':True,'new_model_calls':0});raise
