"""Future bounded operator controller; never auto-starts from an idle GPU gap."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025'
CORE=P/'n5_v3/runtime';H=P/'role_probe_v2/probe';O=B/'results/revtrace/dependability_20261025/role_probe_v2'
N5=B/'results/revtrace/dependability_20261025/n5_v3_supervisor_v2'
HARNESS='b08fa4262d1c3ab7e07137eea340d0bb92be200c';RUNTIME='408d75624104e7e11af3f0f2832263c632b10ed8'
WEIGHTS={'model-00001-of-00002.safetensors':'a4cd1f1a04d90b757dc7f7dd26254e69a013b19e80efe590a83c6a3bde8608d6',
 'model-00002-of-00002.safetensors':'6e0b9d9e09e2e0238e7ef3cc8a484ab387e91b90f1900bedf88bc92d7929ccfc'}
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def save(p,v):
 t=p.with_name(p.name+'.partial');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def live(h):
 p=Path('/proc')/str(h['pid'])
 if not p.exists():return False
 s=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
 return s[19]==str(h.get('start_ticks',h.get('linux_start_ticks'))) and s[0]!='Z'
def idle():return not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def source_check():
 for root,commit in [(CORE,RUNTIME),(H,HARNESS)]:
  m=read(root/'SOURCE_MANIFEST.json');assert m['code_commit']==commit
  for r in m['files']:assert sha(root/r['path'])==r['sha256']
def completed_n5():
 for stage,count,handle in [('formal_normal',105,'FORMAL_NORMAL_LAUNCH.json'),('formal_fault',21,'FORMAL_FAULT_LAUNCH.json')]:
  d=read(N5/handle);assert not live(d),'N5 controller still live'
  s=read(N5/stage/'SUMMARY.json');assert s['cells']==s['expected']==len(set(s['completed']))==count
  assert not (N5/stage/'STOP.json').exists()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['pilot','formal'],required=True);a=ap.parse_args()
 completed_n5();assert idle();source_check()
 assert read(P/'role_probe_v2/LINUX_CPU_GATE.json')['tests']==20
 assert read(P/'role_probe_v2/LINUX_CPU_GATE.json')['status']=='PASS_SOURCE_AND_CPU_ONLY'
 if a.stage=='formal':
  gate=read(O/'PILOT_INDEPENDENT_GATE.json');assert gate['decision']=='GO_BOUNDED_ROLE_PROBE' and gate['harness_commit']==HARNESS
 manifest=P/'n5_v3/DEVELOPMENT_MANIFEST.json';sources=read(manifest)['sessions'][:(1 if a.stage=='pilot' else 4)]
 assert len({s['source_id'] for s in sources})==len(sources)
 assert not any('violet saturn alder' in s['reference'].casefold() for s in sources)
 for name,want in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==want
 dest=O/a.stage;dest.mkdir(exist_ok=False,parents=True);cells=[]
 methods=['renderer_only','strict','revtrace','standard']
 for repeat in range(1 if a.stage=='pilot' else 2):
  for i,s in enumerate(sources):
   order=methods[(repeat+i)%4:]+methods[:(repeat+i)%4]
   for method in order:
    for traffic in (['clean','coherent-proposer'] if (repeat+i)%2==0 else ['coherent-proposer','clean']):
     cells.append(dict(source_id=s['source_id'],method=method,traffic=traffic,repeat=repeat))
 expected=8 if a.stage=='pilot' else 64;assert len(cells)==expected
 save(dest/'FREEZE.json',dict(cells=cells,expected=expected,harness_commit=HARNESS,runtime_commit=RUNTIME,
  source_manifest_sha256=sha(manifest),protocol_sha256=sha(H/'GPU_PROTOCOL_v2.md'),controller_sha256=sha(Path(__file__)),
  weights=WEIGHTS,scope='prepared-input operator, not online serving or natural rate',metadata_shadow_is_not_an_extra_case=True))
 completed=[];active=None;proc=None;owned=None;case=None
 try:
  for c in cells:
   assert idle();source_check();active=f"{c['method']}-{c['traffic']}-{c['source_id']}-r{c['repeat']}";case=dest/active
   cmd=[sys.executable,'-u',str(H/'gpu_feedback_probe.py'),'--runtime',str(CORE),'--model',str(B/'models/Qwen3-ASR-1.7B'),
    '--manifest',str(manifest),'--source-id',c['source_id'],'--base-config',str(N5/'formal_normal/fine_fair-nonsaturated-r0/attempt0/config.json'),
    '--output',str(case),'--method',c['method'],'--traffic',c['traffic'],'--harness-commit',HARNESS]
   with (dest/(active+'.log')).open('xb') as f:
    proc=subprocess.Popen(cmd,cwd=H,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    p=Path('/proc')/str(proc.pid);owned=dict(pid=proc.pid,start_ticks=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
     command_sha256=sha(p/'cmdline'),launch_perf=time.perf_counter())
    save(dest/(active+'.OWNER.json'),dict(cell=c,handle=owned,argv=cmd))
    try:rc=proc.wait(timeout=900)
    except subprocess.TimeoutExpired:
     assert live(owned) and os.getpgid(proc.pid)==proc.pid;os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=20);raise
   assert rc==0,'failed actual case retained; no automatic rerun'
   r=read(case/'result.json');assert r['decision']=='COMPLETE_OPERATOR_PENDING_INDEPENDENT_AUDIT'
   handles=read(case/'OWNED_WORKERS.json');assert not any(live(h) for h in handles)
   until=time.perf_counter()+30;own_pids={h['pid'] for h in handles}
   while not idle():
    ids={int(x) for x in subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).split()}
    assert ids<=own_pids,'different task has started; do not touch it'
    assert time.perf_counter()<until;time.sleep(.1)
   save(case/'RUN_COMPLETE_PENDING_AUDIT.json',dict(harness_commit=HARNESS,runtime_commit=RUNTIME,owned_workers_exited=True,
    method=c['method'],traffic=c['traffic'],metadata_shadow_not_extra_GPU_case=True))
   completed.append(active);save(dest/'PROGRESS.json',dict(status='RUNNING',completed=completed,expected=expected));print('COMPLETE',len(completed),active,flush=True)
  for name,want in WEIGHTS.items():assert sha(B/'models/Qwen3-ASR-1.7B'/name)==want
  save(dest/'SUMMARY.json',dict(status='COMPLETE_REAL_GPU_OPERATOR_PENDING_INDEPENDENT_AUDIT',cells=len(completed),expected=expected,
   completed=completed,GPU_queue_closed=True,no_online_SLO_claim=True))
 except BaseException as e:
  if proc is not None and proc.poll() is None and owned and live(owned) and os.getpgid(proc.pid)==proc.pid:
   os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=20)
  save(dest/'STOP.json',dict(active=active,completed=completed,error=repr(e),raw_retained=True,no_automatic_retry=True));raise
if __name__=='__main__':main()
