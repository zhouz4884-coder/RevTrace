"""Download bounded non-secret historical source/evidence only, read-only SFTP."""
from pathlib import Path
import importlib.util,json,hashlib
P=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
project=B+'/projects/revtrace_r7_0849660'
paths=[project+'/CODE_COMMIT',*[project+'/'+p for p in [
 'scripts/remote/run_r7_whisper_quality.py','scripts/remote/run_r7_whisper_quality.sh',
 'scripts/remote/run_whisper_w_quality.py','scripts/remote/whisper_batched_executor.py',
 'src/revtrace/feedback_coherence.py','src/revtrace/feedback_metrics.py','src/revtrace/whisper_state.py',
 'results/phase0/revbatch/environment/requirements-lock.txt']],
 B+'/datasets/revtrace/librispeech/whisper-w-quality.json',
 B+'/results/revtrace/r7_efsc/whisper_base_preflight/frozen_policy.json',
 B+'/logs/revtrace/r7_efsc/whisper_base_quality/paired-128.log',
 B+'/logs/revtrace/r7_efsc/whisper_base_quality/paired-128-traced.log',
 B+'/results/revtrace/r7_efsc/whisper_base_preflight/w1/seed2026080501.json',
 B+'/results/revtrace/r8_csdr/snapshot-delta.json',
 B+'/results/revtrace/r8_csdr/r8-replay-audit-30k-v2.json']
for name in ['config.json','generation_config.json','preprocessor_config.json','tokenizer_config.json','special_tokens_map.json']:
 paths.append(B+'/models/whisper-base.en/'+name)
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
client=helper.ssh_client();records=[]
try:
 with client.open_sftp() as sftp:
  for path in paths:
   target=P/'remote_files'/path.removeprefix(B+'/');target.parent.mkdir(parents=True,exist_ok=True)
   try:
    st=sftp.stat(path)
    if st.st_size>4*1024*1024:raise ValueError('bounded file limit')
    with sftp.open(path,'rb') as f:data=f.read()
    target.write_bytes(data)
    records.append(dict(remote_path=path,local_path=str(target),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
   except FileNotFoundError:records.append(dict(remote_path=path,status='MISSING'))
finally:client.close()
(P/'FETCH_INDEX.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(files=len(records),missing=[r for r in records if r.get('status')=='MISSING'])))
