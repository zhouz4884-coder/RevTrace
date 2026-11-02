"""Official immutable byte intervals via Windows RAM; first persistent write 8TB."""
import datetime,hashlib,json,urllib.request
from remote import Remote,E,P,O
path=E/'selection/METADATA_SELECTION_v2/METADATA_SELECTION.json'
sel=json.loads(path.read_bytes());records=[];sha=lambda b:hashlib.sha256(b).hexdigest()
assert sel['status']=='PASS_STRICT_SAME_SPLIT_METADATA_SELECTION_PENDING_AUDIO'
with Remote() as c:
 s=c.client.open_sftp();d=P+'/same_members_ranges_v2'
 try:
  try:s.stat(d)
  except FileNotFoundError:s.mkdir(d)
  for g in sel['selected_sources']:
   e=g['technical_header_fallback_order'][0];start=e['local_offset'];length=e['compressed']+4096;end=start+length-1
   data=None;errors=[]
   for suffix in ('','?download=true','?download=true&offset='+str(start)):
    try:
     req=urllib.request.Request(sel['archive_public_url']+suffix,headers={'Range':f'bytes={start}-{end}'})
     with urllib.request.urlopen(req,timeout=40) as r:
      payload=r.read(length+1);cr=r.headers.get('Content-Range','');status=r.status
     if status==206 and len(payload)==length and cr.startswith(f'bytes {start}-{end}/'):
      data=payload;break
     errors.append(dict(status=status,exact_range=False))
    except Exception as exc:errors.append(dict(type=type(exc).__name__,status=getattr(exc,'code',None)))
   assert data is not None,dict(source_id=e['source_id'],errors=errors)
   dest=d+'/'+e['source_id']+'.range';h=sha(data)
   try:
    with s.open(dest,'rb') as f:assert sha(f.read())==h
   except FileNotFoundError:
    with s.open(dest+'.part','wx') as f:f.write(data);f.flush()
    s.rename(dest+'.part',dest);s.chmod(dest,0o444)
   records.append(dict(source_id=e['source_id'],path=dest,sha256=h,bytes=len(data),content_range=cr,public_source=sel['archive_public_url'],public_route_suffix=suffix,transport='officialHTTPS_Windows_RAM_SFTP_first_persistent_write_8TB',local_audio_file_written=False,prior_transport_errors=errors))
   print(json.dumps(dict(source_id=e['source_id'],bytes=len(data),sha256=h)),flush=True)
 finally:s.close()
receipt=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),metadata_selection_sha256=sha(path.read_bytes()),transport_script_sha256=sha(__import__('pathlib').Path(__file__).read_bytes()),same_frozen_members=True,model_calls=0,records=records)
(E/'selection/STAGED_RANGE_TRANSPORT_v2.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
(E/'selection/STAGED_RANGE_INDEX_v2.json').write_text(json.dumps({r['source_id']:r for r in records},indent=2)+'\n',encoding='utf-8')
