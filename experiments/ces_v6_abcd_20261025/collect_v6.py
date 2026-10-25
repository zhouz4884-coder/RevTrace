"""Post-completion byte-audited bounded evidence collector. No audio or models."""
from pathlib import Path
import argparse,gzip,hashlib,json,os,subprocess,tarfile,time
PART=8_000_000;ARCHIVE=32_000_000
CPU_DIRS={'linux_cpu_tmp_v1','linux_cpu_tmp_D'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(PART),b''):h.update(data)
 return h.hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,v):
 assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def confined(root,p):p.resolve().relative_to(root.resolve());assert not p.is_symlink()
def compress_file(source,destroot,logical):
 assert not Path(logical).is_absolute() and '..' not in Path(logical).parts
 before=source.stat();parts=[];h=hashlib.sha256()
 with source.open('rb') as f:
  i=0
  while True:
   data=f.read(PART)
   if not data and i:break
   h.update(data);packed=gzip.compress(data,compresslevel=6,mtime=0);path=Path('payload')/(logical+f'.part{i:04d}.gz')
   out=destroot/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(packed)
   assert len(packed)<40_000_000
   parts.append({'path':path.as_posix(),'bytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest(),'uncompressed_bytes':len(data)})
   i+=1
   if not data:break
 after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'changing raw file'
 return {'logical_path':logical,'raw_bytes':before.st_size,'raw_sha256':h.hexdigest(),'parts':parts}
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);a=p.parse_args();B=a.base
 P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025';D=O/'collection_v1';assert not D.exists()
 expected={'A_pilot':2,'A':24,'C':18,**{n:len(load(P/('PLAN_'+n+'.json'))['cells']) for n in ['D_development','D_heldout']}};stages=[]
 for stage,n in expected.items():
  r=load(O/(stage+'_SUMMARY.json'));audit=load(O/(stage+'_audit/SUMMARY.json'))
  assert r['status']=='COMPLETE_GPU_MATRIX_AND_SAFETY_AUDIT' and r['cells']==n and r['GPU_queue_closed']
  assert audit['failures']==[] and audit['cells']==n and audit['expected_cells']==n
  assert len(r['completed'])==len(set(r['completed']))==n
  assert not (O/(stage+'_STOP.json')).exists()
  for cell in r['completed']:
   C=O/stage/cell;assert (C/'result.json').exists()
   for worker in load(C/'OWNED_WORKER_HANDLES.json'):
    q=Path('/proc',str(worker['pid']),'stat')
    if q.exists():assert q.read_text().rsplit(')',1)[1].split()[19]!=str(worker['linux_start_ticks']),'original Worker still alive'
  stages.append({'stage':stage,'cells':n,'summary_sha256':sha(O/(stage+'_SUMMARY.json')),'audit_sha256':sha(O/(stage+'_audit/SUMMARY.json'))})
 assert load(O/'ABC_SUMMARY.json')['GPU_queue_closed'] and load(O/'D_SEQUENCE_SUMMARY.json')['GPU_queue_closed']
 assert load(O/'B_SUMMARY.json')['calls']==18 and load(O/'B_SORTED_SUMMARY.json')['calls']==18
 assert load(O/'B_SORTED_SUMMARY.json')['worker_exited']
 for source in ['runtime','runtime_A','runtime_D']:
  m=load(P/source/'SOURCE_MANIFEST.json')
  for f in m['files']:assert sha(P/source/f['path'])==f['sha256']
 sources=[];excluded=[]
 def walk(root,prefix):
  for path in sorted(root.rglob('*')):
   rel=path.relative_to(root)
   if prefix=='results' and (rel.parts[0] in CPU_DIRS or rel.parts[0]=='collection_v1' or rel.as_posix()=='COLLECTOR.log'):continue
   if '__pycache__' in rel.parts or '.pytest_cache' in rel.parts:continue
   confined(root,path)
   if not path.is_file():continue
   if path.suffix.lower() in {'.wav','.flac','.mp3','.safetensors','.pt','.bin','.npy','.npz','.ckpt','.pth'}:
    excluded.append({'path':prefix+'/'+rel.as_posix(),'reason':'model/audio/large tensor stays on8TB'});continue
   sources.append((path,prefix+'/'+rel.as_posix()))
 walk(P,'project');walk(O,'results')
 D.mkdir();payloads=[]
 for path,logical in sources:payloads.append(compress_file(path,D,logical))
 save(D/'PAYLOADS.json',{'version':1,'logical_files':payloads,'byte_reassembly':'In part order gzip.decompress each payload and concatenate; verify raw_sha256. No line ending rewriting.'})
 save(D/'RAW_INDEX.json',{'project':str(P),'raw_root':str(O),'stages':stages,'files':[{'path':r['logical_path'],'bytes':r['raw_bytes'],'sha256':r['raw_sha256']} for r in payloads],
  'explicit_CPU_fixture_exclusions':sorted(CPU_DIRS),'excluded_audio_model_files':excluded,'audio_in_heldout_stays_remote':True,'unknown_symlinks_fail_closed':True})
 entries=[D/p['path'] for r in payloads for p in r['parts']]+[D/'PAYLOADS.json',D/'RAW_INDEX.json'];archives=[];pending=[];size=0
 def flush():
  nonlocal pending,size
  if not pending:return
  f=D/f'evidence-{len(archives):03d}.tar'
  with tarfile.open(f,'w',format=tarfile.PAX_FORMAT) as tf:
   for p in pending:tf.add(p,arcname=p.relative_to(D).as_posix(),recursive=False)
  assert f.stat().st_size<40_000_000
  archives.append({'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)});pending=[];size=0
 for f in entries:
  if size+f.stat().st_size+2048>ARCHIVE:flush()
  pending.append(f);size+=f.stat().st_size+2048
 flush()
 report={'status':'COMPLETE_BYTE_AUDITED_V6_COLLECTION','stages':stages,'logical_files':len(payloads),'raw_bytes':sum(r['raw_bytes'] for r in payloads),'parts':sum(len(r['parts']) for r in payloads),'archives':archives,'PAYLOADS_sha256':sha(D/'PAYLOADS.json'),'RAW_INDEX_sha256':sha(D/'RAW_INDEX.json'),'GPU_processes_at_collection':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader'],text=True),'all_our_workers_released':True,'script_sha256':sha(Path(__file__)),'time_unix':time.time()}
 save(D/'COLLECTION.json',report);print(json.dumps(report))
if __name__=='__main__':main()
