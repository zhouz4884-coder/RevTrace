import hashlib,json,pathlib,shlex,sys
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';O=B+'/results/revtrace/dsn_streamcorrect_independent_20261029';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
program='''import hashlib,json,pathlib,wave,zlib
O=pathlib.Path(O_VALUE);out=O/'acquisition_v2';h=json.loads((O/'HANDLE_v2.json').read_text());assert not (pathlib.Path('/proc')/str(h['pid'])).exists()
old=json.loads((O/'HANDLE_v1.json').read_text());assert not (pathlib.Path('/proc')/str(old['pid'])).exists()
r=json.loads((out/'SOURCE_RECEIPT.json').read_text());assert len(r['sources'])==4 and all(s['technical_fallback_index']==0 for s in r['sources'])
for s in r['sources']:
 p=pathlib.Path(s['path']);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==s['audio_sha256'];assert zlib.crc32(b)==s['archive_member']['crc32'];assert len(b)==s['archive_member']['bytes'];assert p.stat().st_mode&0o222==0
 with wave.open(str(p)) as w:assert (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(1,2,16000,s['frames'])
files=[]
for version in ('acquisition_v1','acquisition_v2'):
 for p in sorted((O/version).glob('*.json')):
  b=p.read_bytes();files.append(dict(relative=p.relative_to(O).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
for name in ('HANDLE_v1.json','HANDLE_v2.json','CPU_GATE_v1.json','CPU_GATE_v2.json'):
 p=O/name;b=p.read_bytes();files.append(dict(relative=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
assert sum(x['bytes'] for x in files)<4*1024*1024
print(json.dumps(dict(status='PASS_FOUR_SOURCE_INDEPENDENT_DATA_SHA_CRC_HEADER_AND_IO_RELEASE',sources=4,all_fallback_indices_zero=True,all_workers_exited=True,no_model_or_GPU_calls=True,source_receipt_sha256=hashlib.sha256((out/'SOURCE_RECEIPT.json').read_bytes()).hexdigest(),gate_sha256=hashlib.sha256((out/'GATE.json').read_bytes()).hexdigest(),files=files)))
'''.replace('O_VALUE',repr(O))
c=ssh_client()
try:
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=30);i.write(program);i.flush();i.channel.shutdown_write();body=o.read().decode();err=e.read().decode();assert o.channel.recv_exit_status()==0,err
 m=json.loads(body);out=F/'DATA_ACQUISITION_RESULTS_v2';out.mkdir(exist_ok=False);s=c.open_sftp()
 try:
  for r in m['files']:
   p=out/r['relative'];p.parent.mkdir(parents=True,exist_ok=True);s.get(O+'/'+r['relative'],str(p));assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 finally:s.close()
 (out/'COLLECTION_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8');release={k:v for k,v in m.items() if k!='files'}
 (F/'DATA_READY_AND_IO_RELEASE_v1.json').write_text(json.dumps(release,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(**release,files=len(m['files']),bytes=sum(x['bytes'] for x in m['files']))))
finally:c.close()
