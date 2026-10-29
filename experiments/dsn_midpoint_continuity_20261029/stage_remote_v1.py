"""Prepared bounded staging, invoked later by root after timed GPU work; no launch."""
from pathlib import Path
import hashlib,importlib.util,json,shlex
F=Path(__file__).resolve().parent
P='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_midpoint_continuity_20261029'
PY='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/envs/revbatch-cu128/bin/python'
def main():
    spec=importlib.util.spec_from_file_location('revtrace_approved_ssh',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);c=m.ssh_client()
    try:
        _,o,e=c.exec_command('nvidia-smi --query-compute-apps=pid --format=csv,noheader',timeout=15)
        assert not o.read().decode().strip(),'Timed GPU is active: defer staging'
        _,o,e=c.exec_command('mkdir -p '+shlex.quote(P),timeout=15);assert o.channel.recv_exit_status()==0
        s=c.open_sftp()
        for local,remote in [('PLAN_v1.json','PLAN_v1_FROZEN.json'),('SOURCE_SELECTION_v1.json','SOURCE_SELECTION_v1.json'),('ANALYSIS_SOURCE_v1.json','ANALYSIS_SOURCE_v1.json'),('ANALYSIS_SOURCE_v1.bundle','ANALYSIS_SOURCE_v1.bundle')]:
            s.put(str(F/local),P+'/'+remote)
        s.close()
        program='''import pathlib,json,hashlib,subprocess
P=pathlib.Path(PROJECT_VALUE);S=P/'analysis_source_v1';M=json.loads((P/'ANALYSIS_SOURCE_v1.json').read_bytes())
if not S.exists():subprocess.run(['git','-c','core.autocrlf=false','clone',str(P/'ANALYSIS_SOURCE_v1.bundle'),str(S)],check=True)
subprocess.run(['git','config','core.autocrlf','false'],cwd=S,check=True)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()==M['code_commit']
assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=S,text=True).strip()
for r in M['files']:
 b=(S/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
assert hashlib.sha256((P/'PLAN_v1_FROZEN.json').read_bytes()).hexdigest()=='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84'
record=dict(gate='PASS_BOUNDED_STAGING_NOT_GPU_LAUNCH',analysis_source_commit=M['code_commit'],GPU_calls=0,requires_root_allocation=True)
(P/'STAGING_v1.json').write_text(json.dumps(record,indent=2)+'\\n')
print(json.dumps(record))
'''.replace('PROJECT_VALUE',repr(P))
        i,o,e=c.exec_command(shlex.quote(PY)+' -B -',timeout=30);i.write(program);i.channel.shutdown_write()
        out=o.read().decode();error=e.read().decode();assert o.channel.recv_exit_status()==0,error
        print(out)
    finally:c.close()
if __name__=='__main__':main()
