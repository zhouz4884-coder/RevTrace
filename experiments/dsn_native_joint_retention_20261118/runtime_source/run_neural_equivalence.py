"""Four original sources: protected candidates versus actual full native C/U."""
import argparse,pathlib,json,hashlib,subprocess,sys,os,time,datetime,platform,multiprocessing as mp,traceback
R=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,x):pathlib.Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def verify(manifest):
 m=read(manifest);assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==m['source_commit'];assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain','--untracked-files=all'],text=True).strip();assert set(subprocess.check_output(['git','-C',str(R),'ls-files'],text=True).splitlines())=={r['path'] for r in m['files']}
 for r in m['files']:
  data=(R/r['path']).read_bytes();assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
 return m['source_commit']
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();plan=read(a.plan);commit=verify(a.manifest);assert plan['source_commit']==commit
 a.out.mkdir(exist_ok=False);put(a.out/'CONFIG.json',plan);put(a.out/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),precision='public inference FP32 default; no autocast or TF32',actual_worker_environment='recorded at readiness by native worker'))
 put(a.out/'RUN_RECORD.json',dict(experiment_id=plan['experiment_id'],code_commit=commit,frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=sha(a.out/'CONFIG.json'),environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=sha(a.out/'ENVIRONMENT.json'),raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
 from stage_worker import worker_main
 from stage_packet import CandidatePacket
 from candidate_bridge import semantic_packet_signature
 from feedback_contract import FeedbackCut
 ctx=mp.get_context('spawn');q=ctx.Queue();channels={};workers={};pending={};packets={};projections={};records=[];a.out.joinpath('packets').mkdir()
 settings=plan['settings'];assert settings['corrector_dtype']=='float32';assert len(settings['sources'])==4
 for name,gpu,mode in [('authority',0,'authority'),('producer',1,'protected_asr_stage')]:
  c=ctx.Queue();w=ctx.Process(target=worker_main,args=(name,gpu,mode,settings,c,q));w.start();channels[name]=c;workers[name]=w
 def get():
  r=q.get(timeout=180);r['received_perf']=time.perf_counter()
  if r['kind']=='failed':raise RuntimeError(r['worker']+': '+r['traceback'])
  if r['kind']=='candidate':
   packet=CandidatePacket.from_wire(r['candidate_wire']);dest=a.out/'packets'/(r['job_id']+'.json');assert not dest.exists();dest.write_bytes(r['candidate_wire']);packets[r['job_id']]=packet
  if r['kind'] in ('candidate','asr_early'):projections[r['job_id']]=r['projection']
  return r
 def wait_complete(job):
  while True:
   r=get()
   if r['kind']=='completed' and r['job_id']==job:return r
   assert r['kind'] in ('candidate','asr_early'),'unexpected worker response'
 try:
  ready={}
  while len(ready)<2:
   r=get();assert r['kind']=='ready';ready[r['worker']]=r
  assert ready['authority']['runtime_identity']==ready['producer']['runtime_identity'];assert ready['authority']['neural_ready_warmup']['neural_C_confirmed'] is True
  assert all(x['neural_ready_warmup']['reset_to_genesis'] and not x['neural_ready_warmup']['warmup_packet_admitted'] for x in ready.values());put(a.out/'READY.json',ready)
  sequence=0;repeat_done=False
  for source in settings['sources']:
   sid=source['source_id'];start=FeedbackCut(ready['authority']['initials'][sid]);assert start.same(FeedbackCut(ready['producer']['initials'][sid]))
   for end in list(range(8000,source['frames'],8000))+[source['frames']]:
    job=f'eq_{sequence:04d}';sequence+=1;common=dict(source_id=sid,start=start.state,end=end)
    channels['producer'].put(dict(common,kind='full',job_id=job+'_producer',capture_packet=True));proposed=wait_complete(job+'_producer');candidate=packets.get(job+'_producer')
    channels['authority'].put(dict(common,kind='full',job_id=job+'_full',capture_packet=True));full=wait_complete(job+'_full');full_packet=packets.get(job+'_full');entry=dict(source_id=sid,start=start.frontier,end=end,full_input_sha=start.sha256,candidate_present=candidate is not None,original_full_result=full['record'],predicted_end_equal=proposed['end']==full['end'],candidate_packet_bytes=candidate.bytes if candidate else 0,original_full_cut=full['end'])
    if candidate is not None:
     projection=projections[job+'_producer'];entry['stage_projection_equal_original_identity_closed_node']=projection['end']==proposed['end'] and projection['token_ids']==proposed['record']['token_ids'];assert entry['stage_projection_equal_original_identity_closed_node'],'early ASR projection differs from actual original private identity tail'
     assert full_packet is not None;equal=semantic_packet_signature(candidate)==semantic_packet_signature(full_packet);entry['full_semantic_packet_equal']=equal;assert equal,'actual protected candidate packet differs from original full C/U semantic input'
     channels['authority'].put(dict(common,kind='project',job_id=job+'_projection',packet_wire=candidate.wire()));packet_projection=wait_complete(job+'_projection');entry['packet_projection_equal_original_identity_closed_node']=packet_projection['end']==proposed['end'] and packet_projection['record']['token_ids']==proposed['record']['token_ids'];assert entry['packet_projection_equal_original_identity_closed_node'],'packet-derived projection differs from actual original private identity tail'
     channels['authority'].put(dict(common,kind='consume',job_id=job+'_consume',packet_wire=candidate.wire()));consumed=wait_complete(job+'_consume');entry['consume_result']=consumed['record'];entry['full_C_equal']=full['record']['selected_correction']==consumed['record']['selected_correction'];entry['returned_ids_equal']=full['record']['token_ids']==consumed['record']['token_ids'];entry['closed_state_equal']=full['end']==consumed['end'];assert entry['full_C_equal'] and entry['returned_ids_equal'] and entry['closed_state_equal'],'candidate C/U is not equivalent to original full execution'
     if not repeat_done and sid==settings['sources'][0]['source_id'] and end==32000:
      channels['authority'].put(dict(common,kind='consume',job_id=job+'_repeat',packet_wire=candidate.wire()));again=wait_complete(job+'_repeat');assert again['end']==consumed['end'] and again['record']['selected_correction']==consumed['record']['selected_correction'];entry['same_input_tail_repeat_equal']=True;repeat_done=True
    else:assert full_packet is None,'early native path differs';entry['fallback_full_preserved']=True
    records.append(entry);start=FeedbackCut(full['end']);put(a.out/'PROGRESS.json',dict(completed=len(records),sources=4,candidate_equivalent=sum(r['candidate_present'] for r in records)));put(a.out/'DETAILS.json',records)
  assert len(records)==69 and repeat_done
  for c in channels.values():c.put(None)
  drained=set()
  while len(drained)<2:
   r=get();assert r['kind']=='drained';drained.add(r['worker'])
  for w in workers.values():w.join(30);assert w.exitcode==0
  summary=dict(status='PASS_FOUR_SOURCE_PROTECTED_PACKET_ORIGINAL_C_U_EQUIVALENCE',source_commit=commit,full_steps=len(records),candidate_C_U_comparisons=sum(x['candidate_present'] for x in records),fallback_original_early_steps=sum(not x['candidate_present'] for x in records),predicted_end_differs_but_candidate_valid=sum(x['candidate_present'] and not x['predicted_end_equal'] for x in records),same_input_tail_repeat=True,all_full_C_ids_closed_states_equal=True,full_semantic_packet_equal=True,identity_stage_and_packet_projection_equal_original_full_identity=True,typed_ASR_projection_not_learned_C_completion=True,debug_logits_equality_claimed=False,actual_serving_cells=0,scope='neural same-input control, not online serving; all four original sources included')
  put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',summary);print(json.dumps(summary,indent=2))
 except BaseException:
  (a.out/'failure.txt').write_text(traceback.format_exc());put(a.out/'GATE.json',dict(status='FAIL_PROTECTED_STAGE_EQUIVALENCE_PRESERVED',completed=len(records)));raise
 finally:
  for c in channels.values():c.put(None)
  for w in workers.values():
   w.join(10)
   if w.is_alive():w.terminate();w.join(10)
if __name__=='__main__':main()
