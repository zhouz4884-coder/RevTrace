"""Recount original raw trial after process completion; never launch NN."""
import argparse,pathlib,sys
from common import read,put,need,sha,verify_checkout,disk_path,FINAL
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--audit-output',required=True);a=p.parse_args();raw=disk_path(a.out);config=read(raw/'CONFIG.json');dependency=config['base_NN_source'];need(dependency['source_commit']==FINAL,'wrong NN identity')
    gate=verify_checkout(dependency['source_root'],dependency['source_manifest'],FINAL);need(gate['files_verified']==59 and sha(dependency['source_manifest'])==dependency['source_manifest_sha256'],'full original59 identity differs')
    harness=config['harness_source'];need(pathlib.Path(harness['source_root']).resolve()==pathlib.Path(__file__).resolve().parent,'wrong analysis source');verify_checkout(harness['source_root'],harness['source_manifest'],harness['source_commit'])
    sys.path.insert(0,dependency['source_root']);from interference_analysis import analyze_interference
    result=analyze_interference(raw);put(disk_path(a.audit_output),dict(status='PASS_INDEPENDENT_RAW_RECOUNT_UNCHANGED_NN59',source_gate=gate,summary=result))
