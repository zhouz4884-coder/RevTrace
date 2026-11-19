"""Original official HTTP pieces stay in RAM locally; all corpus files stay on8TB."""
from __future__ import annotations
import concurrent.futures,datetime,hashlib,importlib.metadata,json,math,os,pathlib,platform,subprocess,sys,threading,time,traceback,urllib.request
URL='https://openslr.trmal.net/resources/68/test_set.tar.gz';SIZE=2201936013;ETAG='"833ee08d-58e45ba913852"';PIECE=4*1024*1024
PREFIX='da4298064c4dbff1288a5dd366687d532eef306542704118de04714343aed090'
def need(ok,why):
    if not ok:raise RuntimeError(why)
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def put(path,x):
    with pathlib.Path(path).open('x',encoding='utf8')as f:json.dump(x,f,indent=2);f.write('\n')
def bounds(index):
    need(type(index)is int and 0<=index<math.ceil(SIZE/PIECE),'piece_index_outside_original_asset')
    start=index*PIECE;return start,min(SIZE,start+PIECE)-1
def fetch(index):
    start,end=bounds(index);began=time.monotonic();req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{end}','User-Agent':'RevTrace-original-CPU-memory-transport/1.0'})
    with urllib.request.urlopen(req,timeout=90)as response:
        need(response.url==URL and response.status==206,'official_range_or_redirect_changed')
        need(response.headers.get('Content-Range')==f'bytes {start}-{end}/{SIZE}' and response.headers.get('ETag')==ETAG,'official_piece_identity_changed')
        need(response.headers.get('Content-Length')==str(end-start+1),'official_piece_length_header_changed')
        raw=response.read(end-start+2);need(len(raw)==end-start+1,'official_piece_body_length_changed')
    if index==0:need(hashlib.sha256(raw[:65536]).hexdigest()==PREFIX,'first_piece_prefix_changed')
    return raw,dict(index=index,start=start,end=end,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),HTTP_status=206,Content_Range=f'bytes {start}-{end}/{SIZE}',ETag=ETAG,download_wall_seconds=time.monotonic()-began)
def remote_python(client,script,timeout=90):
    stdin,stdout,stderr=client.exec_command('python3 -',timeout=timeout);stdin.write(script);stdin.flush();stdin.channel.shutdown_write();raw=stdout.read();err=stderr.read();code=stdout.channel.recv_exit_status()
    need(code==0,'remote_CPU_receiver_failed:'+err.decode(errors='replace')[-2000:]);return json.loads(raw)
def verify_source(config,manifest_path):
    root=pathlib.Path(__file__).resolve().parent;m=json.loads(pathlib.Path(manifest_path).read_bytes())
    def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    need(git('rev-parse','HEAD')==m['code_commit']==config['source_commit'],'memory_transport_source_changed');need(not git('status','--porcelain','--untracked-files=all'),'dirty_memory_transport_source')
    need(set(git('ls-files').splitlines())=={r['path']for r in m['files']},'memory_source_manifest_incomplete')
    for row in m['files']:
        p=root/row['path'];need(p.stat().st_size==row['bytes']and sha(p)==row['sha256'],'memory_source_bytes_changed')
    need(sha(manifest_path)==config['source_manifest_sha256'],'memory_manifest_hash_changed')
def run(client,config,manifest_path,metadata_out):
    verify_source(config,manifest_path);need(config['official_url']==URL and config['archive_bytes']==SIZE and config['piece_bytes']==PIECE and config['threads']==4,'frozen_memory_transport_contract_changed')
    need(config['phase']in('canary','full'),'invalid_memory_transport_phase');out=pathlib.Path(metadata_out);out.mkdir(parents=True,exist_ok=False)
    env=dict(python=sys.version,platform=platform.platform(),hostname=platform.node(),paramiko_version=importlib.metadata.version('paramiko'),model_calls=0,GPU_calls=0)
    need(env==config['expected_environment'],'frozen_memory_transport_environment_changed');need('torch'not in sys.modules and 'transformers'not in sys.modules,'unexpected_neural_import')
    put(out/'CONFIG.json',config);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=config['experiment_id'],code_commit=config['source_commit'],frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=config['remote_directory'],aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json')))
    directory=config['remote_directory'];need(directory.startswith(config['experiment_disk']+'/datasets/MAGICDATA68/windows_memory_'),'receiver_not_in_designated_original_asset_area')
    started=time.monotonic();records=[];lock=threading.Lock()
    try:
        setup='C='+repr(dict(directory=directory,config=config,environment=env))+'\n'+r'''
from pathlib import Path
import json,os
p=Path(C['directory']);assert not p.exists();p.mkdir(parents=True)
for key,value in [('CONFIG',C['config']),('ENVIRONMENT',C['environment'])]:(p/(key+'.json')).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(dict(receiver_directory=str(p),created=True)))
'''
        remote_python(client,setup)
        count=4 if config['phase']=='canary' else math.ceil(SIZE/PIECE)
        def one(index):
            raw,record=fetch(index);path=f'{directory}/piece_{index:06d}.bin';began=time.monotonic()
            with client.open_sftp()as sftp:
                with sftp.open(path,'wx')as f:
                    f.set_pipelined(True);f.write(raw);f.flush()
            record.update(remote_path=path,upload_wall_seconds=time.monotonic()-began)
            del raw
            with lock:
                records.append(record)
                with(out/'PIECES.jsonl').open('a',encoding='utf8')as log:log.write(json.dumps(record)+'\n')
                current=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_pieces=len(records),planned_pieces=count,completed_bytes=sum(r['bytes']for r in records),wall_seconds=time.monotonic()-started)
                temp=out/'PROGRESS.tmp';temp.write_text(json.dumps(current));os.replace(temp,out/'PROGRESS.json')
            return record
        with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
            futures=[pool.submit(one,i)for i in range(count)]
            for future in concurrent.futures.as_completed(futures):future.result()
        records.sort(key=lambda r:r['index']);need([r['index']for r in records]==list(range(count)),'missing_memory_transport_piece')
        verification='C='+repr(dict(directory=directory,records=records,phase=config['phase'],archive_path=config['archive_path'],size=SIZE))+'\n'+r'''
from pathlib import Path
import hashlib,json,os
root=Path(C['directory']);rows=C['records'];full=hashlib.sha256();total=0;part=root/'test_set.tar.gz.assembled.part'
stream=part.open('xb')if C['phase']=='full'else None
try:
 for r in rows:
  p=Path(r['remote_path']);assert p.parent==root and p.stat().st_size==r['bytes'];h=hashlib.sha256()
  with p.open('rb')as f:
   for block in iter(lambda:f.read(1024*1024),b''):
    h.update(block);full.update(block);total+=len(block)
    if stream:stream.write(block)
  assert h.hexdigest()==r['sha256']
 if stream:stream.flush();os.fsync(stream.fileno())
finally:
 if stream:stream.close()
result=dict(status='PASS_ALL_REMOTE_PIECE_BYTES_AND_SHA256',verified_pieces=len(rows),verified_bytes=total,ordered_sha256=full.hexdigest())
if C['phase']=='full':
 assert total==C['size'];final=Path(C['archive_path']);assert final.parent==root.parent/'original'
 if final.exists():
  h=hashlib.sha256()
  with final.open('rb')as f:
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
  assert final.stat().st_size==total and h.hexdigest()==result['ordered_sha256']
 else:os.link(part,final)
 result['archive']=dict(path=str(final),bytes=total,sha256=result['ordered_sha256'])
(root/'REMOTE_VERIFY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
'''
        checked=remote_python(client,verification,timeout=180);wall=time.monotonic()-started;speed=checked['verified_bytes']/wall
        status='PASS_MEMORY_TRANSPORT_CANARY_GO'if config['phase']=='canary'and speed>=config['minimum_end_to_end_Bps']else 'NO_GO_MEMORY_TRANSPORT_CANARY_RATE_BELOW_FROZEN_THRESHOLD'if config['phase']=='canary'else 'PASS_COMPLETE_ORIGINAL_MEMORY_TRANSPORT_FULL_SHA256_SIZE_ONLY'
        summary=dict(status=status,experiment_id=config['experiment_id'],source_commit=config['source_commit'],phase=config['phase'],remote_verification=checked,wall_seconds=wall,end_to_end_bytes_per_second=speed,
                     local_corpus_files_written=0,piece_buffer_bytes_max=4*PIECE,model_calls=0,GPU_calls=0,transport_only=True)
        verify_source(config,manifest_path);put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=status,summary_sha256=sha(out/'SUMMARY.json'),model_calls=0,GPU_calls=0));return summary
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());put(out/'GATE.json',dict(status='FAIL_MEMORY_TRANSPORT_PIECES_PRESERVED',source_commit=config['source_commit'],model_calls=0,GPU_calls=0));raise
