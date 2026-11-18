"""Collect bounded files after GPU closure; retries reuse verified immutable ZIPs."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,time,zipfile

E=Path(__file__).resolve().parents[1]
R=E.parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
O=B+'/results/revtrace/dsn_native_joint_retention_20261118'

REMOTE=r"""
from pathlib import Path,PurePosixPath
import datetime,hashlib,json,subprocess,time,zipfile
O=Path(C['out_root']).resolve();assert str(O).startswith('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/')
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()

def stopped(h):
 p=Path('/proc')/str(h['pid']);state='EXITED'
 if p.exists():
  s=(p/'stat').read_text().rsplit(')',1)[1].split();state=s[0]if int(s[19])==h['start_ticks']else'PID_REUSED'
 assert state in('EXITED','Z','X','PID_REUSED'),'owned process still active'
 return state

def identity(st):return(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
def stable_sha(path):
 assert path.is_file()and not path.is_symlink(),str(path)
 before=path.stat();digest=hashlib.sha256()
 with path.open('rb')as stream:
  for chunk in iter(lambda:stream.read(1048576),b''):digest.update(chunk)
 after=path.stat();assert identity(before)==identity(after),'file changed while hashing: '+str(path)
 return dict(path=str(path),bytes=after.st_size,sha256=digest.hexdigest(),mtime_ns=after.st_mtime_ns)

def bounded_bytes(path,limit):
 assert path.is_file()and not path.is_symlink(),str(path)
 before=path.stat();assert before.st_size<=limit,str(path)
 raw=path.read_bytes();after=path.stat();assert identity(before)==identity(after)and len(raw)==after.st_size,'bounded source changed: '+str(path)
 return raw

def safe_member(name):
 n=PurePosixPath(name);assert not n.is_absolute()and'..'not in n.parts and'.git'not in n.parts and'\\'not in name,name
 return name

def immutable_json(path,value):
 raw=(json.dumps(value,indent=2)+'\n').encode()
 if path.exists():assert path.read_bytes()==raw,'existing collection metadata differs: '+str(path)
 else:
  with path.open('xb')as stream:stream.write(raw)
 return raw

closure=None;raw_roots=[];extra_rows=[]
if C['mode']=='service':
 root=Path(C['root']).resolve();assert root.parent==O and root.name==C['phase']
 state=stopped(C['handle'])
 summary=json.loads((root/'SUMMARY.json').read_bytes());gate=json.loads((root/'GATE.json').read_bytes())
 assert summary['completed_trials']==C['expected']and summary['status'].startswith('COMPLETE')and gate['status'].startswith('COMPLETE')
 closure_path=root/'COLLECTION_RESOURCE_CLOSURE.json'
 if closure_path.exists():
  closure=json.loads(closure_path.read_bytes());assert closure['pid']==C['handle']['pid']and closure['start_ticks']==C['handle']['start_ticks']and closure['trials']==C['expected']and closure['status']=='PASS_COLLECTION_PROCESS_AND_CUDA_RELEASE'
 else:
  closure=dict(status='PASS_COLLECTION_PROCESS_AND_CUDA_RELEASE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=C['handle']['pid'],start_ticks=C['handle']['start_ticks'],state=state,CUDA_owners='',trials=C['expected'])
  immutable_json(closure_path,closure)
 extra_rows.append((closure_path,'launch_ops/'+C['phase']+'/COLLECTION_RESOURCE_CLOSURE.json'))
 for cell in C['cells']:
  d=Path(cell['out']);assert not d.is_symlink()and d.resolve().parent==root/'cells'and d.name==cell['cell_id']
  raw_roots.append((d,cell['cell_id']))
  for name,folder in[('log','logs'),('external_power','external')]:
   q=Path(cell[name]);assert not q.is_symlink()and q.resolve().parent==root/folder
else:
 assert C['mode']=='reference_and_premodel'
 for h in C['handles']:stopped(h)
 root=O/'REFERENCE8_V3';assert json.loads((root/'GATE.json').read_bytes())['status'].startswith('PASS')
 for failure in C['premodel_failures']:assert failure['model_calls']==0
 raw_roots.append((root,'REFERENCE8_V3'))

selection_digest=hashlib.sha256(json.dumps(dict(schema=2,mode=C['mode'],selected=C['selected']),sort_keys=True,separators=(',',':')).encode()).hexdigest()
archive=Path(C['archive']);assert archive.parent.resolve()==O and archive.name.endswith('.bounded_collection_v2.zip')and not archive.is_symlink()

def verified_archive(path):
 with zipfile.ZipFile(path)as z:
  names=z.namelist();assert len(names)==len(set(names))and z.testzip()is None
  manifest=json.loads(z.read('collection_manifest.json'));assert manifest['schema']==2 and manifest['selection_sha256']==selection_digest
  for row in manifest['files']:
   safe_member(row['path']);b=z.read(row['path']);assert len(b)==row['bytes']and hashlib.sha256(b).hexdigest()==row['sha256']
  required={r['local_relative_path']for r in C['selected']if r['required_after_successful_closure']};assert required<={r['path']for r in manifest['files']}
 return manifest

if archive.exists():
 manifest=verified_archive(archive)
 print(json.dumps(dict(status='PASS_REUSED_VERIFIED_BOUNDED_ARCHIVE',phase=C['phase'],archive=str(archive),**stable_sha(archive),file_count=len(manifest['files']),closure=closure)))
else:
 index=[]
 for rawroot,cid in raw_roots:
  assert rawroot.is_dir()and not rawroot.is_symlink()and rawroot.resolve().is_relative_to(O)
  for path in sorted(rawroot.rglob('*')):
   assert not path.is_symlink(),'raw symlink forbidden'
   if path.name=='COLLECTION_RAW_HASH_INDEX_V2.json':continue
   if path.is_file():
    assert path.resolve().is_relative_to(rawroot.resolve());index.append(dict(cell_id=cid,**stable_sha(path)))
 if C['mode']=='service':
  for cell in C['cells']:
   for name in('log','external_power'):index.append(dict(cell_id=cell['cell_id'],**stable_sha(Path(cell[name]))))
 rawindex_path=root/'COLLECTION_RAW_HASH_INDEX_V2.json'
 immutable_json(rawindex_path,dict(record_type='RAW_STAYS_8TB_STABLE_SHA_INDEX_ONLY',files=index,file_count=len(index)))
 hash_name='raw_hash_indices/'+C['phase']+'.collection_v2.json'
 extra_rows.append((rawindex_path,hash_name))
 rows=[];missing=[];total=0
 temporary=archive.with_name(archive.name+'.partial');assert temporary.parent==archive.parent and not temporary.is_symlink()
 if temporary.exists():temporary.rename(temporary.with_name(temporary.name+'.abandoned.'+str(time.time_ns())))
 with zipfile.ZipFile(temporary,'x',zipfile.ZIP_DEFLATED)as z:
  for req in C['selected']:
   path=Path(req['remote_path']);assert path.is_absolute()and path.resolve().is_relative_to(Path(C['disk_root']).resolve())and not path.is_symlink()
   assert path.suffix in('.json','.log'),'non-metadata download forbidden'
   if path.suffix=='.log':assert req['evidence_role']=='operator_metadata_failure_before_model_load','normal raw process log is hash-only'
   if C['mode']=='service':assert path.resolve().is_relative_to(root)or str(path)in{cell['config']for cell in C['cells']},'request outside frozen service/config scope'
   else:assert path.resolve().is_relative_to(root)or path in(O/'REFERENCE8_V1.process.log',O/'REFERENCE8_V2.process.log'),'request outside reference/premodel scope'
   if not path.exists():
    assert not req['required_after_successful_closure'],str(path);missing.append(req['local_relative_path']);continue
   b=bounded_bytes(path,req['maximum_bytes']);digest=hashlib.sha256(b).hexdigest()
   if req.get('expected_source_byte_sha256'):assert digest==req['expected_source_byte_sha256'],str(path)
   name=safe_member(req['local_relative_path']);z.writestr(name,b);rows.append(dict(path=name,bytes=len(b),sha256=digest));total+=len(b)
  for src,name in extra_rows:
   b=bounded_bytes(src,16_000_000);name=safe_member(name);z.writestr(name,b);rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));total+=len(b)
  assert len({r['path']for r in rows})==len(rows)and total<=128_000_000
  manifest=dict(schema=2,selection_sha256=selection_digest,phase=C['phase'],mode=C['mode'],files=rows,file_count=len(rows),uncompressed_bytes=total,optional_missing=missing)
  z.writestr('collection_manifest.json',json.dumps(manifest,indent=2)+'\n')
 assert not archive.exists();temporary.rename(archive);verified_archive(archive)
 print(json.dumps(dict(status='PASS_BOUNDED_COLLECTION_CREATED_AFTER_GPU_RELEASE',phase=C['phase'],archive=str(archive),**stable_sha(archive),file_count=len(rows),closure=closure)))
"""


def receive_archive(c,meta,label):
 cache=E/'collection_cache';cache.mkdir(exist_ok=True);local=cache/(label+'.v2.zip')
 if local.exists()and hashlib.sha256(local.read_bytes()).hexdigest()!=meta['sha256']:
  local.rename(local.with_name(local.name+'.badsha.'+str(time.time_ns())))
 if not local.exists():c.get(meta['archive'],local,maximum=100_000_000)
 assert hashlib.sha256(local.read_bytes()).hexdigest()==meta['sha256']
 with zipfile.ZipFile(local)as z:
  assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
  manifest=json.loads(z.read('collection_manifest.json'));assert manifest['schema']==2
  for row in manifest['files']:
   dest=(E/row['path']).resolve();assert dest.is_relative_to(E.resolve())and all(part.lower()!='.git'for part in Path(row['path']).parts)
   b=z.read(row['path']);assert len(b)==row['bytes']and hashlib.sha256(b).hexdigest()==row['sha256']
   if dest.exists():assert dest.read_bytes()==b,'immutable mirror differs '+row['path']
   else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
  (E/'baseline'/('COLLECTION_'+label+'_MANIFEST_V2.json')).write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
 return manifest


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--phase',action='append',choices=['PILOT20_V1','CONFIRM60_V1']);parser.add_argument('--skip-extras',action='store_true');args=parser.parse_args()
 phases=args.phase or['PILOT20_V1','CONFIRM60_V1'];requests=json.loads((E/'COLLECTION_REQUESTS.json').read_bytes())['requests']
 spec=importlib.util.spec_from_file_location('approved',R/'experiments/dsn_v11_closure_20261102/ops/remote.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 collected=[]
 with module.Remote()as c:
  for phase in phases:
   selected=[x for x in requests if x['local_relative_path'].startswith(('gpu_results/'+phase+'/','frozen_configs/'+phase+'/'))]
   handle=json.loads((E/'launch_ops'/phase/'HANDLE.json').read_bytes());plan=json.loads((E/'plans'/(phase+'_PLAN.json')).read_bytes())
   config=dict(mode='service',phase=phase,disk_root=B,out_root=O,root=O+'/'+phase,handle=handle,selected=selected,expected=len(plan['cells']),cells=plan['cells'],archive=O+'/'+phase+'.bounded_collection_v2.zip')
   raw=c.python('C='+repr(config)+'\n'+REMOTE,timeout=240);meta=json.loads(raw);(E/'baseline'/('COLLECTION_'+phase+'_V2.json')).write_bytes(raw+b'\n')
   receive_archive(c,meta,phase);collected.append(meta);print(json.dumps({k:v for k,v in meta.items()if k!='closure'}),flush=True)
  if not args.skip_extras:
   selected=[x for x in requests if x['local_relative_path'].startswith(('gpu_results/REFERENCE8_V3/','preserved_premodel_failures/'))]
   failures=[json.loads((E/'launch_ops'/tag/'ROOT_CLOSEOUT.json').read_bytes())for tag in('REFERENCE8_V1','REFERENCE8_V2')]
   handles=[json.loads((E/'launch_ops'/tag/'HANDLE.json').read_bytes())for tag in('REFERENCE8_V1','REFERENCE8_V2','REFERENCE8_V3')]
   config=dict(mode='reference_and_premodel',phase='REFERENCE_AND_PREMODEL',disk_root=B,out_root=O,selected=selected,premodel_failures=failures,handles=handles,archive=O+'/REFERENCE_AND_PREMODEL.bounded_collection_v2.zip')
   raw=c.python('C='+repr(config)+'\n'+REMOTE,timeout=240);meta=json.loads(raw);(E/'baseline/COLLECTION_REFERENCE_AND_PREMODEL_V2.json').write_bytes(raw+b'\n')
   receive_archive(c,meta,'REFERENCE_AND_PREMODEL');collected.append(meta);print(json.dumps({k:v for k,v in meta.items()if k!='closure'}),flush=True)
 (E/'COLLECTION_INDEX_V2.json').write_bytes((json.dumps(dict(status='PASS_SELECTED_PHASES_BOUNDED_COLLECTION',phases=phases,reference_and_premodel_included=not args.skip_extras,archives=collected,source_data_not_downloaded=True),indent=2)+'\n').encode())

if __name__=='__main__':main()
