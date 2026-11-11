"""Freeze last-four metadata and reuse the unchanged measured-reference recipe."""
from pathlib import Path
import copy,hashlib,importlib.util,json
E=Path(__file__).resolve().parents[1];R=E.parents[1];D=E/'baseline_ops/ROOT_LAST4_REFERENCE_V1';D.mkdir(parents=True,exist_ok=False)
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111';RP=P+'/root_last4_reference_v1';O=B+'/results/revtrace/dsn_strengthening_v16_20261111/REFERENCE_LAST4_V1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,x):
 with Path(p).open('x',encoding='utf8')as f:json.dump(x,f,indent=2);f.write('\n')
bankpath=R/'experiments/dsn_native_confirmation_20261102/confirmation/SERVICE_PLAN_v1.json';bank=json.loads(bankpath.read_bytes())['sources'];bank=sorted(bank,key=lambda s:(s['speaker_id'],s['source_id']));sources=copy.deepcopy(bank[4:8]);assert [s['speaker_id']for s in sources]==['S0907','S0912','S0914','S0915']
receipt=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/REFERENCE_SELECTION_RECEIPT.json').read_bytes());receipt.update(sources=sources,selection_use='existing_bank_reference_last_four',selection_rule='lexicographic original eight bank indices4:8; fixed before this reference generation; no replacement by any model outcome',comparison_bank_indices=[4,5,6,7],parent_local_bank_plan=dict(path=str(bankpath.resolve()),sha256=sha(bankpath)))
put(D/'SELECTION_RECEIPT.json',receipt)
hand=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json').read_bytes());oldplan=json.loads((E/'baseline_ops/PILOT_PREPARATION_V2/REFERENCE_PLAN.json').read_bytes())
plan=copy.deepcopy(oldplan);oldreceipt=plan['selection_receipt'];newreceipt=RP+'/SELECTION_RECEIPT.json';plan.update(experiment_id='REVTRACE_V16_LAST4_EXISTING_BANK_NEW_RUNTIME_REFERENCE_V1',selection_receipt=newreceipt,selection_receipt_sha256=sha(D/'SELECTION_RECEIPT.json'),sources=sources,expected_sources=4,expected_original_steps=sum(len(range(8000,s['frames'],8000))+1 for s in sources),cache_root=B+'/cache/revtrace_dsn_strengthening_v16_20261111/reference_last4_v1',raw_result_location=O)
del plan['inputs'][oldreceipt];plan['inputs'][newreceipt]=dict(bytes=(D/'SELECTION_RECEIPT.json').stat().st_size,sha256=sha(D/'SELECTION_RECEIPT.json'))
put(D/'REFERENCE_PLAN.json',plan)
step1=copy.deepcopy(hand['ordered_commands'][0]);step2=copy.deepcopy(hand['ordered_commands'][1])
for step in [step1,step2]:
 c=step['command'];c[c.index('--plan')+1]=RP+'/REFERENCE_PLAN.json'
 if '--prelaunch'in c:c[c.index('--prelaunch')+1]=RP+'/REFERENCE_PRELAUNCH.json'
 # make_prelaunch uses --out, run_reference uses --prelaunch.
 if '--out'in c:c[c.index('--out')+1]=RP+'/REFERENCE_PRELAUNCH.json'
step1['command'][step1['command'].index('--root-noarg-preflight')+1]=RP+'/root_gates/ROOT_NOARG_RUNTIME.json'
step1['command'][step1['command'].index('--driver-explicit-preflight')+1]=RP+'/root_gates/DRIVER_EXPLICIT.json'
step2['expected_receipt']=O+'/REFERENCE_RECEIPT.json'
hand.update(status='LAST4_METADATA_FROZEN_REFERENCE_INFERENCE_NOT_YET_RUN',ordered_commands=[step1,step2],reference_plan_sha256=sha(D/'REFERENCE_PLAN.json'),new_model_calls_so_far=0,new_GPU_trials_so_far=0)
for role,name in [('root_noarg_runtime','ROOT_NOARG_RUNTIME.json'),('driver_explicit','DRIVER_EXPLICIT.json')]:hand['Root_gates_to_upload'][role]['path']=RP+'/root_gates/'+name
put(D/'LAUNCH_HANDOFF.json',hand)
sp=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
with m.Remote()as c:
 c.python('from pathlib import Path\np=Path('+repr(RP)+')\np.mkdir(parents=True,exist_ok=False)\n(p/\'root_gates\').mkdir()\n')
 for name in ['SELECTION_RECEIPT.json','REFERENCE_PLAN.json','LAUNCH_HANDOFF.json']:c.put(D/name,RP+'/'+name)
 # Validate unchanged generator source and exact original selected WAV bytes.
 script='C='+repr(dict(source=hand['driver']['source_root'],receipt=newreceipt))+'\n'+r'''
from pathlib import Path
import hashlib,json,sys,wave
sys.path.insert(0,C['source']);from ref_common import sources_from_receipt
sources=sources_from_receipt(json.loads(Path(C['receipt']).read_bytes()))
for s in sources:
 assert hashlib.sha256(Path(s['path']).read_bytes()).hexdigest()==s['audio_sha256']
 with wave.open(s['path'],'rb')as f:assert f.getnframes()==s['frames']and f.getframerate()==16000 and f.getnchannels()==1 and f.getsampwidth()==2
print(json.dumps(dict(metadata_only=True,model_calls=0,sources=[s['source_id']for s in sources])))
'''
 out=c.python(script,timeout=30);(D/'METADATA_BYTE_READBACK.json').write_bytes(out+b'\n')
raw=(E/'ops/launch_reference_v2.py').read_text(encoding='utf8').replace('baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json','baseline_ops/ROOT_LAST4_REFERENCE_V1/LAUNCH_HANDOFF.json').replace('baseline_ops/PILOT_PREPARATION_V2/REFERENCE_PLAN.json','baseline_ops/ROOT_LAST4_REFERENCE_V1/REFERENCE_PLAN.json').replace('REFERENCE_FULL4_V2','REFERENCE_LAST4_V1')
target=E/'ops/launch_reference_last4_v1.py';assert not target.exists();target.write_text(raw,encoding='utf8')
print(out.decode())
