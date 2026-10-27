"""Approved credential helper; read package identity only, no GPU imports/calls."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import time

helper_path = Path(r"C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py")
spec = importlib.util.spec_from_file_location("authorized_ssh", helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
base = "/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9"
source = """import importlib.metadata as m,json,os,sys
names=['langgraph','langgraph-checkpoint-sqlite','langgraph-checkpoint','langchain-core','torch','transformers']
out={}
for name in names:
 try: out[name]=m.version(name)
 except m.PackageNotFoundError: out[name]=None
print(json.dumps(dict(python=sys.version,executable=sys.executable,real_prefix=os.path.realpath(sys.prefix),packages=out)))
"""
command = base + "/envs/revbatch-cu128/bin/python -c " + shlex.quote(source)
client = helper.ssh_client()
try:
    _, out, err = client.exec_command(command, timeout=50)
    stdout, stderr = out.read().decode(), err.read().decode()
    code = out.channel.recv_exit_status()
    record = {"observed_ns": time.time_ns(), "command": command, "returncode": code,
              "stdout": stdout, "stderr": stderr, "helper_source_sha256": hashlib.sha256(helper_path.read_bytes()).hexdigest(),
              "scope": "environment metadata only; no GPU/model invocation"}
    p = Path(__file__).parent / "ENVIRONMENT_BASE_READ.json"
    assert not p.exists()
    p.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
finally:
    client.close()
