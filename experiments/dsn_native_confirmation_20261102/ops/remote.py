"""Approved SSH transport; never returns or records credentials."""
from pathlib import Path
import json,shlex,sys

E=Path(__file__).resolve().parents[1]
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_native_confirmation_20261102'
O=B+'/results/revtrace/dsn_native_confirmation_20261102'
PY=json.loads((E/'REMOTE_PRELAUNCH_ENVIRONMENT_v1.json').read_bytes())['executable']

class Remote:
    def __enter__(self):
        sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
        from contractkv_ssh_credential import ssh_client
        self.client=ssh_client();return self
    def __exit__(self,*args):self.client.close()
    def python(self,script,timeout=60):
        i,o,e=self.client.exec_command(shlex.quote(PY)+' -B -',timeout=timeout)
        i.write(script);i.flush();i.channel.shutdown_write()
        raw=o.read();err=e.read();rc=o.channel.recv_exit_status()
        if rc:raise RuntimeError('Remote rc '+str(rc)+'\n'+raw.decode(errors='replace')[-6000:]+'\n'+err.decode(errors='replace')[-4000:])
        return raw
    def put(self,local,remote):
        assert Path(remote).is_relative_to(Path(B))
        raw=Path(local).read_bytes();s=self.client.open_sftp()
        try:
            try:
                with s.open(remote,'rb') as f:assert f.read()==raw,'immutable staged file differs: '+remote
            except FileNotFoundError:
                with s.open(remote,'wx') as f:f.write(raw);f.flush()
        finally:s.close()
    def get(self,remote,local,maximum=20_000_000):
        assert Path(remote).is_relative_to(Path(B))
        s=self.client.open_sftp()
        try:
            assert s.stat(remote).st_size<=maximum
            with s.open(remote,'rb') as f:raw=f.read()
        finally:s.close()
        target=Path(local);target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==raw,'immutable local mirror differs'
        else:target.write_bytes(raw)
        return raw
