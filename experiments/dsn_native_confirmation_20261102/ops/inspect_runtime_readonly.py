"""Read-only prelaunch inspection through the approved local SSH route."""
import hashlib,json,shlex,sys
from pathlib import Path
E=Path(__file__).resolve().parents[1];R=E.parents[1]
F=R/'experiments/dsn_native_resilience_20261030'
env=json.loads((F/'FROZEN_ENVIRONMENT_v2.json').read_bytes())
config=json.loads((F/'FORMAL_SHORT28_V1_RESULTS_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0764W0209_none_conservative_r0/CONFIG.json').read_bytes())
params=dict(base=env['executable'].split('/envs/')[0],asset_manifest=env['assets_manifest_path'],author=config['settings']['backend']['author_root'])
script='P='+repr(params)+'\n'+r'''
import datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys
def cmd(a):return subprocess.check_output(a,text=True,timeout=30).strip()
asset=pathlib.Path(P['asset_manifest'])
r=dict(scope='Read-only prerequisites, no inference or process control',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=platform.node(),python=sys.version,executable=sys.executable,gpus=cmd(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader']),compute_processes=cmd(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),disk=shutil.disk_usage(P['base'])._asdict(),memory=[s for s in pathlib.Path('/proc/meminfo').read_text().splitlines() if s.startswith(('MemTotal:','MemAvailable:'))],author_head=cmd(['git','-C',P['author'],'rev-parse','HEAD']),author_dirty=bool(cmd(['git','-C',P['author'],'status','--porcelain','--untracked-files=all'])),asset_manifest_sha256=hashlib.sha256(asset.read_bytes()).hexdigest())
print(json.dumps(r))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
c=ssh_client()
try:
    i,o,e=c.exec_command(shlex.quote(env['executable'])+' -B -',timeout=60)
    i.write(script);i.flush();i.channel.shutdown_write();raw=o.read();err=e.read();rc=o.channel.recv_exit_status()
    if rc:raise RuntimeError(err.decode(errors='replace')[-1500:])
    result=json.loads(raw)
    assert result['author_head']==env['author_source_commit'] and not result['author_dirty']
    assert result['asset_manifest_sha256']==env['assets_manifest_sha256']
    result['local_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target=E/'REMOTE_PRELAUNCH_ENVIRONMENT_v1.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
finally:c.close()
