"""Stage and run a frozen CPU-only helper on designated disk via approved vault."""
import argparse,json,pathlib,shlex,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];ROOT=E.parents[1]
DISK='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
PY=DISK+'/envs/revtrace-streamcorrect-20261028/bin/python'
def main():
    p=argparse.ArgumentParser()
    for n in ('source','manifest','bundle','branch','remote-project','remote-out','local-out','entry'):p.add_argument('--'+n,required=True)
    a=p.parse_args();local=pathlib.Path(a.local_out);local.mkdir(parents=True,exist_ok=False)
    subprocess.run([sys.executable,'-B',str(ROOT/'experiments/repository_identity_20261027/preflight.py'),'--source',a.source,'--manifest',a.manifest,'--output',str(local/'LOCAL_SOURCE_GATE.json')],check=True,capture_output=True)
    assert a.remote_project.startswith(DISK+'/projects/') and a.remote_out.startswith(DISK+'/results/')
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    def run(command,body=None):
        i,o,e=c.exec_command(command,timeout=300)
        if body is not None:i.write(body);i.flush();i.channel.shutdown_write()
        raw,err=o.read().decode('utf8'),e.read().decode('utf8');return o.channel.recv_exit_status(),raw,err
    try:
        code,raw,err=run('python3 -B -',f"from pathlib import Path\np=Path({a.remote_project!r})\nassert not p.exists()\np.mkdir(parents=True)\n")
        assert code==0,err
        with c.open_sftp() as s:
            s.put(a.bundle,a.remote_project+'/SOURCE.bundle');s.put(a.manifest,a.remote_project+'/SOURCE.json')
        code,raw,err=run('git clone --branch '+shlex.quote(a.branch)+' '+shlex.quote(a.remote_project+'/SOURCE.bundle')+' '+shlex.quote(a.remote_project+'/source'))
        assert code==0,err
        code,raw,err=run('git -C '+shlex.quote(a.remote_project+'/source')+' config core.autocrlf false');assert code==0,err
        command='env CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(a.remote_project+'/source')+' PYTHONDONTWRITEBYTECODE=1 '+shlex.quote(PY)+' -B '+shlex.quote(a.remote_project+'/source/'+a.entry)+' --manifest '+shlex.quote(a.remote_project+'/SOURCE.json')+' --out '+shlex.quote(a.remote_out)
        code,raw,err=run(command);(local/'STDOUT.json').write_text(raw,encoding='utf8');(local/'STDERR.log').write_text(err,encoding='utf8')
        with c.open_sftp() as s:
            for name in s.listdir(a.remote_out):
                if name.endswith(('.json','.log','.txt')):s.get(a.remote_out+'/'+name,str(local/name))
        print(raw);print('CPU_exit='+str(code));return code
    finally:c.close()
if __name__=='__main__':raise SystemExit(main())
