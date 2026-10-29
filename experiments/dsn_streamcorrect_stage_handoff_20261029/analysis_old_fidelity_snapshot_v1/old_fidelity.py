"""Exact old/new task fidelity, with one declared contract-tag projection only."""
from __future__ import annotations
import argparse,copy,datetime,hashlib,json,os,pathlib,platform,re,subprocess,sys,traceback

STATE_FIELDS={'audio_segments','tokens','context','last_attend_frame','detected_language',
 'initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript'}
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def need(x,message):
 if not x:raise ValueError(message)
def equal(a,b):return canonical(a)==canonical(b)
def projected_cut(new,stage):
 need(set(new)==STATE_FIELDS,'unexpected/missing new state fields')
 p=copy.deepcopy(new);need(type(p['contract']) is dict,'missing new contract')
 need('stage_execution' in p['contract'],'new stage_execution absent')
 need(equal(p['contract']['stage_execution'],stage),'unallowed stage_execution binding')
 del p['contract']['stage_execution']
 return p
def indexed(rows,key,label):
 out={}
 for r in rows:
  k=key(r);need(k not in out,'duplicate '+label+': '+repr(k));out[k]=r
 return out

def compare_bank(*,histories,wals,jobs,details,initials,sources,stage,audit_histories):
 """Compare all calls; unknown/missing/extra data fails rather than disappears."""
 expected={}
 for s in sources:
  sid=s['source_id'];need(sid not in expected,'duplicate source')
  frontiers=list(range(8000,s['frames'],8000))+[s['frames']]
  expected[sid]=frontiers
 need(set(histories)==set(expected) and set(initials)==set(expected),'source scope differs')
 history={}
 for sid,rows in histories.items():
  need([r['F'] for r in rows]==expected[sid],'old full history frontier sequence differs')
  need([r['state_sha256'] for r in rows]==audit_histories[sid],'old history differs from prior frozen audit')
  for r in rows:
   need(set(r['state'])==STATE_FIELDS,'unexpected/missing old state field')
   need('stage_execution' not in r['state']['contract'],'old history already has new stage tag')
   need(r['state']['frontier']==r['F'] and digest(r['state'])==r['state_sha256'],'old history hash/frontier invalid')
   history[(sid,r['F'])]=r
 wanted=set(history)
 wal=indexed(wals,lambda r:(r['source_id'],r['state']['frontier']),'old WAL')
 job=indexed(jobs,lambda r:(r['source_id'],r['record']['end']),'old job')
 new=indexed(details,lambda r:(r['source_id'],r['end']),'new detail')
 need(set(wal)==wanted and set(job)==wanted and set(new)==wanted,'missing/extra actual calls')
 previous={sid:initials[sid] for sid in expected};previous_F={sid:0 for sid in expected};results=[]
 for s in sources:
  sid=s['source_id'];source_sha=s['audio_sha256']
  for F in expected[sid]:
   k=(sid,F);h=history[k];w=wal[k];j=job[k];n=new[k];nr=n['original_full_result'];cut=n['original_full_cut'];start=previous[sid]
   need(w['state_sha256']==h['state_sha256'] and equal(w['state'],h['state']),'old WAL/history cut differs')
   need(equal(j['end'],h['state']),'old job/history cut differs')
   need(equal(j['record']['selected_correction'],w['selected']),'old actual C/WAL differs')
   need(equal(j['record']['token_ids'],h['token_ids']),'old returned IDs/history differs')
   need(j['record']['end_state']==h['state_sha256'],'old record end binding differs')
   need(j['record']['start_state']==digest(j['start']),'old record start binding differs')
   need(j['start']['frontier']==previous_F[sid] and j['record']['start']==previous_F[sid],'old original start differs')
   need(n['start']==previous_F[sid] and nr['start']==previous_F[sid] and nr['end']==F,'new original interval differs')
   need(n['full_input_sha']==digest(start) and nr['start_state']==digest(start),'new original input hash differs')
   need(nr['end_state']==digest(cut),'new record end binding differs')
   need(start['contract']['source_sha']==source_sha and cut['contract']['source_sha']==source_sha,'new source bytes binding differs')
   normalized_start=projected_cut(start,stage);normalized_end=projected_cut(cut,stage)
   need(equal(normalized_start,j['start']),'complete original start differs after declared tag projection')
   need(equal(normalized_end,h['state']),'complete original end differs after declared tag projection')
   need(equal(nr['token_ids'],j['record']['token_ids']),'returned token IDs differ')
   need(equal(nr['selected_correction'],j['record']['selected_correction']),'complete selected C differs')
   need(equal(nr['text'],j['record']['text']),'appended text differs')
   need(nr['native_model_evaluated'] is j['record']['native_model_evaluated'],'model-evaluated path differs')
   need(nr['role']=='authority' and nr['authority_ASR_executed'] is True,'new full reference did not execute Authority ASR')
   results.append(dict(source_id=sid,start=previous_F[sid],end=F,
    original_old_cut_sha256=h['state_sha256'],new_unprojected_cut_sha256=digest(cut),
    new_projected_cut_sha256=digest(normalized_end),old_raw_and_new_raw_hashes_equal=h['state_sha256']==digest(cut),
    complete_start_equal_after_declared_tag_projection=True,complete_end_equal_after_declared_tag_projection=True,
    full_selected_C_equal=True,returned_ids_equal=True,appended_text_equal=True,
    token_ids=nr['token_ids'],selected_correction=nr['selected_correction'],text=nr['text']))
   previous[sid]=cut;previous_F[sid]=F
 return results

def verify_source(root,manifest):
 m=json.loads(manifest.read_bytes())
 def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
 need(git('rev-parse','HEAD')==m['source_commit'],'analysis commit differs')
 need(not git('status','--porcelain','--untracked-files=all'),'analysis source dirty')
 need(set(git('ls-files','-z').split('\0'))-{''}=={r['path'] for r in m['files']},'incomplete analysis manifest')
 for r in m['files']:
  raw=(root/r['path']).read_bytes();need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'analysis source bytes differ')
 return m['source_commit']

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 root=pathlib.Path(__file__).resolve().parent;commit=verify_source(root,a.manifest);plan=json.loads(a.plan.read_bytes());need(plan['analysis_source_commit']==commit,'plan source differs');a.out.mkdir(exist_ok=False)
 def put(n,x):(a.out/n).write_bytes(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False).encode())
 put('CONFIG.json',plan);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),models_loaded=0,gpu_launched=False,analysis='stdlib CPU exact comparison of saved neural outputs'))
 put('RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],analysis_source_commit=commit,source_manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),config_sha256=hashlib.sha256((a.out/'CONFIG.json').read_bytes()).hexdigest(),environment_sha256=hashlib.sha256((a.out/'ENVIRONMENT.json').read_bytes()).hexdigest(),raw_result_location=str(a.out/'COMPARISONS.json'),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 receipts={}
 def load(label,path,expected=None,jsonl=False):
  path=pathlib.Path(path);raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest();need(expected is None or h==expected,label+' frozen bytes differ');receipts[label]=dict(path=str(path),bytes=len(raw),sha256=h)
  return [json.loads(line) for line in raw.splitlines() if line.strip()] if jsonl else json.loads(raw)
 try:
  controls=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root),'-p','test_*.py','-v'],cwd=root,env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
  log=controls.stdout+controls.stderr;(a.out/'CPU_CONTROLS.log').write_text(log,encoding='utf8');need(controls.returncode==0 and 'skipped=' not in log,'frozen CPU controls failed/skipped')
  count=re.search(r'Ran (\d+) tests?',log);need(count is not None and int(count[1])==17,'frozen CPU scope differs');put('CPU_CONTROLS.json',dict(status='PASS_FROZEN_SYNTHETIC_COMPARATOR_CONTROLS_ONLY',tests=int(count[1]),native_neural_calls=0))
  native=load('old_native_plan',plan['old_native_plan'],plan['old_native_plan_sha256'])
  prior=load('prior_native_audit',plan['prior_native_audit'],plan['prior_native_audit_sha256']);need(prior['status']=='PASS_TWELVE_ACTUAL_NATIVE_CELLS_AND_FULL_HISTORY_EQUIVALENCE','prior native gate missing')
  ref=load('original_fixed_references',plan['original_fixed_references'],plan['original_fixed_references_sha256'])
  eq=load('new_neural_plan',plan['new_neural_plan'],plan['new_neural_plan_sha256']);need(eq['source_commit']==plan['neural_source_commit'],'new actual source differs')
  gate=load('new_neural_gate',plan['new_neural_out']+'/GATE.json');need(gate['status']=='PASS_FOUR_SOURCE_PROTECTED_PACKET_ORIGINAL_C_U_EQUIVALENCE' and gate['full_steps']==69 and gate['source_commit']==plan['neural_source_commit'],'new neural gate not complete PASS')
  need(equal(native['sources'],ref['sources']) and equal(eq['settings']['sources'],ref['sources']),'original four source definitions changed')
  need(equal(eq['settings']['backend'],ref['backend']),'new original neural backend changed')
  details=load('new_neural_details',plan['new_neural_out']+'/DETAILS.json');ready=load('new_neural_ready',plan['new_neural_out']+'/READY.json')
  need(equal(ready['authority']['initials'],ready['producer']['initials']),'new ready roots differ')
  histories={};wals=[];jobs=[];audit={}
  for cohort in ('A','B'):
   cells=[c for c in native['cells'] if c['stage']=='formal' and c['cohort']==cohort and c['arm']=='sequential' and c['repeat']==0];need(len(cells)==1,'old baseline selector ambiguous');cell=cells[0];base=cell['out']
   cfg=load('old_'+cohort+'_config',cell['config'],ref['config_sha256'] if cohort=='A' else None);need(equal(cfg['settings']['backend'],ref['backend']),'old baseline backend changed')
   h=load('old_'+cohort+'_histories',base+'/CANONICAL_HISTORIES.json',ref['original_histories_sha256'] if cohort=='A' else None)
   need(not set(histories)&set(h),'old source duplicated across cohorts');histories.update(h)
   wals+=load('old_'+cohort+'_canonical_wal',base+'/canonical_wal.jsonl',jsonl=True)
   js=load('old_'+cohort+'_actual_jobs',base+'/native_jobs.jsonl',jsonl=True)
   need(all(r['role'].startswith('authority') for r in js),'old selected baseline contains private completions');jobs+=js
   rows=[c for c in prior['cells'] if c['cell_id']==cell['cell_id']];need(len(rows)==1,'old baseline absent from prior audit');audit.update(rows[0]['canonical_history_sha'])
  stage=dict(protocol='protected_original_asr_ready_only_v1',asr_dtype='float32',corrector_dtype='float32',source_commit=plan['neural_source_commit'])
  rows=compare_bank(histories=histories,wals=wals,jobs=jobs,details=details,initials=ready['authority']['initials'],sources=ref['sources'],stage=stage,audit_histories=audit)
  need(len(rows)==69,'full fixed 69-call scope missing');put('COMPARISONS.json',rows)
  for label,r in receipts.items():need(hashlib.sha256(pathlib.Path(r['path']).read_bytes()).hexdigest()==r['sha256'],'input changed during CPU comparison: '+label)
  put('INPUT_MANIFEST.json',receipts)
  summary=dict(status='PASS_ALL_69_OLD_NATIVE_TASK_RESULTS_AFTER_EXACT_DECLARED_STAGE_TAG_PROJECTION',analysis_source_commit=commit,neural_source_commit=plan['neural_source_commit'],frozen_cpu_controls=int(count[1]),calls=len(rows),sources=len(histories),full_start_comparisons=len(rows),full_end_comparisons=len(rows),complete_C_comparisons=len(rows),returned_ID_comparisons=len(rows),raw_old_new_cut_hashes_equal=sum(r['old_raw_and_new_raw_hashes_equal'] for r in rows),only_removed_state_field='contract.stage_execution (exact expected value required)',all_other_state_fields_preserved=True,timing_equality_claimed=False,new_inference_calls=0,serving_cells=0,scope='saved-output fidelity to original native sequential-r0 A/B; raw cut hashes include different contract tags and are not called equal')
  put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(summary,indent=2));return 0
 except BaseException:
  put('INPUT_MANIFEST.json',receipts);(a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');put('GATE.json',dict(status='FAIL_OLD_NATIVE_TASK_FIDELITY_PRESERVED',analysis_source_commit=commit));raise

if __name__=='__main__':raise SystemExit(main())
