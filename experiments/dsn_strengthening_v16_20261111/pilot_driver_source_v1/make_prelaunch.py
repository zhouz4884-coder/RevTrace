"""Bind Root-provided CURRENT/explicit gates to one frozen reference/service plan."""
import argparse,pathlib,datetime
from confirmation_common import read,sha,put,verify_source,validate_prelaunch,need
def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','plan','root-noarg-preflight','driver-explicit-preflight','asset-byte-gate','exclusive-window-id','out'):p.add_argument('--'+n,required=True)
    a=p.parse_args();plan=read(a.plan);own=verify_source(pathlib.Path(__file__).parent,a.manifest)
    driver=plan.get('driver',plan.get('generator'));base=plan['actual_NN']
    need(driver['source_commit']==own['source_commit'] and driver['source_manifest_sha256']==own['source_manifest_sha256'],'plan generator/driver differs')
    pre=dict(plan_sha256=sha(a.plan),root_noarg_preflight=a.root_noarg_preflight,root_noarg_preflight_sha256=sha(a.root_noarg_preflight),driver_explicit_preflight=a.driver_explicit_preflight,driver_explicit_preflight_sha256=sha(a.driver_explicit_preflight),exclusive_GPU_window_authorized_by_root=True,exclusive_window_id=a.exclusive_window_id,asset_byte_gate=dict(path=a.asset_byte_gate,sha256=sha(a.asset_byte_gate)),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    need(bool(a.exclusive_window_id.strip()),'Root window identity required');validate_prelaunch(pre,a.plan,driver,base);put(a.out,pre)
if __name__=='__main__':main()
