"""Only approved tiny entry-route CPU check; never launches a service/model."""
import json,pathlib,shlex,sys
E=pathlib.Path(__file__).resolve().parents[1];B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
PY=B+'/envs/revtrace-streamcorrect-20261028/bin/python';PROJECT=B+'/projects/revtrace_dsn_strengthening_v16_20261111/entry_route_v1';OUT=B+'/results/revtrace/dsn_strengthening_v16_20261111/CPU_ENTRY_ROUTE_V1'
def main():
    local=E/'baseline_ops/CPU_ENTRY_ROUTE_V1';local.mkdir(exist_ok=False)
    sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
    from contractkv_ssh_credential import ssh_client
    c=ssh_client()
    def execute(command,body=None):
        i,o,e=c.exec_command(command,timeout=90)
        if body is not None:i.write(body);i.flush();i.channel.shutdown_write()
        raw,err=o.read().decode('utf8'),e.read().decode('utf8');return o.channel.recv_exit_status(),raw,err
    try:
        code,raw,err=execute('python3 -B -',f"from pathlib import Path\np=Path({PROJECT!r})\nassert not p.exists()\np.mkdir(parents=True)\n");assert code==0,err
        with c.open_sftp() as s:
            s.put(str(E/'packages/ENTRY_ROUTE_SOURCE_v1.bundle'),PROJECT+'/SOURCE.bundle');s.put(str(E/'packages/ENTRY_ROUTE_SOURCE_v1.json'),PROJECT+'/SOURCE.json')
        code,raw,err=execute('git clone --branch codex/dsn-v16-entry-route-v1 '+shlex.quote(PROJECT+'/SOURCE.bundle')+' '+shlex.quote(PROJECT+'/source'));assert code==0,err
        code,raw,err=execute('git -C '+shlex.quote(PROJECT+'/source')+' config core.autocrlf false');assert code==0,err
        d=B+'/projects/revtrace_dsn_strengthening_v16_20261111/pilot_driver_v2';r=B+'/projects/revtrace_dsn_strengthening_v16_20261111/baseline_runtime_v3';plan=B+'/results/revtrace/dsn_strengthening_v16_20261111/PILOT_PREPARATION_V2/SERVICE_PLAN.json'
        command=[PY,'-B',PROJECT+'/source/run_check.py','--manifest',PROJECT+'/SOURCE.json','--driver-source',d+'/source','--driver-manifest',d+'/SOURCE.json','--runtime-source',r+'/source','--runtime-manifest',r+'/SOURCE.json','--plan',plan,'--out',OUT]
        cmd='env CUDA_VISIBLE_DEVICES='+shlex.quote('')+' PYTHONPATH='+shlex.quote(PROJECT+'/source')+' PYTHONDONTWRITEBYTECODE=1 '+shlex.join(command)
        code,raw,err=execute(cmd);(local/'STDOUT.json').write_text(raw,encoding='utf8');(local/'STDERR.log').write_text(err,encoding='utf8')
        with c.open_sftp() as s:
            for name in s.listdir(OUT):
                if name.endswith('.json'):s.get(OUT+'/'+name,str(local/name))
        if code:raise RuntimeError('route CPU gate failed; preserved '+err)
        print(raw)
    finally:c.close()
if __name__=='__main__':main()
