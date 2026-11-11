"""Publish a clearly partial, timestamped readback without touching run inputs."""
from pathlib import Path
import hashlib,json,subprocess
E=Path(__file__).resolve().parents[1];W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace');T=W/'experiments'/E.name
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
assert not git('status','--porcelain')
p=max((E/'launch_ops/PILOT24_V2').glob('POLL_*.json'),key=lambda p:p.stat().st_mtime_ns);x=json.loads(p.read_bytes());r=x['records'];pr=r['PROGRESS.json']
status=dict(record_type='PARTIAL_ACTUAL_GPU_SERVING_READBACK_NOT_FINAL_COMPARISON',observed_utc=x['utc'],matrix_active=x['controller']['active_owned_process'],completed_trials=pr['completed'],planned_trials=pr['planned'],current_cell=pr['current'],runtime_commit='de0936b2e30179d63aeef6e235cd1af685578c58',driver_commit='f367c4e1068a9391a0e99d8537c94995a3388e13',service_plan_sha256='2ceea09f423987faf1b9b3343c15e69ab2f3c437d9e40deb31d6512c30380ed6',predeclared_interpretation='plans/PILOT_OPPORTUNITY_AND_INTERPRETATION_v5.json',completed_cells=r.get('completed_cell_summaries',[]),first_inclusive_observation=r.get('first_cell_inclusive_observation'),scope='Existing two speakers, incomplete timing repeats. All completed SLO failures retained. No final strategy superiority, independent-source confirmation, mechanism attribution or p-value implied. Original four-source reference run and its energy remain separate.')
live=E/'LIVE_GPU_STATUS.json';live.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
readme=E/'README.md';text=readme.read_text(encoding='utf8');note='Current serving progress: [timestamped partial GPU status](LIVE_GPU_STATUS.json).\nThe reference/prelaunch counts below describe their frozen snapshot; the live\nstatus is incomplete and does not replace a final matrix gate.\n'
if note not in text:text=text.replace('Start with ',note+'\nStart with ',1);readme.write_text(text,encoding='utf8')
m=json.loads((T/'DELIVERY_MANIFEST.json').read_bytes());rows={r['path']:r for r in m['files']}
for name in ['LIVE_GPU_STATUS.json','README.md']:
 if name in rows:assert sha(T/name)==rows[name]['sha256']
 raw=(E/name).read_bytes();(T/name).write_bytes(raw);rows[name]=dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
m.update(record_type='BOUNDED_RESEARCH_WITH_PARTIAL_SERVING_READBACK',files=sorted(rows.values(),key=lambda r:r['path']),file_count=len(rows),bytes=sum(r['bytes']for r in rows.values()),new_serving_GPU_trials_completed=pr['completed'],new_serving_GPU_trials_planned=pr['planned'],last_live_readback_utc=x['utc'],serving_matrix_final=False)
m.pop('new_serving_GPU_trials',None)
(T/'DELIVERY_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')
names=['experiments/'+E.name+'/'+n for n in ['README.md','LIVE_GPU_STATUS.json','DELIVERY_MANIFEST.json']]
git('add','--',*names)
assert set(git('diff','--cached','--name-only').splitlines())==set(names)
for name in names:assert subprocess.check_output(['git','-C',str(W),'show',':'+name])==(W/name).read_bytes()
git('commit','--quiet','-m','Record timestamped partial GPU pilot without final comparative claims')
git('-c','http.version=HTTP/1.1','push','origin','HEAD:main')
commit=git('rev-parse','HEAD');remote=git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0];assert commit==remote
print(json.dumps(dict(commit=commit,completed=pr['completed'],planned=pr['planned'],status='PUBLISHED_PARTIAL_READBACK_NOT_FINAL')))
