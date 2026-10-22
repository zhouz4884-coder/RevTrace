"""Freeze original evidence and source byte identities; no GPU operations."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
B=Path(sys.argv[1]);P=B/'projects/revtrace_opportunity_20261022';O=B/'results/revtrace/opportunity_20261022'
audit=json.loads((O/'INDEPENDENT_AUDIT.json').read_text());assert audit['completed_GPU_fault_trials']==22 and audit['status'].startswith('PASS_INDEPENDENT')
assert len(audit['logical_job_reconstruction_checks'])==22
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
raw=[]
for p in sorted(O.rglob('*')):
 if p.is_file() and p.name not in ['RAW_EVIDENCE_INDEX_v2.json','RESOURCE_CLOSED.json'] and not p.name.startswith('BOUNDED_EVIDENCE'):
  raw.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
sources=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(P.glob('*')) if p.is_file()]
(O/'RAW_EVIDENCE_INDEX_v2.json').write_text(json.dumps({'files':raw,'sources':sources,'all_on_8TB':True,'old_D_raw_index_untouched':True,'failed_pilot_included':True,'supersedes_initial_bounded_freeze':True},indent=2)+'\n')
resource={'no_own_GPU_queue':True,'no_further_GPU_work':True,'GPU':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader'],text=True),'admitted_complete_trials':22,'CPU_only_after_this_point':True};(O/'RESOURCE_CLOSED.json').write_text(json.dumps(resource,indent=2)+'\n')
with tarfile.open(O/'BOUNDED_EVIDENCE_v2.tar.gz','w:gz') as t:
 for p in sorted(O.rglob('*')):
  if p.is_file() and not p.name.startswith('BOUNDED_EVIDENCE') and p.stat().st_size<2_000_000:t.add(p,arcname=p.relative_to(O).as_posix())
print(json.dumps({'status':'BOUNDED_EVIDENCE_FROZEN','raw_files':len(raw),'sources':len(sources),'archive_sha256':sha(O/'BOUNDED_EVIDENCE_v2.tar.gz'),'bytes':(O/'BOUNDED_EVIDENCE_v2.tar.gz').stat().st_size,'resource':resource}))
