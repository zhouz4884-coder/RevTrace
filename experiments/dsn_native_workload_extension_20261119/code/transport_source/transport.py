"""CPU-only multi-mirror transport of one unchanged official public archive."""
from __future__ import annotations
import argparse,datetime,hashlib,json,os,pathlib,platform,re,subprocess,sys,time,traceback,urllib.request

URLS=('https://openslr.elda.org/resources/68/test_set.tar.gz','https://openslr.trmal.net/resources/68/test_set.tar.gz','https://openslr.magicdatatech.com/resources/68/test_set.tar.gz')
SIZE=2201936013
ETAG='"833ee08d-58e45ba913852"'
PREFIX_SHA='da4298064c4dbff1288a5dd366687d532eef306542704118de04714343aed090'
def need(value,why):
    if not value:raise RuntimeError(why)
def digest(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()
def put(path,value):
    path=pathlib.Path(path)
    with path.open('x',encoding='utf8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def generation(pid):
    fields=(pathlib.Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,start_ticks=int(fields[19]),state=fields[0])
def source_identity(root,manifest,path,config):
    def git(*a):return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
    need(git('rev-parse','HEAD')==manifest['code_commit']==config['source_commit'],'source_commit_changed')
    need(not git('status','--porcelain','--untracked-files=all'),'dirty_transport_source')
    need(set(git('ls-files').splitlines())=={r['path'] for r in manifest['files']},'incomplete_source_manifest')
    for row in manifest['files']:
        p=root/row['path'];need(p.is_file() and p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],'source_bytes_changed')
    need(digest(path)==config['source_manifest_sha256'],'source_manifest_changed')
def safe_headers(headers):
    return {k:headers[k] for k in ('Content-Length','Content-Range','ETag','Last-Modified','Content-Type','Accept-Ranges') if headers.get(k) is not None}
def probe(url):
    need(url in URLS,'nonofficial_mirror')
    req=urllib.request.Request(url,headers={'Range':'bytes=0-65535','User-Agent':'RevTrace-original-public-data-transport/1.0'})
    with urllib.request.urlopen(req,timeout=45) as response:
        need(response.url==url and response.status==206,'mirror_range_or_redirect_changed')
        headers=safe_headers(response.headers)
        need(headers.get('Content-Range')==f'bytes 0-65535/{SIZE}' and headers.get('ETag')==ETAG,'mirror_identity_changed')
        raw=response.read(65537);need(len(raw)==65536 and hashlib.sha256(raw).hexdigest()==PREFIX_SHA,'mirror_prefix_changed')
    return dict(url=url,utc=utc(),headers=headers,range_bytes=len(raw),prefix_sha256=PREFIX_SHA)
def aria_command(aria,input_path,directory,part_name,rpc_port=None):
    return [aria,'--input-file='+str(input_path),'--split=16',
            '--max-connection-per-server=6','--max-concurrent-downloads=1','--uri-selector=adaptive',
            '--file-allocation=none','--auto-file-renaming=false','--allow-overwrite=false','--continue=true',
            '--check-certificate=true','--max-tries=8','--retry-wait=5','--connect-timeout=30','--timeout=60',
            '--enable-color=false','--human-readable=false','--summary-interval=30','--download-result=full',
            '--enable-rpc=false']
def aria_input(urls,directory,part_name):
    need('\n' not in str(directory) and '\n' not in part_name,'unsafe_aria_input_option')
    return '\t'.join(urls)+'\n dir='+str(directory)+'\n out='+part_name+'\n'
def log_progress(path):
    with pathlib.Path(path).open('rb')as f:
        f.seek(0,2);length=f.tell();f.seek(max(0,length-32768));tail=f.read().decode('utf8',errors='replace')
    matches=list(re.finditer(r'\[#([0-9a-f]+) (\d+)B/(\d+)B\(\d+%\) CN:(\d+) DL:(\d+)B[^\]\n]*\]',tail))
    if not matches:return dict(progress_unavailable='no_exact_byte_progress_line_yet')
    gid,done,total,connections,speed=matches[-1].groups()
    return dict(gid=gid,completed_bytes=int(done),total_bytes=int(total),connections=int(connections),download_bytes_per_second=int(speed),progress_source='aria2_exact_B_log_not_sparse_file_size')
def publish(part,final):
    need(part.is_file() and part.stat().st_size==SIZE,'incomplete_transport_bytes')
    h=digest(part)
    if final.exists():need(final.stat().st_size==SIZE and digest(final)==h,'different_existing_original_never_overwritten')
    else:os.link(part,final) # same-disk atomic no-clobber; preserve the transport file.
    return dict(path=str(final.resolve()),bytes=SIZE,sha256=h,transport_path=str(part.resolve()),unchanged_compressed_archive=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
    root=pathlib.Path(__file__).resolve().parent;cfg=json.loads(a.config.read_bytes());mf=json.loads(a.manifest.read_bytes())
    source_identity(root,mf,a.manifest,cfg);need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU_only_visibility_required')
    need(cfg['urls']==list(URLS) and cfg['archive_bytes']==SIZE and cfg['ETag']==ETAG and cfg['prefix_sha256']==PREFIX_SHA,'frozen_public_asset_identity_changed')
    disk=pathlib.Path(cfg['experiment_disk']).resolve();final=pathlib.Path(cfg['archive_path']);part=final.with_name('test_set.tar.gz.multi.part')
    for path in (a.out,final,part):need(path.resolve().is_relative_to(disk),'transport_outputs_must_stay_on_8TB')
    a.out.mkdir(parents=True,exist_ok=False);final.parent.mkdir(parents=True,exist_ok=True);put(a.out/'CONFIG.json',cfg)
    environment=dict(utc=utc(),python=sys.version,executable=sys.executable,platform=platform.platform(),hostname=platform.node(),CUDA_VISIBLE_DEVICES='',model_calls=0,GPU_calls=0,
        aria2_version=subprocess.check_output([cfg['aria2_path'],'--version'],text=True).splitlines()[0])
    for key,value in cfg['expected_environment'].items():need(environment[key]==value,'frozen_transport_environment_changed')
    put(a.out/'ENVIRONMENT.json',environment)
    put(a.out/'RUN_RECORD.json',dict(experiment_id=cfg['experiment_id'],source_commit=cfg['source_commit'],frozen_config=str(a.out/'CONFIG.json'),frozen_config_sha256=digest(a.out/'CONFIG.json'),
        environment_record=str(a.out/'ENVIRONMENT.json'),environment_record_sha256=digest(a.out/'ENVIRONMENT.json'),source_manifest_sha256=digest(a.manifest),
        raw_result_location=str(a.out),aggregate_summary_location=str(a.out/'SUMMARY.json'),gate_decision_location=str(a.out/'GATE.json')))
    child=None;started=time.monotonic()
    try:
        need(not final.exists(),'complete_archive_already_exists_do_not_launch_transport')
        need(not part.exists() or part.with_name(part.name+'.aria2').exists(),'untracked_existing_multi_part_never_overwritten')
        probes=[]
        for url in URLS:probes.append(probe(url));put(a.out/f'MIRROR_PROBE_{len(probes)}.json',probes[-1])
        # One entry with tab-separated mirror URIs means ONE file, not 3 jobs.
        input_path=a.out/'ARIA2_INPUT.txt';input_path.write_text(aria_input(URLS,final.parent,part.name),encoding='ascii')
        command=aria_command(cfg['aria2_path'],input_path,final.parent,part.name);put(a.out/'COMMAND.json',dict(command=command,rpc_enabled=False,total_split=16,max_connections_per_host=6))
        with (a.out/'aria2.log').open('xb') as log,(a.out/'PROGRESS.jsonl').open('x',encoding='utf8') as progress:
            child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=str(final.parent))
            owned=generation(child.pid);put(a.out/'OWNED_ARIA2_HANDLE.json',owned)
            while child.poll() is None:
                need(time.monotonic()-started<=cfg['maximum_wall_seconds'],'bounded_transport_wall_budget_exceeded')
                need(not final.exists(),'aria_created_official_path_before_complete_transport')
                try:record=dict(utc=utc(),wall_seconds=time.monotonic()-started,**log_progress(a.out/'aria2.log'))
                except (OSError,ValueError,RuntimeError) as exc:record=dict(utc=utc(),wall_seconds=time.monotonic()-started,progress_unavailable=type(exc).__name__)
                progress.write(json.dumps(record)+'\n');progress.flush()
                tmp=a.out/'PROGRESS_CURRENT.tmp';tmp.write_text(json.dumps(record,indent=2)+'\n');os.replace(tmp,a.out/'PROGRESS_CURRENT.json')
                time.sleep(10)
            exit_code=child.wait();put(a.out/'ARIA2_EXIT.json',dict(utc=utc(),exit_code=exit_code,owned_process=owned))
        need(exit_code==0,'aria2_failed_partial_and_log_preserved')
        identity=publish(part,final);source_identity(root,mf,a.manifest,cfg)
        summary=dict(status='PASS_COMPLETE_ORIGINAL_ARCHIVE_MULTI_MIRROR_TRANSPORT_SHA256_SIZE_ONLY',experiment_id=cfg['experiment_id'],source_commit=cfg['source_commit'],
                     archive=identity,mirror_probes=probes,wall_seconds=time.monotonic()-started,aria2_exit_code=exit_code,model_calls=0,GPU_calls=0,
                     next_gate='Original prep V2 must independently validate full gzip/tar/allWAV headers before any selection or model call')
        put(a.out/'SUMMARY.json',summary);put(a.out/'GATE.json',dict(status=summary['status'],summary_sha256=digest(a.out/'SUMMARY.json'),model_calls=0,GPU_calls=0))
        print(json.dumps(summary,indent=2))
    except BaseException:
        (a.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
        # Only the child launched by this wrapper is ours; never touch other jobs.
        if child is not None and child.poll() is None:child.terminate();child.wait(timeout=30)
        put(a.out/'GATE.json',dict(status='FAIL_MULTI_MIRROR_TRANSPORT_PARTIAL_PRESERVED',experiment_id=cfg['experiment_id'],source_commit=cfg['source_commit'],model_calls=0,GPU_calls=0));raise
if __name__=='__main__':main()
