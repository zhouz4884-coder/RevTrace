"""CPU-only byte/environment readiness. Hashing warms page cache; not a cold run."""
from pathlib import Path
import argparse, datetime, hashlib, importlib.metadata, json, os, subprocess, sys, time, traceback

def need(x, why):
    if not x: raise RuntimeError(why)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_bytes())
def put(p,x):
    with Path(p).open('x',encoding='utf8') as f: json.dump(x,f,indent=2);f.write('\n')
def git(root,*a): return subprocess.check_output(['git','-C',str(root),*a],text=True).strip()
def verify_source(manifest):
    root=Path(__file__).resolve().parent;m=read(manifest)
    need(git(root,'rev-parse','HEAD')==m['code_commit'],'source HEAD')
    need(not git(root,'status','--porcelain','--untracked-files=all'),'dirty source')
    need(set(git(root,'ls-files').splitlines())=={r['path'] for r in m['files']},'source set')
    for r in m['files']:
        p=root/r['path'];need(p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'source bytes '+r['path'])
    return m['code_commit']
def gpu_snapshot():
    def q(s):return subprocess.check_output(['nvidia-smi','--query-'+s,'--format=csv,noheader'],text=True).strip()
    return dict(gpus=q('gpu=index,uuid,name,memory.total,memory.used,utilization.gpu'),compute_owners=q('compute-apps=pid,process_name,used_memory'))
def meminfo():
    keys={'MemAvailable','Cached','SwapCached','Dirty','Writeback'}
    return {l.split(':',1)[0]:l.split(':',1)[1].strip() for l in Path('/proc/meminfo').read_text().splitlines() if l.split(':',1)[0] in keys}
def run(a):
    commit=verify_source(a.manifest);c=read(a.config);out=Path(c['raw_result_location']);base=Path(c['disk_root']).resolve()
    need(out.resolve().is_relative_to(base),'raw disk');out.mkdir(parents=True,exist_ok=False)
    env=dict(python=sys.version,executable=sys.executable,packages={k:importlib.metadata.version(k) for k in c['packages']},source_commit=commit,new_model_calls=0)
    put(out/'CONFIG.json',c);put(out/'ENVIRONMENT.json',env)
    put(out/'RUN_RECORD.json',dict(experiment_id=c['experiment_id'],code_commit=commit,frozen_config=str(out/'CONFIG.json'),frozen_config_sha256=sha(out/'CONFIG.json'),environment_record=str(out/'ENVIRONMENT.json'),environment_record_sha256=sha(out/'ENVIRONMENT.json'),raw_result_location=str(out),aggregate_summary_location=str(out/'SUMMARY.json'),gate_decision_location=str(out/'GATE.json'),prelaunch_record=a.prelaunch,prelaunch_sha256=sha(a.prelaunch)))
    try:
        pre=read(a.prelaunch);need(pre['config_sha256']==sha(a.config) and pre['source_commit']==commit,'prelaunch identity')
        need(env['packages']==c['packages'] and Path(sys.executable).resolve(strict=True)==Path(c['executable']).resolve(strict=True),'package/interpreter identity')
        before=gpu_snapshot();need(not before['compute_owners'],'GPU occupied before readiness')
        before_cache=meminfo();begin=time.perf_counter();rows=[]
        need(sha(c['assets_manifest'])==c['assets_manifest_sha256'],'asset manifest')
        assets=read(c['assets_manifest'])['files']
        for r in assets+c['audio_files']:
            p=Path(r['path']);need(not p.is_symlink() and p.resolve().is_relative_to(base),'asset outside disk')
            need(p.is_file() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],'asset bytes '+str(p))
            rows.append(dict(path=str(p),bytes=r['bytes'],sha256=r['sha256']))
        after=gpu_snapshot();need(not after['compute_owners'],'GPU occupied after readiness')
        need(verify_source(a.manifest)==commit and pre['config_sha256']==sha(a.config),'source/config drift')
        summary=dict(status='PASS_FROZEN_CPU_BYTE_AND_ENVIRONMENT_READINESS',experiment_id=c['experiment_id'],source_commit=commit,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),asset_manifest_sha256=c['assets_manifest_sha256'],asset_files=len(assets),audio_files=len(c['audio_files']),checked_bytes=sum(r['bytes'] for r in rows),rows=rows,environment=env,before=before,after=after,before_meminfo=before_cache,after_meminfo=meminfo(),verification_wall_seconds=time.perf_counter()-begin,new_model_calls=0,scope='File hashing and metadata only. Cache warmed by this check; no CUDA allocation, model inference, reservation, or serving result.')
        put(out/'SUMMARY.json',summary);put(out/'GATE.json',dict(status=summary['status'],summary_sha256=sha(out/'SUMMARY.json'),new_model_calls=0))
    except BaseException:
        put(out/'GATE.json',dict(status='FAIL_READINESS_PRESERVED',failure=traceback.format_exc(),new_model_calls=0));raise
    return {k:v for k,v in summary.items() if k not in {'rows','environment','before','after'}}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('manifest','config','prelaunch'):p.add_argument('--'+k,required=True)
    print(json.dumps(run(p.parse_args())))
