import hashlib,importlib.util,json,shlex
from pathlib import Path
F=Path(__file__).resolve().parent;O=F/'RESULTS_v1'
config=json.loads((F/'CONFIG_v1.json').read_text(encoding='utf8'))
spec=importlib.util.spec_from_file_location('revtrace_authorized_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.ssh_client()
try:
    program='''import hashlib,json,pathlib
P=pathlib.Path(PATH_VALUE)
print(json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in P.iterdir() if p.is_file()}))
'''.replace('PATH_VALUE',repr(config['output']))
    py='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python'
    stdin,stdout,stderr=c.exec_command(shlex.quote(py)+' -B -',timeout=30)
    stdin.write(program);stdin.channel.shutdown_write()
    raw=stdout.read();error=stderr.read();assert stdout.channel.recv_exit_status()==0,error.decode()
    remote=json.loads(raw)
    for name,proof in remote.items():
        b=(O/name).read_bytes()
        assert dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())==proof,name
    (O/'VERIFIED_OUTPUT_BYTES_v1.json').write_text(json.dumps(dict(status='PASS_REMOTE_LOCAL_OUTPUT_BYTES',remote_hash_method='remote Python hashlib SHA256 over each bounded result file',files=remote,total_bytes=sum(x['bytes'] for x in remote.values())),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(status='PASS_REMOTE_LOCAL_OUTPUT_BYTES',files=len(remote),bytes=sum(x['bytes'] for x in remote.values()))))
finally:c.close()
