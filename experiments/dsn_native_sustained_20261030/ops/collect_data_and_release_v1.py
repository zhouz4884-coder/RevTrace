"""Collect only terminal bounded metadata and release the root-allocated data IO window."""
import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_native_sustained_20261030';P=B+'/projects/revtrace_dsn_native_sustained_20261030';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
handle=json.loads((F/'ACQUISITION_HANDLE_v1.json').read_bytes())
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
 code="""import hashlib,json,pathlib,sys,wave,datetime
O=pathlib.Path(OVALUE);h=json.loads((O/'ACQUISITION_HANDLE_v1.json').read_bytes());proc=pathlib.Path('/proc')/str(h['pid'])
alive=False;state='absent'
if proc.exists():
 fields=(proc/'stat').read_text().rsplit(')',1)[1].split();state=fields[0]
 if state!='Z':
  assert int(fields[19])==h['start_ticks'];assert hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'];alive=True
assert not alive,'same acquisition process still active; do not collect or restart'
out=pathlib.Path(h['raw_result_location']);gate=json.loads((out/'GATE.json').read_bytes())
assert gate['status']=='PASS_FROZEN_TWO_SPEAKER_48_PART_SYNTHETIC_LONG_INPUTS'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
receipt=json.loads((out/'SOURCE_RECEIPT.json').read_bytes());assert len(receipt['sources'])==2 and receipt['parts']==48 and receipt['model_calls']==0
for source in receipt['sources']:
 assert sha(source['path'])==source['audio_sha256']
 with wave.open(source['path']) as w:
  assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==16000 and w.getnframes()==source['frames'];pcm=w.readframes(w.getnframes())
 assert hashlib.sha256(pcm).hexdigest()==source['PCM_sha256']
 offset=0;pieces=[]
 for part in source['parts']:
  assert sha(part['path'])==part['audio_sha256'] and part['start_sample']==offset
  with wave.open(part['path']) as w:
   assert w.getnchannels()==1 and w.getframerate()==16000 and w.getsampwidth()==2 and w.getnframes()==part['frames'];piece=w.readframes(w.getnframes())
  assert hashlib.sha256(piece).hexdigest()==part['PCM_sha256'];pieces.append(piece);offset+=part['frames'];assert part['end_sample']==offset
 assert pcm==b''.join(pieces) and offset==source['frames']
 assert source['reference']==' '.join(p['reference'] for p in source['parts'])
names=['CONFIG.json','ENVIRONMENT.json','RUN_RECORD.json','PROGRESS.json','SOURCE_RECEIPT.json','SUMMARY.json','GATE.json'];files=[dict(path=n,bytes=(out/n).stat().st_size,sha256=sha(out/n)) for n in names]
release=dict(status='PASS_ALL48_PARTS_AND_TWO_SYNTHETIC_STREAMS_BYTE_VERIFIED_IO_RELEASED',observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),acquisition_process_exited=True,process_state=state,source_commit=h['source_commit'],config_sha256=h['config_sha256'],raw_result_location=str(out),source_receipt_sha256=sha(out/'SOURCE_RECEIPT.json'),gate_sha256=sha(out/'GATE.json'),streams=[dict(source_id=s['source_id'],speaker_id=s['speaker_id'],frames=s['frames'],seconds=s['duration'],audio_sha256=s['audio_sha256'],PCM_sha256=s['PCM_sha256']) for s in receipt['sources']],raw_ranges_and_audio_remain_on8TB=True,model_calls=0,resource_released=True,files=files)
(O/'DATA_IO_RELEASE_v1.json').write_text(json.dumps(release,indent=2)+'\\n');print(json.dumps(release))
""".replace('OVALUE',repr(O))
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=60);i.write(code);i.flush();i.channel.shutdown_write();a=o.read();b=e.read();rc=o.channel.recv_exit_status();(F/'DATA_RELEASE_STDOUT_v1.json').write_bytes(a);(F/'DATA_RELEASE_STDERR_v1.txt').write_bytes(b);assert rc==0,b.decode('utf8',errors='replace');release=json.loads(a)
 s=c.open_sftp();d=F/'ACQUISITION_RESULTS_v1';d.mkdir(exist_ok=False)
 for row in release['files']:
  s.get(release['raw_result_location']+'/'+row['path'],str(d/row['path']));assert (d/row['path']).stat().st_size==row['bytes'] and hashlib.sha256((d/row['path']).read_bytes()).hexdigest()==row['sha256']
 s.get(O+'/DATA_IO_RELEASE_v1.json',str(F/'DATA_IO_RELEASE_v1.json'));s.close()
 (F/'SOURCE_RECEIPT_v1.json').write_bytes((d/'SOURCE_RECEIPT.json').read_bytes())
 print(json.dumps({k:v for k,v in release.items() if k!='files'},indent=2))
finally:c.close()

