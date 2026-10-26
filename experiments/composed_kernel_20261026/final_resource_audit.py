"""Read-only final source/resource/completeness audit; never kills a process."""
from pathlib import Path
import json,subprocess,hashlib,importlib.metadata,platform,sys
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def live(h):
    p=Path('/proc')/str(h['pid'])/'stat'
    if not p.exists():return False
    s=p.read_text().rsplit(')',1)[1].split()
    return s[0]!='Z' and s[19]==str(h.get('start_ticks',h.get('linux_start_ticks')))
def main():
    assert any((O/n).exists() for n in ['CAMPAIGN_COMPLETE_v3.json','CAMPAIGN_COMPLETE_v2.json'])
    expected={'boundary_pilot':4,'post_sync_pilot':2,'normal':24,'fault':36,'boundary':16,'post_sync':8}
    handles=[];checks=[]
    for stage,N in expected.items():
        done=read(O/stage/'SUMMARY.json');assert done['expected']==len(done['completed'])==N
        assert not (O/stage/'STOP.json').exists()
        assert read(O/(stage+'_AUDIT.json'))['status'].startswith('PASS_')
        assert read(O/(stage+'_ASSETS.json'))['status'].startswith('PASS_')
        for name in done['completed']:
            E=O/stage/name
            for f in E.glob('attempt*/OWNED_WORKER_HANDLES.json'):handles+=read(f)
            for f in E.glob('OWNER_HANDLE_*.json'):handles.append(read(f))
        checks.append(dict(stage=stage,completed=N,independent_and_asset_gates='PASS'))
    for name in ['CAMPAIGN_OWNER.json','RESUME_OWNER_v2.json','RESUME_OWNER_v3.json']:
        if (O/name).exists():handles.append(read(O/name))
    unique={(h['pid'],str(h.get('start_ticks',h.get('linux_start_ticks')))):h for h in handles}
    assert all(not live(h) for h in unique.values()),'still-owned process; do not call released'
    source=read(P/'runtime/SOURCE_MANIFEST.json')
    for f in source['files']:assert hashlib.sha256((P/'runtime'/f['path']).read_bytes()).hexdigest()==f['sha256']
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)
    environment=dict(python=sys.version,platform=platform.platform(),
        package_versions={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers','numpy','soundfile','safetensors']},
        hardware=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,uuid,driver_version,memory.total','--format=csv,noheader'],text=True),
        note='final observation corroborates per-run environment records, not a fabricated pre-run snapshot')
    dest=O/'FINAL_RESOURCE_AND_SOURCE_v1.json';assert not dest.exists()
    dest.write_text(json.dumps(dict(status='PASS_ALL90_SERVICE_EPISODES_SOURCE_GATES_AND_OWNED_RESOURCE_RELEASE',
        stages=checks,formal_service_episodes=84,development_service_episodes=6,
        owned_handles_verified_exited=len(unique),source=source['code_commit'],source_files=len(source['files']),
        current_GPU_apps=apps,GPUs_observed_idle=not apps.strip(),environment=environment,
        no_new_GPU_queue=True,no_manuscript_edits=True),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',owned_handles_verified_exited=len(unique),GPUs_observed_idle=not apps.strip())))
if __name__=='__main__':main()
