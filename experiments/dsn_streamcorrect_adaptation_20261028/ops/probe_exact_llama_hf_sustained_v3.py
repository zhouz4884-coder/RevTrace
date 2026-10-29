"""64 MiB same-byte memory probe, with contemporaneous sole-writer growth."""
import datetime
import json
import pathlib
import shlex
import sys
import time
import urllib.parse
import urllib.request

T=pathlib.Path(__file__).resolve().parents[1]
OFFSET=268435456;COUNT=67108864;SIZE=2471645608
SHA='1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f'
with urllib.request.urlopen('https://huggingface.co/api/models/unsloth/Llama-3.2-1B-Instruct?blobs=true',timeout=25) as response:metadata=json.load(response)
item=next(row for row in metadata['siblings'] if row['rfilename']=='model.safetensors')
assert metadata['private'] is False and metadata['gated'] is False and item['lfs']['sha256']==SHA and item['size']==SIZE
public_url='https://huggingface.co/unsloth/Llama-3.2-1B-Instruct/resolve/'+metadata['sha']+'/model.safetensors?download=true'
started=time.monotonic()
with urllib.request.urlopen(urllib.request.Request(public_url,headers={'Range':f'bytes={OFFSET}-{OFFSET+COUNT-1}'}),timeout=25) as response:
    response.read(1);ephemeral_url=response.geturl()
    safe=dict(public_url=public_url,final_hostname=urllib.parse.urlsplit(ephemeral_url).hostname,
        http_status=response.status,content_range=response.headers.get('Content-Range'),elapsed_seconds=time.monotonic()-started)
REMOTE=r'''
import datetime,hashlib,json,pathlib,sys,time,urllib.parse,urllib.request
j=json.load(sys.stdin);B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_20261028/assets_v1'
p=B/'models/revtrace_streamcorrect_20261028/llama32_1b_instruct_f8e6b/model.safetensors.partial'
handle=json.loads((O/'ACTIVE_DOWNLOAD_HANDLE.json').read_text());proc=pathlib.Path('/proc')/str(handle['pid'])
st=(proc/'stat').read_text().rsplit(')',1)[1].split();assert int(st[19])==handle['start_ticks']
result=dict(worker_pid=handle['pid'],worker_start_ticks=handle['start_ticks'],offset=j['offset'],count=j['count'],
    worker_cmdline_sha256=hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest())
a=j['offset'];n=j['count']
if p.exists() and p.stat().st_size>=a+n:
 with p.open('rb') as f:f.seek(a);existing=f.read(n)
 result['existing_partial_slice']=dict(bytes=len(existing),sha256=hashlib.sha256(existing).hexdigest())
before=p.stat().st_size;observed_before=datetime.datetime.now(datetime.timezone.utc).isoformat();started=time.monotonic()
try:
 with urllib.request.urlopen(urllib.request.Request(j['download_url'],headers={'Range':f'bytes={a}-{a+n-1}'}),timeout=40) as response:
  opened=time.monotonic();first=response.read(1);first_at=time.monotonic();data=first+response.read(n);finished=time.monotonic()
  result['probe']=dict(public_url=j['public_url'],http_status=response.status,content_range=response.headers.get('Content-Range'),
    final_hostname=urllib.parse.urlsplit(response.geturl()).hostname,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
    open_headers_seconds=opened-started,first_byte_after_headers_seconds=first_at-opened,
    body_after_first_byte_seconds=finished-first_at,total_seconds=finished-started,
    effective_body_bytes_per_second=(len(data)-1)/(finished-first_at))
except BaseException as error:
 result['probe']=dict(error=type(error).__name__,http_status=getattr(error,'code',None),total_seconds=time.monotonic()-started)
after=p.stat().st_size;end=time.monotonic();result['worker_growth']=dict(observed_before_utc=observed_before,
    observed_after_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bytes_before=before,bytes_after=after,
    growth_bytes=after-before,elapsed_seconds=end-started,bytes_per_second=(after-before)/(end-started))
print(json.dumps(result))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
client=ssh_client()
try:
    stdin,stdout,stderr=client.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(REMOTE),timeout=50)
    stdin.write(json.dumps(dict(download_url=ephemeral_url,public_url=public_url,offset=OFFSET,count=COUNT)));stdin.flush();stdin.channel.shutdown_write()
    data=stdout.read();diagnostic=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Bounded sustained memory probe failed; diagnostics suppressed')
    result=json.loads(data);probe=result['probe'];growth=result['worker_growth']
    result.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='64 MiB memory-only probe while original writer remains active; no asset/downloader writes',
        expected_full_bytes=SIZE,expected_full_sha256=SHA,alternative_revision=metadata['sha'],local_route_resolution=safe,
        exact_range=probe.get('http_status')==206 and probe.get('content_range')==f'bytes {OFFSET}-{OFFSET+COUNT-1}/{SIZE}' and probe.get('bytes')==COUNT,
        full_slice_matches_existing_partial=probe.get('sha256')==result.get('existing_partial_slice',{}).get('sha256'))
    if growth['bytes_per_second']>0 and probe.get('effective_body_bytes_per_second'):
        result['hf_body_vs_contemporaneous_original_worker_ratio']=probe['effective_body_bytes_per_second']/growth['bytes_per_second']
    folder=T/'acquisition_monitor_v1';folder.mkdir(exist_ok=True);path=folder/'EXACT_LLAMA_HF_MEMORY_PROBE_V3_64MIB.json'
    assert not path.exists();path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(evidence=str(path),**result),indent=2))
finally:client.close()
