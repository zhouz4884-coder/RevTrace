"""Read old actual fault-point facts as reference; never relabel to new source."""
import hashlib,json,shlex,sys
from pathlib import Path

E=Path(__file__).resolve().parents[1]
PY='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revtrace-streamcorrect-20261028/bin/python'
CODE=r'''
import hashlib,json,pathlib,struct
import soundfile as sf
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
root=B/'results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells'
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
rows=[];states=[]
for arm in ('conservative','fullcall'):
 for repeat in (0,1):
  cell=root/('SC_FORMAL_SHORT28_v1_BAC009S0908W0369_owner_after_durable_'+arm+'_r'+str(repeat));p=cell/'facts.wal';raw=p.read_bytes();pos=0;previous='0'*64;seq=0;found=None
  while pos<len(raw):
   begin=pos;assert raw[pos:pos+4]==b'RVN1';n=struct.unpack('>I',raw[pos+4:pos+8])[0];payload=raw[pos+8:pos+8+n];checksum=raw[pos+8+n:pos+40+n];assert len(checksum)==32 and hashlib.sha256(payload).digest()==checksum
   obj=json.loads(payload);assert canonical(obj)==payload and obj['sequence']==seq+1 and obj['previous']==previous;seq+=1;previous=checksum.hex();pos+=n+40
   if obj['kind']=='canonical' and obj['body']['source_id']=='BAC009S0908W0369' and obj['body']['next_state']['frontier']==32000:
    body=obj['body'];found=dict(transition_id=body['transition_id'],job_id=body['job']['job_id'],owner_epoch=body['owner_epoch'],journal_sequence=seq,frame_sha256=previous,offset=begin,end_offset=pos,parent_cut_sha256=digest(body['parent_state']),end_cut_sha256=digest(body['next_state']),original_full_record_sha256=digest(body['record']));states.append(body['next_state'])
  assert found
  rows.append(dict(cell_id=cell.name,wal_path=str(p),wal_bytes=len(raw),wal_sha256=hashlib.sha256(raw).hexdigest(),actual_fault_fact=found))
assert all(s==states[0] for s in states),'old actual cuts differ; never silently force equality'
config=json.loads((root/rows[0]['cell_id']/'CONFIG.json').read_bytes());s=next(s for s in config['settings']['sources'] if s['source_id']=='BAC009S0908W0369');p=pathlib.Path(s['path']);a,sr=sf.read(p,dtype='float32');assert sr==16000 and a.ndim==1 and len(a)==s['frames'];assert hashlib.sha256(p.read_bytes()).hexdigest()==s['audio_sha256']
wave=a.astype('<f4',copy=False)
print(json.dumps(dict(status='HISTORICAL_ACTUAL_MATCHED_INPUT_REFERENCE_NOT_NEW_SOURCE_FIXTURE',historical_execution_commit=config['settings']['source_commit'],source_id=s['source_id'],WAV_path=str(p),WAV_bytes=p.stat().st_size,WAV_file_sha256=s['audio_sha256'],full_float32_le_wave_sha256=hashlib.sha256(wave.tobytes()).hexdigest(),sample_rate=sr,source_frames=len(wave),postfault_start=32000,postfault_target=40000,is_last=False,postfault_float32_le_audio_slice_sha256=hashlib.sha256(wave[32000:40000].tobytes()).hexdigest(),postfault_slice_bytes=wave[32000:40000].nbytes,full_start_state=states[0],full_start_state_sha256=digest(states[0]),configuration_token_contract=config['settings']['backend']['contract'],actual_fact_bindings=rows,scope='Historical4f actual full-state/audio reference, read-only; new source fixture must be generated/frozen separately because execution source is embedded in full cut contract. No new model call or serving result.')))
'''

def main():
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    try:
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60)
        i.write(CODE);i.flush();i.channel.shutdown_write();raw,err=o.read(),e.read();rc=o.channel.recv_exit_status();assert rc==0,err.decode('utf8',errors='replace')
        x=json.loads(raw);x['reader_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        out=E/'review/LOADER_CONTROL_HISTORICAL_INPUT_REFERENCE_v2.json';assert not out.exists();out.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(path=str(out),status=x['status'],full_start_state_sha256=x['full_start_state_sha256'],WAV_file_sha256=x['WAV_file_sha256'],postfault_float32_le_audio_slice_sha256=x['postfault_float32_le_audio_slice_sha256'],matched_old_cells=len(x['actual_fact_bindings']))))
    finally:c.close()

if __name__=='__main__':main()
