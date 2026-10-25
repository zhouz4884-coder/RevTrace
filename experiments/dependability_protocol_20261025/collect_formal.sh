set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025';O=B/'results/revtrace/dependability_20261025'
S=O/'formal';summary=json.loads((S/'SUMMARY.json').read_text());freeze=json.loads((S/'FREEZE.json').read_text())
assert summary['cells']==summary['expected']==54 and not (S/'STOP.json').exists()
expected=['-'.join(str(c[k]) for k in ['method','consumer','window','order','repeat']) for c in freeze['cells']]
assert summary['completed']==expected and len(set(expected))==54
sys.path.insert(0,str(P/'runtime/scripts'))
from audit_tc_live_qwen import audit
checks=[];handles=[]
for name in expected:
 C=S/name;checks.append(dict(cell=name,**audit(C)))
 for h in json.loads((C/'OWNED_WORKER_HANDLES.json').read_text()):
  q=Path('/proc')/str(h['pid'])
  same=q.exists() and q.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks'])
  assert not same,('owned GPU worker remains',h)
  handles.append(dict(h,verified_exited=True))
launch=json.loads((O/'FORMAL_LAUNCH.json').read_text());proc=Path('/proc')/str(launch['pid'])
same=proc.exists() and proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==launch['start_ticks']
assert not same,'controller not yet exited; do not restart anything'
source=json.loads((P/'runtime/SOURCE_MANIFEST.json').read_text())
for r in source['files']:assert hashlib.sha256((P/'runtime'/r['path']).read_bytes()).hexdigest()==r['sha256']
report={'status':'PASS_COMPLETE54_CERTIFICATE_WAL_CLOCK_AND_OWNED_RESOURCE_CHECK',
 'cells':54,'checks':checks,'owned_worker_handles':handles,'controller_exited':True,
 'current_GPU_processes':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True),
 'no_other_task_touched':True,'time_unix':time.time()}
(O/'FORMAL_CERTIFICATE_AND_RELEASE_v1.json').write_text(json.dumps(report,indent=2)+'\n')
files=[p for p in S.rglob('*') if p.is_file()]
manifest=[{'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(O/'FORMAL_RAW_INDEX_v1.json').write_text(json.dumps({'files':manifest,'cells':54},indent=2)+'\n')
target=O/'formal_evidence_v1.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz') as t:
 t.add(S,arcname='formal')
 for name in ['FORMAL_CERTIFICATE_AND_RELEASE_v1.json','FORMAL_RAW_INDEX_v1.json','FORMAL_LAUNCH.json']:
  t.add(O/name,arcname=name)
 t.add(P/'MANIFEST.json',arcname='MANIFEST.json')
print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
 'cells':54,'owned_workers_exited':len(handles),'GPU_processes':report['current_GPU_processes']}))
PY
