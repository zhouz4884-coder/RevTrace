"""Bounded 16 MiB same-offset in-memory transport comparison; no writes.

Ephemeral CDN URLs exist only in RAM and an anonymous SSH stdin pipe. The
existing single downloader remains active throughout this diagnostic.
"""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import shlex
import sys
import time
import urllib.parse
import urllib.request

T = pathlib.Path(__file__).resolve().parents[1]
OFFSET = 268435456
COUNT = 16777216
EXPECTED = '1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f'
SIZE = 2471645608
with urllib.request.urlopen('https://huggingface.co/api/models/unsloth/Llama-3.2-1B-Instruct?blobs=true', timeout=25) as response:
    metadata = json.load(response)
item = next(row for row in metadata['siblings'] if row['rfilename'] == 'model.safetensors')
assert metadata['private'] is False and metadata['gated'] is False
assert item['lfs']['sha256'] == EXPECTED and item['size'] == SIZE
routes = [
    dict(name='modelscope_api', public_url='https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo?Revision=f8e6bf8fec8194d75228ef38e85fda45c6046fbd&FilePath=model.safetensors'),
    dict(name='public_unsloth_exact_sha', public_url='https://huggingface.co/unsloth/Llama-3.2-1B-Instruct/resolve/'+metadata['sha']+'/model.safetensors?download=true'),
]

def resolve(row):
    started = time.monotonic()
    try:
        request=urllib.request.Request(row['public_url'],headers={'Range':f'bytes={OFFSET}-{OFFSET+COUNT-1}'})
        with urllib.request.urlopen(request,timeout=25) as response:
            response.read(1)
            return dict(safe=dict(name=row['name'],public_url=row['public_url'],
                local_resolve_seconds=time.monotonic()-started,http_status=response.status,
                content_range=response.headers.get('Content-Range'),
                final_hostname=urllib.parse.urlsplit(response.geturl()).hostname),
                download_url=response.geturl(),offset=OFFSET,count=COUNT)
    except BaseException as error:
        return dict(safe=dict(name=row['name'],public_url=row['public_url'],
            error=type(error).__name__,http_status=getattr(error,'code',None)))

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    jobs=list(pool.map(resolve,routes))
assert all('download_url' in job for job in jobs), 'public route resolution failed'
REMOTE = r'''
import concurrent.futures,hashlib,json,pathlib,sys,time,urllib.parse,urllib.request
jobs=json.load(sys.stdin)
def probe(job):
 safe=job['safe'];started=time.monotonic();a=job['offset'];n=job['count']
 try:
  request=urllib.request.Request(job['download_url'],headers={'Range':f'bytes={a}-{a+n-1}'})
  with urllib.request.urlopen(request,timeout=30) as response:
   opened=time.monotonic();first=response.read(1);first_at=time.monotonic();data=first+response.read(n);finished=time.monotonic()
   return dict(name=safe['name'],public_url=safe['public_url'],http_status=response.status,
    final_hostname=urllib.parse.urlsplit(response.geturl()).hostname,content_range=response.headers.get('Content-Range'),
    bytes=len(data),open_headers_seconds=opened-started,first_byte_after_headers_seconds=first_at-opened,
    body_after_first_byte_seconds=finished-first_at,total_seconds=finished-started,
    effective_body_bytes_per_second=(len(data)-len(first))/(finished-first_at),
    memory_sha256=hashlib.sha256(data).hexdigest())
 except BaseException as error:
  return dict(name=safe['name'],public_url=safe['public_url'],error=type(error).__name__,
   http_status=getattr(error,'code',None),total_seconds=time.monotonic()-started)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(probe,jobs))
p=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/models/revtrace_streamcorrect_20261028/llama32_1b_instruct_f8e6b/model.safetensors.partial')
current_slice=None;a=jobs[0]['offset'];n=jobs[0]['count']
if p.exists() and p.stat().st_size>=a+n:
 with p.open('rb') as f:f.seek(a);data=f.read(n)
 current_slice=dict(offset=a,bytes=len(data),memory_sha256=hashlib.sha256(data).hexdigest())
print(json.dumps(dict(probes=result,existing_partial_slice=current_slice)))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client

client=ssh_client()
try:
    stdin,stdout,stderr=client.exec_command('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '+shlex.quote(REMOTE),timeout=45)
    stdin.write(json.dumps(jobs));stdin.flush();stdin.channel.shutdown_write()
    data=stdout.read();diagnostic=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Memory probe failed; temporary URL diagnostics suppressed')
    result=json.loads(data)
    result.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='two 16 MiB concurrent memory probes while original downloader remains active; no downloader or asset writes',
        offset=OFFSET,count=COUNT,expected_full_sha256=EXPECTED,expected_full_bytes=SIZE,
        alternative_public_revision=metadata['sha'],local_route_resolution=[job['safe'] for job in jobs])
    all_probes=result['probes']
    result['all_ranges_exact']=all(row.get('http_status')==206 and row.get('bytes')==COUNT and row.get('content_range')==f'bytes {OFFSET}-{OFFSET+COUNT-1}/{SIZE}' for row in all_probes)
    result['same_complete_slice_sha256']=len({row.get('memory_sha256') for row in all_probes})==1 and all(row.get('bytes')==COUNT for row in all_probes)
    if result['existing_partial_slice']:
        result['matches_existing_partial_slice']=all(row.get('memory_sha256')==result['existing_partial_slice']['memory_sha256'] for row in all_probes)
    folder=T/'acquisition_monitor_v1';folder.mkdir(exist_ok=True);path=folder/'EXACT_LLAMA_MEMORY_ROUTE_PROBE_V2_16MIB.json'
    assert not path.exists();path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(evidence=str(path),**result),indent=2))
finally:
    client.close()
