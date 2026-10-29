"""Official public Range -> RAM -> approved SFTP B disk; never local audio files."""
import datetime,hashlib,json,pathlib,sys,urllib.request
F=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_streamcorrect_independent_20261029';D=P+'/transport_v2_ranges'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
sels=json.loads((F/'METADATA_SELECTION_v1_FROZEN.json').read_text(encoding='utf-8'));records=[];c=ssh_client();s=c.open_sftp()
try:
 try:s.stat(D)
 except FileNotFoundError:s.mkdir(D)
 for group in sels['selected']:
  e=group['technical_fallback_order'][0];start=e['local_offset'];length=e['compressed']+4096;end=start+length-1
  # Network route changes cannot alter the frozen byte interval or member.
  for suffix in ('','?download=true'):
   req=urllib.request.Request(sels['archive_public_url']+suffix,headers={'Range':f'bytes={start}-{end}'})
   with urllib.request.urlopen(req,timeout=30) as response:
    data=response.read(length+1);status=response.status;cr=response.headers.get('Content-Range','')
   if status==206 and len(data)==length and cr.startswith(f'bytes {start}-{end}/'):break
  else:raise RuntimeError('official Range did not match frozen interval')
  h=hashlib.sha256(data).hexdigest();path=D+'/'+e['source_id']+'.range'
  try:
   with s.open(path,'rb') as f:assert hashlib.sha256(f.read()).hexdigest()==h
  except FileNotFoundError:
   # Paramiko requires an explicit w with x; preserve the empty first-mode
   # attempt rather than overwriting or silently deleting it.
   with s.open(path+'.part2','wx') as f:f.write(data);f.flush()
   s.rename(path+'.part2',path);s.chmod(path,0o444)
  records.append(dict(source_id=e['source_id'],path=path,sha256=h,bytes=len(data),content_range=cr,
    public_source=sels['archive_public_url'],public_route_suffix=suffix,transport='localRAM_officialHTTPS_to_approvedSFTP_designatedB',local_audio_file_written=False))
  print(json.dumps(dict(source_id=e['source_id'],bytes=len(data),sha256=h,local_audio_file_written=False)),flush=True)
 receipt=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_sha256=hashlib.sha256((F/'METADATA_SELECTION_v1_FROZEN.json').read_bytes()).hexdigest(),same_frozen_members=True,records=records,model_calls=0)
 (F/'STAGED_RANGE_TRANSPORT_v2.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
finally:s.close();c.close()
