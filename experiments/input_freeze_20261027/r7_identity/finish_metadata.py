from pathlib import Path
import hashlib,json,subprocess,importlib.util
P=Path(__file__).resolve().parent;R=Path(r'D:\VLA_QWEN\RevTrace')
index=json.loads((P/'REMOTE_INDEX.json').read_text());base='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/models/whisper-base.en'
paths=[r['path'] for r in index['roots'][base]['files'] if r['path'].endswith('.metadata')]
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);client=helper.ssh_client();cache=[]
try:
 with client.open_sftp() as sftp:
  for path in paths:
   with sftp.open(path) as f:raw=f.read()
   cache.append(dict(path=path,content=raw.decode(),sha256=hashlib.sha256(raw).hexdigest()))
finally:client.close()
executor=P/'remote_files/projects/revtrace_r7_0849660/scripts/remote/whisper_batched_executor.py'
digest=hashlib.sha256(executor.read_bytes()).hexdigest();matched=[]
commits=subprocess.check_output(['git','-C',str(R),'log','--all','--format=%H','--','scripts/remote/whisper_batched_executor.py'],text=True).splitlines()
for commit in commits:
 raw=subprocess.check_output(['git','-C',str(R),'show',commit+':scripts/remote/whisper_batched_executor.py'])
 matched.append(dict(commit=commit,sha256=hashlib.sha256(raw).hexdigest(),matches_remote=hashlib.sha256(raw).hexdigest()==digest))
out=dict(huggingface_local_download_receipts=cache,
 caution='download metadata identifies current cached artifact, not measured weight bytes at historical GPU execution',
 executor_current_remote_sha256=digest,executor_git_matches=matched)
(P/'MODEL_AND_EXECUTOR_IDENTITY.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
