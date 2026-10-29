"""Machine-local source selection after the native scope; never edits old runs."""
from pathlib import Path
import subprocess, json, hashlib, os, datetime

R=Path(__file__).resolve().parents[2]
F=Path(__file__).resolve().parent
I=R/'experiments/repository_identity_20261027'
S=R/'experiments/physical_retirement_20261028/source_v3'
M=R/'experiments/physical_retirement_20261028/packages/SOURCE_v3.json'
C='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
H='19547df369c2899d4cb0eec49d137eff7f160802668072033ae9197565771625'

def main():
    assert hashlib.sha256(M.read_bytes()).hexdigest()==H
    assert hashlib.sha256((F/'PLAN_v1.json').read_bytes()).hexdigest()=='fb344f88774b8cdae15af213e66f296adcaf4632fa982383e730f92a18023b84'
    cmd=['python',str(I/'preflight.py')]
    subprocess.run(cmd+['--source',str(S),'--manifest',str(M),'--output',str(F/'EXPLICIT_SOURCE_PREFLIGHT_v1.json')],cwd=R,check=True)
    q=I/'CURRENT.json';old=q.read_bytes();previous=json.loads(old)
    assert previous['source_commit']=='61c9afac00561f7ff1351f3eba9fd95adb239e8c'
    backup=F/'CURRENT_BEFORE_MIDPOINT_v1.json'
    with backup.open('xb') as f:f.write(old)
    new=dict(previous,updated_date='2026-10-29',source_worktree=str(S),source_commit=C,
             source_manifest=str(M),source_manifest_sha256=H,
             analysis_source=str(F/'analysis_source_v1'),analysis_commit='fb8a429d95ab682002bc39aedca8bcbec8942b67',
             research_state=str(F/'ACTIVE_STATE.json'),GPU_queue='UNIQUE_MIDPOINT12_AFTER_COMPLETED_NATIVE_AND_RXK_QUALITY',
             scope='Machine-local launch pointer only. Native runtime and completed runs retain their original execution identities.',previous_pointer=str(backup))
    temp=I/'CURRENT.midpoint_v1.tmp';assert not temp.exists()
    temp.write_text(json.dumps(new,indent=2)+'\n',encoding='utf8');os.replace(temp,q)
    try:
        subprocess.run(cmd+['--output',str(F/'LOCAL_PREFLIGHT_BEFORE_GPU_v1.json')],cwd=R,check=True)
    except BaseException:
        temp.write_bytes(old);os.replace(temp,q);raise
    result=dict(gate='PASS_LOCAL_POINTER_SELECTED_F0_WITH_FRESH_NO_ARGUMENT_PREFLIGHT',
                previous_sha256=hashlib.sha256(old).hexdigest(),current_sha256=hashlib.sha256(q.read_bytes()).hexdigest(),
                selected_source_commit=C,time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                old_runs_relabelled=False,neural_calls=0)
    (F/'POINTER_SELECTION_v1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
