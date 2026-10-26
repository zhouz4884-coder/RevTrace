"""Read-only final own-process/model identity check. No kill/restart."""
from pathlib import Path
import json,hashlib,subprocess,time,sys
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
def main():
    assert json.loads((O/'M_FORMAT_AUDIT.json').read_text())['episodes']==64
    assert json.loads((O/'X_SERVICE_AUDIT.json').read_text())['runs']==16
    assert json.loads((O/'x_service_oracle_v1/SUMMARY.json').read_text())['status']=='PASS_ALL_ACTUAL_PARENT_CONTROLS'
    own=[]
    for p in O.glob('*OWNER*.json'):
        x=json.loads(p.read_text())
        for key,pid in x.items():
            if 'pid' not in key.lower() or not isinstance(pid,int):continue
            proc=Path('/proc')/str(pid)
            if proc.exists():
                raw=proc.joinpath('cmdline').read_bytes();state=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[0]
                if b'lp1_20261026' in raw and state!='Z':own.append(dict(pid=pid,owner=str(p),state=state))
    assert not own,'an owned controller is still running'
    for f in (O/'x_service_v2').glob('*/attempt0/OWNED_WORKER_HANDLES.json'):
        for h in json.loads(f.read_text()):
            p=Path('/proc')/str(h['pid'])
            if p.exists():
                tail=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
                assert tail[19]!=h['linux_start_ticks'] or tail[0]=='Z','original GPU worker alive'
    inv=json.loads((O/'export_v1/MODEL_INVENTORY.json').read_text());checked=0
    for r in inv['models']:
        p=B/'models'/r['model']/r['file'];h=hashlib.sha256()
        with p.open('rb') as stream:
            for b in iter(lambda:stream.read(2**22),b''):h.update(b)
        assert h.hexdigest()==r['sha256'];checked+=1
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)
    result=dict(status='COMPLETE_ALL_SCOPED_RUNS_AND_INDEPENDENT_GATES',observed_unix=time.time(),own_controllers_running=own,
        original_service_GPU_workers_exited=True,model_inventory_files_reverified=checked,active_compute_apps=apps,
        GPU_released_by_this_task=True,pending_GPU_stages=[],paper_edits=False,
        source_branches=dict(operator='f33acdb4475be6c43e3b72dba88e21bb1ad4e940',memory='e83983004b22f0e7b6081157260f9954f4cf2ff7',
            service='4d23d23569cb39db231ed5748f2604c26e663eec',content_control='ea9fc8999076aaf773e7618e170953fa1ccd1280'))
    (O/'COMPLETION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
