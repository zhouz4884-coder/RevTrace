"""Prior actual BDFA protected calls -> fixed original-task reference, no replay."""
import argparse,copy,datetime,hashlib,json,pathlib,platform,subprocess,sys
BDFA='bdfa3b1307d267a5a4caf6484e1ad465c39a592e'
FIELDS={'audio_segments','tokens','context','last_attend_frame','detected_language','initial_tokens','initial_token_length','sot_index','decoder_type','contract','frontier','transcript'}
def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def lines(p):return [json.loads(x) for x in pathlib.Path(p).read_bytes().splitlines() if x.strip()]
def need(ok,message):
 if not ok:raise ValueError(message)
def put(p,x):pathlib.Path(p).write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
def same(a,b):return canonical(a)==canonical(b)
def cut_ok(state):
 need(set(state)==FIELDS,'incomplete or unknown complete state field');need(state['contract']['stage_execution']['source_commit']==BDFA,'reference state is not actual BDFA execution; never relabel99')

def extract(source,jobs,histories,wal,dispatch,events,provenance):
 sid=source['source_id'];n=source['frames'];expected=list(range(8000,n,8000))+[n]
 need(set(histories)=={sid},'history source differs');history=histories[sid]
 need([h['F'] for h in history]==expected and [w['state']['frontier'] for w in wal]==expected,'Canonical/EOS history incomplete or changed')
 need(len(jobs)==len(dispatch)==len(expected),'unexpected prior work; fixed conservative reference must contain one full call per frontier')
 byend={j['end']['frontier']:j for j in jobs};need(len(byend)==len(jobs),'duplicate completed target')
 dmap={d['job_id']:d for d in dispatch};installs=[e for e in events if e.get('kind')=='canonical_install'];need(len(installs)==len(expected),'actual install count differs');imap={e['job_id']:e for e in installs};need(len(dmap)==len(imap)==len(expected),'job IDs reused')
 previous=None;out=[]
 for h,w,F in zip(history,wal,expected):
  need(F in byend,'missing complete job');j=byend[F];r=j['record'];start=j['start'];end=j['end'];cut_ok(start);cut_ok(end);jid=j['job_id'];need(jid in dmap and jid in imap,'call lacks dispatch or actual installation');d=dmap[jid]
  need(j['kind']=='completed' and j['mode']=='authority' and j['source_id']==sid and j['worker']==j['physical_channel_worker']==d['worker'],'changed physical/source full-call identity')
  need(r['role']=='authority' and r['candidate_handoff'] is False and r['start_state']==digest(start) and r['end_state']==digest(end),'not original complete C/U or cut binding changed')
  need(r['start']==start['frontier'] and r['end']==F and F==min(n,start['frontier']+8000),'original cadence changed')
  need(start['contract']['source_sha']==source['audio_sha256'] and same(start['contract'],end['contract']),'source/audio contract changed')
  need((previous is None and start['frontier']==0 and start['transcript']=='') or (previous is not None and same(start,previous)),'complete input/output dependency gap')
  need(d['source_id']==sid and d['start']==start['frontier'] and d['end']==F and d['start_sha']==digest(start) and d['dispatch_epoch']==j['dispatch_epoch']==w['dispatch_epoch'],'dispatch input/epoch changed')
  need(same(h['state'],end) and same(w['state'],end) and h['state_sha256']==w['state_sha256']==digest(end),'three independent actual-state records differ')
  need('selected' in w and same(w['selected'],r['selected_correction']) and h['token_ids']==r['token_ids'],'original C/IDs differ between actual records')
  need(r['model_start']<=r['model_end']<=j['received_perf']<=imap[jid]['observed'] and d['dispatched_perf']<=r['model_start'],'actual execution/receipt/install ordering differs')
  out.append(dict(source_id=sid,speaker_id=source['speaker_id'],start=start['frontier'],end=F,full_input_sha=digest(start),original_full_start_cut=copy.deepcopy(start),original_full_cut=copy.deepcopy(end),original_full_result=copy.deepcopy(r),reference_only=True,provenance=dict(provenance,actual_execution_source_commit=BDFA,prior_job_id=jid,prior_worker=j['worker'],prior_dispatch_epoch=j['dispatch_epoch'],reference_origin='Fixed prior conservative r0 actual original full ASR/C/U; not rerun, source relabelling or service-performance replay.')))
  previous=end
 return out

def combine(old,new,provenance):
 old_ids={r['source_id'] for r in old};need(not old_ids & {r['source_id'] for r in new},'old/new reference source overlap')
 seen=set();result=[]
 for row in new:
  cut_ok(row['original_full_start_cut']);cut_ok(row['original_full_cut']);key=row['source_id'],row['end'];need(key not in seen,'duplicate existing reference frontier');seen.add(key)
  need(row['full_input_sha']==digest(row['original_full_start_cut']) and row['end']==row['original_full_cut']['frontier'] and row['end']>row['original_full_start_cut']['frontier'],'existing complete reference binding changed')
  copied=copy.deepcopy(row);copied['combined_reference_provenance']=provenance;result.append(copied)
 result.extend(old);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();cfg=read(a.config);m=read(a.manifest);root=pathlib.Path(__file__).resolve().parent
 commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip();need(commit==m['source_commit']==cfg['code_commit'],'exporter source differs');need(not subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip(),'exporter source dirty')
 tracked=set(subprocess.check_output(['git','-C',str(root),'ls-files'],text=True).splitlines());need(tracked=={r['path'] for r in m['files']},'exporter manifest incomplete')
 for row in m['files']:need(sha(root/row['path'])==row['sha256'] and (root/row['path']).stat().st_size==row['bytes'],'exporter bytes changed')
 a.out.mkdir();put(a.out/'CONFIG.json',cfg);put(a.out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),model_calls=0))
 put(a.out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],code_commit=commit,frozen_config=str(a.config),config_sha256=sha(a.config),environment_record=str(a.out/'ENVIRONMENT.json'),environment_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=cfg['original_remote_raw_root'],bounded_local_inputs=cfg['inputs'],aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json'),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),model_calls=0,serving_metrics_computed=False))
 try:
  for row in cfg['inputs'].values():need(sha(row['path'])==row['sha256'] and pathlib.Path(row['path']).stat().st_size==row['bytes'],'fixed actual input bytes differ')
  paths={k:v['path'] for k,v in cfg['inputs'].items()};oldcfg=read(paths['old_config']);run=read(paths['old_run_record']);need(oldcfg['arm']=='two_full_early' and oldcfg['repeat']==0 and oldcfg['settings']['source_commit']==run['code_commit']==BDFA,'not fixed prior BDFA conservative r0')
  source=oldcfg['settings']['sources'][0];need(source['source_id']=='BAC009S0764W0209' and source['frames']==129088,'fixed regression source changed')
  prior_gate=read(paths['old_gate']);need(prior_gate['status'].startswith('PASS'),'prior actual neural cell incomplete')
  newgate=read(paths['new_reference_gate']);new=read(paths['new_reference_details']);need(newgate['status'].startswith('PASS') and newgate['imported_model_runtime_commit']==BDFA and newgate['reference_details_sha256']==sha(paths['new_reference_details']),'existing new4 reference gate differs')
  provenance=dict(input_sha256={k:v['sha256'] for k,v in cfg['inputs'].items()},original_remote_raw_root=cfg['original_remote_raw_root'])
  old=extract(source,lines(paths['old_jobs']),read(paths['old_histories']),lines(paths['old_wal']),read(paths['old_dispatch']),lines(paths['old_events']),provenance);need(len(old)==17 and len(new)==68,'fixed17+68 scope differs');merged=combine(old,new,dict(existing_reference_actual_runtime_commit=BDFA,existing_reference_details_sha256=sha(paths['new_reference_details']),existing_reference_gate_sha256=sha(paths['new_reference_gate'])))
  need(len(merged)==85 and len({r['source_id'] for r in merged})==5,'combined85 scope differs');put(a.out/'SOURCE0_DETAILS.json',old);put(a.out/'DETAILS.json',merged);put(a.out/'INPUT_MANIFEST.json',cfg['inputs'])
  summary=dict(status='PASS_PRIOR_ACTUAL_BDFA_SHORT85_REFERENCE_EXPORT',code_commit=commit,measured_native_source_commit=BDFA,source0_calls=17,existing_new4_calls=68,combined_calls=85,source_ids=sorted({r['source_id'] for r in merged}),reference_details_sha256=sha(a.out/'DETAILS.json'),source0_details_sha256=sha(a.out/'SOURCE0_DETAILS.json'),all_original_full_states_C_IDs_and_cadence_cross_checked=True,all_reference_tags_remain_actual_BDFA=True,model_calls=0,serving_metrics_computed=False,scope='Reuses fixed prior real protected calls and original offline references only for future full-task checks. Not a new acoustic sample, numerical rerun, performance replay or relabelled99 execution.')
  put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',summary);print(json.dumps(summary,indent=2))
 except BaseException as e:put(a.out/'GATE.json',dict(status='FAIL_SHORT_REFERENCE_EXPORT_PRESERVED',code_commit=commit,error_type=type(e).__name__,reason=str(e),model_calls=0));raise
if __name__=='__main__':main()
