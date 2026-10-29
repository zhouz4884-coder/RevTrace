"""Metadata and bounded 1 MiB memory-only probes; no target-file writes.

Resolved CDN URLs are sent only through an anonymous SSH stdin pipe and are not
printed or saved. No authenticated routes, downloader changes, or GPU calls.
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
EXPECTED = '1ff795ff6a07e6a68085d206fb84417da2f083f68391c2843cd2b8ac6df8538f'
SIZE = 2471645608
COUNT = 1048576
api = 'https://huggingface.co/api/models/unsloth/Llama-3.2-1B-Instruct?blobs=true'
with urllib.request.urlopen(api, timeout=25) as response:
    metadata = json.load(response)
item = next(x for x in metadata['siblings'] if x['rfilename'] == 'model.safetensors')
assert metadata['private'] is False and metadata['gated'] is False
assert item['lfs']['sha256'] == EXPECTED and item['size'] == SIZE
identity = dict(public_metadata_url=api, repository=metadata['id'], revision=metadata['sha'],
    private=metadata['private'], gated=metadata['gated'], git_lfs_pointer_blob=item['blobId'],
    sha256=item['lfs']['sha256'], bytes=item['size'], exact_frozen_weight_match=True)
routes = [
    dict(name='modelscope_api', public_url='https://modelscope.cn/api/v1/models/LLM-Research/Llama-3.2-1B-Instruct/repo?Revision=f8e6bf8fec8194d75228ef38e85fda45c6046fbd&FilePath=model.safetensors'),
    dict(name='modelscope_resolve', public_url='https://modelscope.cn/models/LLM-Research/Llama-3.2-1B-Instruct/resolve/f8e6bf8fec8194d75228ef38e85fda45c6046fbd/model.safetensors'),
    dict(name='public_unsloth_exact_sha', public_url='https://huggingface.co/unsloth/Llama-3.2-1B-Instruct/resolve/'+metadata['sha']+'/model.safetensors?download=true'),
]

def resolve(row):
    started = time.monotonic()
    try:
        request = urllib.request.Request(row['public_url'], headers={'Range': 'bytes=0-1048575'})
        with urllib.request.urlopen(request, timeout=25) as response:
            first = response.read(COUNT + 1)
            safe = dict(name=row['name'], public_url=row['public_url'],
                final_hostname=urllib.parse.urlsplit(response.geturl()).hostname,
                http_status=response.status, content_range=response.headers.get('Content-Range'),
                content_length=response.headers.get('Content-Length'), bytes=len(first),
                elapsed_seconds=time.monotonic()-started,
                memory_sha256=hashlib.sha256(first).hexdigest())
            return dict(safe=safe, download_url=response.geturl())
    except BaseException as error:
        return dict(safe=dict(name=row['name'], public_url=row['public_url'],
            error=type(error).__name__, http_status=getattr(error, 'code', None),
            elapsed_seconds=time.monotonic()-started))

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    resolved = list(pool.map(resolve, routes))
remote = r'''
import concurrent.futures,hashlib,json,sys,time,urllib.parse,urllib.request
jobs=json.load(sys.stdin)
def probe(job):
 row=job['safe'];started=time.monotonic()
 try:
  request=urllib.request.Request(job['download_url'],headers={'Range':'bytes=0-1048575'})
  with urllib.request.urlopen(request,timeout=25) as response:
   data=response.read(1048577)
   return dict(name=row['name'],public_url=row['public_url'],http_status=response.status,
    final_hostname=urllib.parse.urlsplit(response.geturl()).hostname,content_range=response.headers.get('Content-Range'),
    content_length=response.headers.get('Content-Length'),bytes=len(data),elapsed_seconds=time.monotonic()-started,
    memory_sha256=hashlib.sha256(data).hexdigest())
 except BaseException as error:
  return dict(name=row['name'],public_url=row['public_url'],error=type(error).__name__,
   http_status=getattr(error,'code',None),elapsed_seconds=time.monotonic()-started)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:result=list(pool.map(probe,jobs))
print(json.dumps(result))
'''
sys.path.insert(0, r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client

client = ssh_client()
try:
    stdin, stdout, stderr = client.exec_command(
        '/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python -B -c '
        + shlex.quote(remote), timeout=40)
    stdin.write(json.dumps([row for row in resolved if 'download_url' in row])); stdin.flush(); stdin.channel.shutdown_write()
    data=stdout.read(); diagnostics=stderr.read(); rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('Memory route probe failed; temporary URL diagnostics suppressed')
    result=dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='metadata and bounded 1 MiB in-memory only; no downloader/file changes',
        identity=identity, local_windows_probes=[row['safe'] for row in resolved], remote_probes=json.loads(data))
    folder=T/'acquisition_monitor_v1';folder.mkdir(exist_ok=True)
    path=folder/'EXACT_LLAMA_MEMORY_ROUTE_PROBE_V1.json'
    assert not path.exists()
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(evidence=str(path),**result),indent=2))
finally:
    client.close()
