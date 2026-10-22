"""Read-only independent WAL/source/receipt/clock/power recomputation. CPU only."""
from pathlib import Path
import copy,csv,hashlib,json,shutil,statistics,sys,tempfile
B=Path(sys.argv[1]);P=B/'projects/revtrace_opportunity_20261022';O=B/'results/revtrace/opportunity_20261022';D=B/'results/revtrace/phaseD_20261021';S=B/'projects/revtrace_phaseD_20261021/continuity_v6'
sys.path[:0]=[str(S/'src'),str(S/'scripts')]
from revtrace.dgft import FeedbackTransactionState,digest_tokens
from revtrace.durable_journal import DurableCommitJournal
from revtrace.certified_display import TrustedQwenRender,replay_bound_text
from transformers import AutoProcessor,GenerationConfig
import qwen_asr
from qwen_asr import parse_asr_output
from reconstruction import reconstruct_next
from adoption_core import semantic
from dataclasses import replace
import soundfile as soundfile,numpy as np
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
model=B/'models/Qwen3-ASR-1.7B';proc=AutoProcessor.from_pretrained(model,local_files_only=True);eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id
render=TrustedQwenRender(proc.tokenizer,parse_asr_output,[eos] if isinstance(eos,int) else eos,256)
frozen=json.loads((D/'RAW_EVIDENCE_INDEX.json').read_text());prior={r['path']:r['sha256'] for r in frozen['files']};A=json.loads((O/'A_SUMMARY_v3.json').read_text());matches=0
for r in A['raw_hashes']:
 for name,key in [('events.jsonl','events_sha256'),('worker_records.jsonl','worker_records_sha256')]:
  path=D/r['cell']/name;assert sha(path)==r[key]==prior[str(path)];matches+=1
src=json.loads((S/'SOURCE_MANIFEST.json').read_text())
# Source manifest shapes are explicit; do not silently assume a list layout.
sf=src.get('files',src.get('source_sha256'))
if isinstance(sf,dict):source_rows=[{'path':k,'sha256':v} for k,v in sf.items()]
else:source_rows=sf
assert isinstance(source_rows,list)
source_checked=0
for r in source_rows:
 name=r.get('path',r.get('file'));wanted=r['sha256']
 if name=='SOURCE_MANIFEST.json':continue
 assert sha(S/name)==wanted,name;source_checked+=1
weights=[]
for p in sorted(model.glob('*.safetensors')):weights.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
priorweights=json.loads((D/'State-continuity_PREFLIGHT.json').read_text())['model_assets'];assert {Path(r['path']).name:r['sha256'] for r in weights}=={r['file']:r['sha256'] for r in priorweights}
outrows=[];raw=[];completed=0;started=0;seedcalls=0;energy_corrections=[];reconstruction_checks=[]
for campaign,expectedn in [('B_gpu_v2',18),('B_gpu_nonempty',4)]:
 summary=json.loads((O/campaign/'SUMMARY.json').read_text());assert len(summary['rows'])==expectedn and summary['all_Z_P_text_same_input_oracles_equal']
 oracle=set()
 for cell in sorted((O/campaign).iterdir()):
  if not (cell/'result.json').exists():continue
  cfg=json.loads((cell/'config.json').read_text());r=json.loads((cell/'result.json').read_text());coord=json.loads((cell/'new_coordinator.json').read_text());registry=json.loads((cell/'SUPERVISOR_RECORDS.json').read_text());views=[json.loads(l) for l in (cell/'consumer.jsonl').read_text().splitlines()];power=json.loads((cell/'power.json').read_text())
  assert r['status']=='COMPLETE_BOUNDED_GPU_FEASIBILITY';assert views[0]['observed_perf']==coord['first_certified_consumer_perf'];assert abs(r['first_certified_consumer_RTO']-views[0]['observed_perf']+r['fault_perf'])<1e-8
  expectedstate=FeedbackTransactionState(0,1,'coarse',contract_digest=cfg['contract_digest'],canonical_runtime_digest=cfg['runtime_digest'])
  before=sha(cell/'ledger.wal')
  with tempfile.TemporaryDirectory(prefix='cpu-replay-',dir=O) as td:
   copied=Path(td)/'ledger.wal';shutil.copy2(cell/'ledger.wal',copied)
   with DurableCommitJournal(copied,[expectedstate]) as j:
    states=j.states();events=[e for e in j.events() if e.get('event')=='canonical-segment-committed'];state=states[0]
    for e in events:replay_bound_text(render,e)
    assert len(events)==(2 if campaign.endswith('nonempty') else 1)
    assert state.prompt_tokens==tuple(r['P']) and state.stable_token_segments[-1]==tuple(r['Z'])
    assert views[-1]['certified_text']==events[-1]['committed_text']==r['text']
    assert views[-1]['certified_frontier']==state.audio_frontier_window
    assert len(state.committed_segment_ids)==len(set(state.committed_segment_ids))
  assert sha(cell/'ledger.wal')==before
  oracle.add(hashlib.sha256(json.dumps([r['Z'],r['P'],r['text']]).encode()).hexdigest())
  rs=list(registry['records'].values());done=[v for v in rs if v['result'] is not None]
  manifest=json.loads((B/'datasets/revtrace/phaseD_20261021/manifest.json').read_text());spec=dict(manifest['sessions'][0],session_id=0);wav,sr=soundfile.read(spec['path'],dtype='float32');assert sr==16000;audio=np.asarray(wav,dtype='<f4').tobytes()
  oldrec=min(rs,key=lambda v:v['dispatch_epoch']);parentP=events[0]['text_binding']['render_inputs']['state_tokens'] if campaign.endswith('nonempty') else []
  parent=replace(expectedstate,checkpoint_id=1 if campaign.endswith('nonempty') else 0,prompt_tokens=tuple(parentP),audio_frontier_window=96000 if campaign.endswith('nonempty') else 0,contract_epoch=oldrec['dispatch_epoch'])
  rebuilt=reconstruct_next(parent,spec,audio,cfg['contract'],cfg['contract_digest'],cfg['runtime_digest']);assert rebuilt==semantic(oldrec['job'])
  reconstruction_checks.append({'cell':str(cell),'from_actual_WAL_parent':True,'fixed_manifest_audio_hash_verified':True,'all_logical_input_fields_equal':True,'not_execution_origin_attestation':True})
  for v in rs:
   assert v['supervisor_id']==cfg['supervisor_id'] and v['source_role']=='authority'
   assert hashlib.sha256(json.dumps(v['job'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['job_sha256']
   if v['result'] is None:continue
   z=v['result'];assert hashlib.sha256(json.dumps(z,sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['result_sha256']
   assert z['runtime_digest']==cfg['runtime_digest'] and z['prefix_audio_sha256']==v['job']['prefix_audio_sha256']
   assert z['job_id']==v['job']['job_id'];assert z['model_started_perf']<=z['model_completed_perf']<=z['completed_perf']
   Pnew,text=render(v['job'],z['token_ids']);assert Pnew==z['state_tokens'] and text==z['text']
  if r['phase']=='wal':assert len(rs)==1 and r['restored_WAL_without_generation'] and not r['adopted']
  elif r['method']=='adopt':assert len(rs)==1 and r['adopted'] and done[0]['dispatch_epoch']<coord['state']['contract_epoch']
  else:assert len(rs)==2 and not r['adopted']
  if r['method'] in ['strict','adopt']:
   assert len({v['worker_incarnation'] for v in rs})==1
  if r['phase']=='running' and r['method']!='cold':
   old=min(rs,key=lambda v:v['dispatch_epoch']);assert old['result']['model_started_perf']<=r['fault_perf']<=old['result']['model_completed_perf']
  # Independently integrate only the sample-supported window; disclose coverage.
  a,b=r['fault_perf'],coord['first_certified_consumer_perf'];energy=0.
  for l,u in zip(power,power[1:]):
   lo,hi=max(a,l['time']),min(b,u['time'])
   if hi<=lo:continue
   def watts(t):return l['watts']+(u['watts']-l['watts'])*(t-l['time'])/(u['time']-l['time'])
   energy+=(watts(lo)+watts(hi))*(hi-lo)/2
  delta=energy-r['recovery_GPU_energy_J']
  if abs(delta)>1e-6:energy_corrections.append({'cell':str(cell),'live_estimator_J':r['recovery_GPU_energy_J'],'final_raw_recomputed_J':energy,'difference_J':delta,'reason':'power thread could append a final sample after live estimator snapshot; original result preserved'})
  coverage=max(0,min(b,power[-1]['time'])-max(a,power[0]['time']))/(b-a)
  row={k:r[k] for k in ['phase','method','repeat','first_certified_consumer_RTO','ledger_recovery_seconds','initial_worker_init_seconds','recovery_worker_init_seconds','old_job_remaining_GPU_model_seconds','dispatches','completed_GPU_generations','adopted','restored_WAL_without_generation','GPU_peak_MiB']}
  row.update(campaign=campaign,energy_sample_supported_J=energy,original_live_energy_J=r['recovery_GPU_energy_J'],recomputed_energy_correction_J=delta,energy_window_coverage=coverage,energy_not_full_window_if_coverage_less_than_one=coverage<1,canonical_installs=len(events),epoch_at_first_consumer=coord['state']['contract_epoch'],seed_parent_present=campaign.endswith('nonempty'))
  outrows.append(row);completed+=len(done);started+=len(rs)
  if (cell/'SEED_PARENT.json').exists():
   seed=json.loads((cell/'SEED_PARENT.json').read_text());assert seed['state_checkpoint']==1 and seed['state_F']==96000 and seed['state_P'];seedcalls+=1
  for p in cell.iterdir():
   if p.is_file():raw.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
 assert len(oracle)==1
with (O/'B_INDEPENDENT_CELLS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(outrows[0]));w.writeheader();w.writerows(outrows)
decision={'status':'PASS_INDEPENDENT_SOURCE_RENDER_WAL_RECEIPT_CLOCK_AUDIT_WITH_ENERGY_LIMITATION','completed_GPU_fault_trials':len(outrows),'logical_job_reconstruction_checks':reconstruction_checks,'prior_A_trace_hashes_checked':matches,'frozen_runtime_source_files_checked':source_checked,'completed_target_GPU_generations':completed,'started_target_GPU_jobs':started,'additional_completed_seed_parent_generations':seedcalls,'all_same_input_oracles_equal_within_each_campaign':True,'failed_pilot_preserved':(O/'B_gpu/STOP.json').exists(),'energy_live_field_corrections':energy_corrections,'energy_caveat':'use independent final raw reintegration only; sample-supported integral, coverage column mandatory, short-window full energy not established','model_weights_postflight_match_prior_frozen_hashes':weights,'weight_verification_timing':'full weights postflight, JSON/parser/tokenizer assets validated by original worker before GPU calls','raw_files':raw,'no_new_GPU_calls':True}
(O/'INDEPENDENT_AUDIT.json').write_text(json.dumps(decision,indent=2)+'\n');print(json.dumps({k:v for k,v in decision.items() if k not in ['raw_files','model_weights_postflight_match_prior_frozen_hashes']}))
