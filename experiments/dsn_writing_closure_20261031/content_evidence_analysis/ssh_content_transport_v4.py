"""Approved credential route for bounded CPU source/metadata operations only."""
from pathlib import Path
import hashlib,json,shlex,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
E=ROOT/'experiments/dsn_writing_closure_20261031'
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_writing_closure_20261031'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'

def remote(c,code):
 compile(code,'bounded_content_operation','exec')
 i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=180)
 i.write(code);i.flush();i.channel.shutdown_write()
 stdout=o.read();stderr=e.read();rc=o.channel.recv_exit_status()
 if rc:raise RuntimeError('Remote exit '+str(rc)+'\n'+stderr.decode('utf8','replace')[-9000:]+'\n'+stdout.decode('utf8','replace')[-6000:])
 return json.loads(stdout)

def upload(s,path,name):
 data=path.read_bytes()
 with s.open(P+'/'+name,'wx') as f:f.write(data)
 return dict(path=P+'/'+name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())

def main():
 operation=sys.argv[1]
 sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
 from contractkv_ssh_credential import ssh_client
 c=ssh_client()
 try:
  if operation=='prepare':
   resource=remote(c,(HERE/'remote_prepare_content_v4.py').read_text(encoding='utf8').split('# AFTER_UPLOAD')[0])
   s=c.open_sftp();sent=[]
   for file,name in [('CONTENT_SOURCE_v4.bundle','CONTENT_SOURCE_v4_UPLOAD1.bundle'),('CONTENT_SOURCE_v4.json','CONTENT_SOURCE_v4.json')]:
    sent.append(upload(s,E/'content_packages_v4'/file,name))
   s.close()
   code=(HERE/'remote_prepare_content_v4.py').read_text(encoding='utf8').split('# AFTER_UPLOAD')[1]
   prepared=remote(c,code)
   result=dict(resource=resource,uploaded=sent,prepared=prepared)
  elif operation=='run':
   s=c.open_sftp();sent=[]
   for name,path in [('ROOT_NOARG_CONTENT_CPU_v4.json',E/'ROOT_NOARG_CONTENT_CPU_v4.json'),('CONTENT_CONTROLS_v4_FROZEN.json',HERE/'CONTENT_CONTROLS_v4_FROZEN.json'),('CONTENT_COMPLETE20_v4_FROZEN.json',HERE/'CONTENT_COMPLETE20_v4_FROZEN.json')]:sent.append(upload(s,path,name))
   s.close();result=remote(c,(HERE/'remote_run_content_v4.py').read_text(encoding='utf8'));result['uploaded']=sent
  elif operation=='collect':
   result=remote(c,(HERE/'remote_collect_content_v4.py').read_text(encoding='utf8'))
   assert result['total_bytes']<=8*1024*1024
   out=E/'CONTENT_CPU_V4_RESULTS';out.mkdir(exist_ok=False);s=c.open_sftp()
   for row in result['files']:
    with s.open(row['path'],'rb') as f:data=f.read()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    path=out/row['relative'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
   s.close()
   (out/'COLLECTION_INDEX.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
  else:raise ValueError(operation)
  with (HERE/('REMOTE_'+operation.upper()+'_v4.json')).open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
  print(json.dumps(result if operation!='collect' else {k:v for k,v in result.items() if k!='files'},indent=2))
 finally:c.close()

if __name__=='__main__':main()
