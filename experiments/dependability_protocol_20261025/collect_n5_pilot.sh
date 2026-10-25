set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_dependability_20261025/n5_v1';O=B/'results/revtrace/dependability_20261025/n5_v1'
s=json.loads((O/'pilot/SUMMARY.json').read_text());assert s['cells']==s['expected']==4 and not (O/'pilot/STOP.json').exists()
launch=json.loads((O/'PILOT_LAUNCH.json').read_text());p=Path('/proc')/str(launch['pid'])
assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==launch['start_ticks'])
handles=[]
for name in s['completed']:
 C=O/'pilot'/name/'attempt0';r=json.loads((C/'result.json').read_text());assert r['fine_window_accounting_complete']
 for h in json.loads((C/'OWNED_WORKER_HANDLES.json').read_text()):
  p=Path('/proc')/str(h['pid']);assert not (p.exists() and p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==str(h['linux_start_ticks']))
  handles.append(dict(h,verified_exited=True))
 print(json.dumps({'cell':name,'commits':r['certified_commits'],'input_fsync_calls':r['input_fsync_calls'],
   'controller_CPU':r['envelope_decision_CPU_seconds'],'modes':r['fine_window_outcomes']}))
save={'status':'PASS4_RUN_COMPLETENESS_AND_OWNED_EXIT_PENDING_INDEPENDENT_AUDIT','workers':handles,
 'current_GPU_processes':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader'],text=True)}
(O/'PILOT_RELEASE.json').write_text(json.dumps(save,indent=2)+'\n')
index=[{'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (O/'pilot').rglob('*') if p.is_file()]
(O/'PILOT_RAW_INDEX_v1.json').write_text(json.dumps({'files':index},indent=2)+'\n')
target=O/'pilot_evidence_v1.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz') as t:
 t.add(O/'pilot',arcname='pilot')
 for name in ['PILOT_RELEASE.json','PILOT_RAW_INDEX_v1.json','PILOT_LAUNCH.json']:t.add(O/name,arcname=name)
 for name in ['DEVELOPMENT_MANIFEST.json','CPU_N5_LINUX_v1.xml']:t.add(P/name,arcname=name)
print(json.dumps({'archive':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(index)}))
PY
