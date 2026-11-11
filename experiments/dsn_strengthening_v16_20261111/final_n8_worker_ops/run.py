import json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];OPS=E/'final_n8_worker_ops';B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9';P=B+'/projects/revtrace_dsn_strengthening_v16_20261111/final_n8_worker_v1';O=B+'/results/revtrace/dsn_strengthening_v16_20261111/FINAL_N8_WORKER_V1';PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python'
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools');from contractkv_ssh_credential import ssh_client
c=ssh_client()
def run(cmd,body=None):
 i,o,e=c.exec_command(cmd,timeout=180)
 if body is not None:i.write(body);i.flush();i.channel.shutdown_write()
 raw,err=o.read().decode(),e.read().decode();return o.channel.recv_exit_status(),raw,err
try:
 code,raw,err=run('python3 -B -',f"from pathlib import Path\np=Path({P!r})\nassert not p.exists()\np.mkdir(parents=True)\n");assert code==0,err
 with c.open_sftp() as s:
  for local,remote in [(E/'packages/FINAL_N8_WORKER_SOURCE_v1.bundle',P+'/SOURCE.bundle'),(E/'packages/FINAL_N8_WORKER_SOURCE_v1.json',P+'/SOURCE.json'),(OPS/'SELECTION.json',P+'/SELECTION.json')]:s.put(str(local),remote)
 code,raw,err=run('git clone --branch codex/dsn-v16-final-n8-worker-v1 '+shlex.quote(P+'/SOURCE.bundle')+' '+shlex.quote(P+'/source'));assert code==0,err
 code,raw,err=run('git -C '+shlex.quote(P+'/source')+' config core.autocrlf false');assert code==0,err
 cmd=['env','CUDA_VISIBLE_DEVICES=','PYTHONDONTWRITEBYTECODE=1',PY,'-B',P+'/source/derive.py','--manifest',P+'/SOURCE.json','--selection',P+'/SELECTION.json','--out',O]
 code,raw,err=run(shlex.join(cmd));(OPS/'STDOUT.json').write_text(raw,encoding='utf8');(OPS/'STDERR.log').write_text(err,encoding='utf8')
 with c.open_sftp() as s:
  for name in s.listdir(O):
   if name.endswith(('.json','.log')):s.get(O+'/'+name,str(OPS/name))
 print(raw)
 if code:raise RuntimeError(err)
finally:c.close()
