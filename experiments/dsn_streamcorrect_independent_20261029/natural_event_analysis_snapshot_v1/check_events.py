"""Post-hoc exact natural-event reconstruction; no endpoint/model changes."""
import argparse,datetime,hashlib,json,pathlib,platform,subprocess,sys,traceback
METHOD='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def need(x,m):
 if not x:raise ValueError(m)
def same(a,b):return canonical(a)==canonical(b)
def check_reference(job,sid,refs):
 r=next(r for r in refs if r['source_id']==sid and r['end']==job['record']['end'])
 need(same(job['start'],r['original_full_start_cut']) and same(job['end'],r['original_full_cut']),'actual canonical complete input/end differs from original reference')
 need(same(job['record']['selected_correction'],r['original_full_result']['selected_correction']) and job['record']['token_ids']==r['original_full_result']['token_ids'],'actual C/IDs differ')
def event_for_row(row,events,jobs):
 matches=[e for e in events if e['kind']=='canonical_install' and jobs[e['job_id']]['record']['end']==row['certified_frontier'] and e['observed']<=row['observed']]
 need(len(matches)==1,'nonunique actual canonical install');return matches[0]
def early_bound(jobid,early,jobs,dispatch):
 e=early[jobid];j=jobs[jobid];d=dispatch[jobid]
 need(e['job_id']==j['job_id']==d['job_id']==jobid and e['worker']==j['worker']==d['worker']==j['physical_channel_worker'],'owned job/physical channel changed')
 need(e['dispatch_epoch']==j['dispatch_epoch']==d['dispatch_epoch']==0,'epoch changed')
 need(same(e['start_state'],j['start']) and digest(j['start'])==e['start_state_sha']==j['record']['start_state']==d['start_sha'],'complete frozen input changed')
 need(digest(e['projection']['end'])==e['projection']['end_state_sha'] and not e['projection']['learned_C_executed'] and not e['projection']['original_full_infer_completed'],'projection mislabeled closed neural C/U')
 return e,j,d
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();root=pathlib.Path(__file__).resolve().parent;cfg=json.loads(a.config.read_bytes());manifest=json.loads(a.manifest.read_bytes());commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
 need(commit==manifest['code_commit']==cfg['code_commit'],'analysis source changed');need(not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip(),'source dirty')
 need(set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines())=={f['path'] for f in manifest['files']},'manifest incomplete')
 for f in manifest['files']:need(sha(root/f['path'])==f['sha256'] and (root/f['path']).stat().st_size==f['bytes'],'source bytes changed')
 a.out.mkdir(exist_ok=False)
 def put(n,x):(a.out/n).write_bytes((json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
 put('CONFIG.json',cfg);put('ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0,remote_operations=0));put('RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=cfg['original_remote_raw_root'],aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),posthoc_natural_event_diagnostic=True,new_model_calls=0))
 inputs={}
 def load(p,h=None,lines=False):
  p=pathlib.Path(p);data=p.read_bytes();actual=hashlib.sha256(data).hexdigest();need(h is None or actual==h,'input SHA mismatch');inputs[str(p)]=dict(bytes=len(data),sha256=actual);return [json.loads(z) for z in data.splitlines() if z] if lines else json.loads(data)
 try:
  bank=pathlib.Path(cfg['collection_root']);receipt=load(bank/'COLLECTION_MANIFEST.json',cfg['collection_manifest_sha256']);need(receipt['all_bytes_equal'] and receipt['source_commit']==METHOD,'collection not actual bdfa');rows_by_path={r['path']:r for r in receipt['files']}
  def raw(cell,name,lines=False):
   key=cell+'/'+name;return load(bank/key,rows_by_path[key]['sha256'],lines)
  refs=load(cfg['reference_details'],cfg['reference_details_sha256']);withdrawals=load(cfg['withdrawals'],cfg['withdrawals_sha256']);primary=load(cfg['primary_gate'],cfg['primary_gate_sha256']);content=load(cfg['content_gate'],cfg['content_gate_sha256'])
  need(primary['status']=='PASS_COMPLETE_16_CELL_INDEPENDENT_PAIRED_RECOUNT' and content['gate']=='PASS_ALL16_272_ORIGINAL_AND_CONTENT_RECOUNT','prior full recount not PASS')
  plan=load(cfg['service_plan'],cfg['service_plan_sha256']);cases=[];ahead_cases=[];discard_cases=[]
  for cell in plan['cells']:
   sid=cell['source_id'];cid=cell['cell_id'];consumer=raw(cid,'consumer.jsonl',True)
   requested=[w for w in withdrawals if w['cell_id']==cid];ahead=[(ix,r) for ix,r in enumerate(consumer) if r['kind']=='canonical' and r['private_job'] is not None and r['visible_frontier']>r['certified_frontier']]
   ledger=raw(cid,'FULLSPEC_LEDGER.json') if cell['arm']=='two_full_spec_early' else {'discarded':[]}
   if not requested and not ahead and not ledger['discarded']:continue
   events=raw(cid,'events.jsonl',True);jobs={j['job_id']:j for j in raw(cid,'native_jobs.jsonl',True)};dispatch={e['job_id']:e for e in events if e['kind']=='dispatch'};early={e['job_id']:e for e in events if e['kind']=='asr_early'};hist=raw(cid,'CANONICAL_HISTORIES.json')[sid];hby={h['F']:h for h in hist};installs={e['job_id']:e for e in events if e['kind']=='canonical_install'};promotions={r['job_id']:r for r in ledger.get('promotions',[])}
   for w in requested:
    ix=w['row_index'];before=consumer[ix-1];after=consumer[ix];need(before['visible_frontier']==w['before']==96000 and after['visible_frontier']==after['certified_frontier']==w['after']==88000,'withdrawal row changed')
    parent_event=event_for_row(after,events,jobs);parentid=parent_event['job_id'];parent=jobs[parentid];viewid=before['private_job'];e,j,d=early_bound(viewid,early,jobs,dispatch);pe,pj,pd=early_bound(parentid,early,jobs,dispatch)
    need(parent['record']['start']==80000 and digest(parent['start'])==before['canonical_sha']==hby[80000]['state_sha256'],'old Root/start not bound')
    need(same(pe['projection']['end'],j['start']) and j['record']['start']==88000 and j['record']['end']==96000,'complete 80k->88k->96k conditional chain broken')
    need(parent_event['fullspec_promoted'] and promotions[parentid]['birth_canonical_sha']==pd['birth_canonical_sha'] and viewid not in promotions,'promotion rewrote ownership or invalid child promoted')
    need(e['projection']['end']['frontier']==96000 and before['text']==e['projection']['end']['transcript'] and before['certified_frontier']==80000,'actual private view not bound to chain')
    need(same(parent['end'],hby[88000]['state']) and after['canonical_sha']==digest(parent['end']) and after['text']==parent['end']['transcript'],'new Root/Consumer does not match actual parent')
    check_reference(parent,sid,refs);differences=sorted(k for k in j['start'] if not same(j['start'][k],parent['end'][k]));need(differences==['tokens','transcript'],'unexpected complete-cut mismatch fields')
    discarded=next(x for x in ledger['discarded'] if x['job_id']==viewid);proof=discarded['proof'];need(proof['kind']=='actual_canonical_disagrees_with_complete_start' and proof['expected_cut_sha']==digest(j['start']) and proof['actual_cut_sha']==digest(parent['end']) and proof['witness_frontier']==88000,'discard witness not actual complete same-F mismatch')
    need(viewid not in installs and all(h['state_sha256']!=digest(j['end']) for h in hist),'wrong branch was installed')
    successor=next(jj for jid,jj in jobs.items() if jid in installs and jj['record']['end']==96000);need(same(successor['start'],parent['end']),'actual successor did not restart from chosen Root');check_reference(successor,sid,refs)
    cases.append(dict(cell_id=cid,repeat=cell['repeat'],consumer_row_index=ix,certified_samples_before=80000,certified_samples_after=88000,visible_samples_before=96000,visible_samples_after=88000,winning_parent_job=parentid,discarded_job=viewid,old_Root_sha=before['canonical_sha'],frozen_start_sha=digest(j['start']),new_actual_Root_sha=digest(parent['end']),different_complete_cut_fields=differences,first_beam_text=j['start']['transcript'],actual_C_text=parent['end']['transcript'],actual_C_selected_append=parent['record']['selected_correction']['corrected_appended_text'],full_input_chain_verified=True,owned_job_and_epoch_preserved=True,discard_proof_verified=True,discarded_full_result_never_Canon_installed=True,subsequent_96k_original_reference_exact=True,classification='necessary_direct_complete_start_incompatibility_under_exact_contract',note='One acoustic correction pattern observed in two fresh timing runs; not two independent acoustic events'))
   for ix,after in ahead:
    before=consumer[ix-1];need(before['certified_frontier']==64000 and after['certified_frontier']==72000 and before['visible_frontier']==after['visible_frontier']==80000,'unexpected compatible preservation shape')
    parent_event=event_for_row(after,events,jobs);pid=parent_event['job_id'];parent=jobs[pid];vid=after['private_job'];e,j,d=early_bound(vid,early,jobs,dispatch);pe,pj,pd=early_bound(pid,early,jobs,dispatch)
    need(vid==before['private_job'] and before['text']==after['text']==e['projection']['end']['transcript'],'whole actual view/job not retained')
    need(d['birth_canonical_sha']==before['canonical_sha']==digest(parent['start'])==hby[64000]['state_sha256'],'older actual birth identity changed')
    need(promotions[vid]['birth_canonical_sha']==d['birth_canonical_sha'] and parent_event['fullspec_promoted'] and promotions[pid]['birth_canonical_sha']==pd['birth_canonical_sha'],'actual promotion changed original birth identity')
    need(same(pe['projection']['end'],parent['end']) and same(j['start'],parent['end']) and digest(j['start'])==after['canonical_sha']==hby[72000]['state_sha256'],'surviving suffix complete start not equal actual new Root')
    need(j['record']['start']==72000 and j['record']['end']==80000 and after['certified_frontier']<after['visible_frontier'],'private end was improperly certified')
    need(j['record']['model_start']<parent_event['observed']<j['record']['model_end'] and e['admitted_perf']<parent_event['observed'],'not an actual preexisting model-active private view')
    check_reference(parent,sid,refs);check_reference(j,sid,refs)
    ahead_cases.append(dict(cell_id=cid,repeat=cell['repeat'],consumer_row_index=ix,certified_seconds_before=4.0,certified_seconds_after=4.5,visible_seconds_before=5.0,visible_seconds_after=5.0,winning_parent_job=pid,retained_view_job=vid,older_birth_Root_sha=d['birth_canonical_sha'],new_Root_and_frozen_start_sha=digest(j['start']),whole_view_text=after['text'],complete_old_ancestor_chain_verified=True,complete_surviving_input_equals_actual_new_Root=True,unchanged_owned_job_identity_and_view_text=True,actually_model_active_at_parent_install=True,private_5s_end_not_certified_at_4_5s=True,eventual_original_5s_C_state_IDs_exact=True,classification='compatible_suffix_preserved_across_actual_Canonical_advance',reconciliation_record=parent_event['reconciliation']))
   for discarded in ledger['discarded']:
    jid=discarded['job_id'];need(any(c['cell_id']==cid and c['discarded_job']==jid for c in cases),'unexplained completed full-result discard');j=jobs[jid];need(jid not in installs,'discarded job installed');discard_cases.append(dict(cell_id=cid,job_id=jid,completed_full_result=True,never_Canon_installed=True,reason=discarded['proof']['kind'],expected_cut_sha=discarded['proof']['expected_cut_sha'],actual_cut_sha=discarded['proof']['actual_cut_sha'],dispatch_epoch=dispatch[jid]['dispatch_epoch'],original_birth_canonical_sha=dispatch[jid]['birth_canonical_sha']))
  need(len(cases)==len(withdrawals)==2 and len(ahead_cases)==1 and len(discard_cases)==2,'natural event scope changed')
  for p,record in inputs.items():need(sha(p)==record['sha256'],'input mutated while diagnosing')
  put('WITHDRAWALS.json',cases);put('COMPATIBLE_VIEW_PRESERVATION.json',ahead_cases);put('DISCARDED_FULL_RESULTS.json',discard_cases);put('INPUT_MANIFEST.json',inputs)
  summary=dict(status='PASS_NATURAL_NATIVE_EVENT_COMPLETE_CHAIN_AND_OWNERSHIP_RECONSTRUCTION',code_commit=commit,imported_actual_neural_source_commit=METHOD,withdrawal_observations=2,acoustic_withdrawal_patterns=1,completed_full_results_discarded_with_actual_same_F_start_witness=2,compatible_cross_Root_actual_whole_view_preservation_observations=1,compatible_view_withdrawals_in_these_events=0,new_model_calls=0,remote_operations=0,endpoints_unchanged=True,scope='Post-hoc natural witnesses only; not a new R x S ablation, natural prevalence estimate, or global guarantee.')
  put('SUMMARY.json',summary);put('GATE.json',summary);print(json.dumps(summary,indent=2))
 except BaseException:
  put('INPUT_MANIFEST.json',inputs);(a.out/'failure.txt').write_text(traceback.format_exc());put('GATE.json',dict(status='FAIL_NATURAL_EVENT_RECONSTRUCTION_PRESERVED',code_commit=commit));raise
if __name__=='__main__':main()
