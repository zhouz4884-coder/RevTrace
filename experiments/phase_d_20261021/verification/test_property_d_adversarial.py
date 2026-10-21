"""Independent CPU protocol attacks, not naturally observed faults."""
import hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'sdk/src'))
from revtrace.certified_display import validate_bound_text,replay_bound_text,text_sha,ContinuityView
from revtrace.dgft import digest_tokens
spec=importlib.util.spec_from_file_location('d_cpu_fixture',W/'sdk/tests/test_certified_display.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def bound_event():
 job={'prompt_tokens':[],'chunk_id':0,'language':'English'};Z=[ord(c) for c in '你好🙂']+[0];P,text=f.render()(job,Z);r={'token_ids':Z,'state_tokens':P,'text':text};proof=validate_bound_text(f.render(),job,r)
 return {'committed_text':text,'text_binding':proof,'certificate':{'display_sha256':digest_tokens(Z),'feedback_state_sha256':digest_tokens(P),'prompt_sha256':digest_tokens([])}}
@pytest.mark.parametrize('attack',['text_only','text_and_digest','wrong_Z','wrong_parent'])
def test_recovery_render_binding_not_just_frame_hash(attack):
 e=bound_event()
 if attack in ['text_only','text_and_digest']:e['committed_text']='ALTERED'
 if attack=='text_and_digest':e['text_binding']['text_sha256']=text_sha('ALTERED')
 if attack=='wrong_Z':e['text_binding']['render_inputs']['token_ids']=[97,0]
 if attack=='wrong_parent':e['text_binding']['render_inputs']['prompt_tokens']=[ord('x')]
 with pytest.raises(ValueError):replay_bound_text(f.render(),e)
def test_checksum_valid_wrong_text_wal_fails_d1_restart(tmp_path):
 p=tmp_path/'d.wal';s=f.build(p);s.run();s.close();data=p.read_bytes();pos=0;previous='';parts=[]
 while pos<len(data):
  n=int.from_bytes(data[pos:pos+4],'big');r=json.loads(data[pos+4:pos+4+n]);pos+=n+36;r['previous_sha256']=previous
  if r['kind']=='commit':r['event']['committed_text']='ALTERED';r['event']['text_binding']['text_sha256']=text_sha('ALTERED')
  payload=json.dumps(r,sort_keys=True,separators=(',',':')).encode();h=hashlib.sha256(payload).digest();parts.append(len(payload).to_bytes(4,'big')+payload+h);previous=h.hex()
 p.write_bytes(b''.join(parts))
 program="import importlib.util,sys; from pathlib import Path; w=Path(sys.argv[1]);sys.path.insert(0,str(w/'sdk/src'));sp=importlib.util.spec_from_file_location('f',w/'sdk/tests/test_certified_display.py');f=importlib.util.module_from_spec(sp);sp.loader.exec_module(f);f.build(Path(sys.argv[2]))"
 child=subprocess.run([sys.executable,'-B','-c',program,str(W),str(p)],capture_output=True,text=True)
 assert child.returncode!=0 and 'recovered render/text mismatch' in child.stderr
 # Fail-stop process exit releases OS locks; no claim of same-process retry API.
def test_certified_lane_can_revise_without_audio_rollback():
 v=ContinuityView('two_lane');v.consume({'kind':'run-start','t0_perf':1})
 for version,text in [(1,'I saw a cat'),(2,'I saw a dog')]:
  v.consume({'kind':'commit','session_id':0,'version':version,'segment_id':str(version),'audio_end_sample':version*32000,'next_prompt_tokens':[version]})
  row=v.consume({'kind':'canonical-display','session_id':0,'time':version,'displayed':version,'display_revision':version,'version':version,'transaction_id':str(version),'audio_end_sample':version*32000,'text':text,'text_sha256':text_sha(text),'canonical_projection_sha256':digest_tokens([version])})
 assert row['audio_rollback_samples']==0 and row['erased_characters']>0 and row['certified_text']=='I saw a dog'
