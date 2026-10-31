"""Read only the already authorized experiment host; never expose credentials."""
import hashlib
import json
from pathlib import Path
import shlex
import sys

E=Path(__file__).resolve().parents[1]
R=E.parents[1]
F=R/'experiments/dsn_native_resilience_20261030'
env=json.loads((F/'FROZEN_ENVIRONMENT_v2.json').read_bytes())
config=json.loads((F/'FORMAL_SHORT28_V1_RESULTS_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0764W0209_none_conservative_r0/CONFIG.json').read_bytes())
base=env['executable'].split('/envs/')[0]
params=dict(base=base,asset_manifest=env['assets_manifest_path'],author=config['settings']['backend']['author_root'])
script='PARAMS='+repr(params)+'\n'+r'''
import datetime,hashlib,json,pathlib,platform,shutil,subprocess,sys
def command(args):return subprocess.check_output(args,text=True,timeout=30).strip()
asset=pathlib.Path(PARAMS['asset_manifest'])
result=dict(scope='read-only prerequisite; no model inference or process control',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=platform.node(),python=sys.version,executable=sys.executable,gpus=command(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total,memory.used,utilization.gpu','--format=csv,noheader']),compute_processes=command(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),disk=shutil.disk_usage(PARAMS['base'])._asdict(),memory=[line for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))],author_head=command(['git','-C',PARAMS['author'],'rev-parse','HEAD']),author_dirty=bool(command(['git','-C',PARAMS['author'],'status','--porcelain','--untracked-files=all'])),asset_manifest_sha256=hashlib.sha256(asset.read_bytes()).hexdigest())
print(json.dumps(result))
'''
sys.path.insert(0,r'C:\Users\LENOVO\.codex\local-tools')
from contractkv_ssh_credential import ssh_client
client=ssh_client()
try:
    stdin,stdout,stderr=client.exec_command(shlex.quote(env['executable'])+' -B -',timeout=60)
    stdin.write(script);stdin.flush();stdin.channel.shutdown_write()
    raw=stdout.read();err=stderr.read();rc=stdout.channel.recv_exit_status()
    if rc:raise RuntimeError('read-only host inspection failed: '+err.decode('utf8',errors='replace'))
    result=json.loads(raw)
    assert result['author_head']==env['author_source_commit'] and not result['author_dirty']
    assert result['asset_manifest_sha256']==env['assets_manifest_sha256']
    result['local_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    target=E/'REMOTE_READONLY_ENVIRONMENT_v1.json'
    assert not target.exists()
    target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))
finally:
    client.close()
