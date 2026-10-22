"""Byte-exact bounded evidence archive on8TB; all heavy raw data stays there."""
from pathlib import Path
import hashlib,json,sys,tarfile
B=Path(sys.argv[1]);O=B/'results/revtrace/row_completion_20261023';D=O/'DELIVERY_EVIDENCE_v1';assert not D.exists();D.mkdir()
assert json.loads((O/'FINAL_CLOSED_EVIDENCE_v1/SUMMARY.json').read_text())['status']=='PASS_FINAL_CLOSED_UNION_AND_TASK_RELEASE'
source=json.loads((O/'FINAL_CLOSED_EVIDENCE_v1/RAW_EVIDENCE_INDEX.json').read_text());index={r['path']:r for r in source['files']}
dirs=['formal_row_v1_independent_audit_v2','validation_row_v1_independent_audit_v2','formal_row_v1_processor_replay_v1',
 'validation_row_v1_processor_replay_v1','ROW_FORMAL_RESULTS_v1','row_timing_v1','private_blocker_audit_v1','f2_exposure_v1',
 'matrix_consistency_v1','rescue_feasibility_v1','closed_raw_index_v1','rescue_cost_gpu_v1','rescue_cost_independent_v1']
paths=[];skipped=[]
for directory in dirs:
 for p in sorted((O/directory).iterdir()):
  if p.is_file():paths.append(p.relative_to(O).as_posix())
for n in ['FORMAL_ROW_SUMMARY_v1.json','FORMAL_ROW_FREEZE_v1.json','POST_ROW_CPU_SUMMARY_v1.json','EXTRA_ROW_CPU_SUMMARY_v1.json',
 'F2_EXPOSURE_CPU_SUMMARY_v1.json','MATRIX_CONSISTENCY_CPU_SUMMARY_v1.json','RECOVERY_EVENT_SCOPE_AUDIT_v1.json']:
 paths.append(n)
for stage in ['formal_row_v1','validation_row_v1']:
 for C in sorted((O/stage).iterdir()):
  if C.is_dir() and (C/'result.json').exists():
   paths.extend((C/n).relative_to(O).as_posix() for n in ['config.json','provenance.json','sessions.json','result.json','workers.json'])
  elif C.is_file() and C.name.endswith(('.COMMAND.json','.CPU_IO.txt')):paths.append(C.relative_to(O).as_posix())
records=[];total=0
for name in sorted(set(paths)):
 p=O/name;r=index[name]
 if p.stat().st_size>16_000_000:skipped.append({'path':name,'bytes':r['bytes'],'sha256':r['sha256'],'reason':'large derived table remains on8TB'});continue
 assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
 total+=r['bytes'];assert total<100_000_000;records.append(r)
# Include the final union index itself:it is intentionally not self-indexed.
for p in sorted((O/'FINAL_CLOSED_EVIDENCE_v1').iterdir()):
 assert p.is_file();records.append({'path':p.relative_to(O).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'status':'BOUNDED_COMPLETE150_METADATA_AND_FINAL_AUDIT_ARCHIVE','files':records,'skipped':skipped,
 'raw_root':str(O),'complete_raw_index_sha256':hashlib.sha256((O/'FINAL_CLOSED_EVIDENCE_v1/RAW_EVIDENCE_INDEX.json').read_bytes()).hexdigest(),
 'no_models_audio_env_or_large_worker_event_banks':True}
(D/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=D/'formal_evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
 for r in records:tf.add(O/r['path'],arcname=r['path'],recursive=False)
 tf.add(D/'MANIFEST.json',arcname='MANIFEST.json',recursive=False)
out={'status':'PACKED_BOUNDED_FORMAL_METADATA_ARCHIVE','files':len(records)+1,'expanded_bytes':sum(r['bytes'] for r in records),
 'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'manifest_sha256':hashlib.sha256((D/'MANIFEST.json').read_bytes()).hexdigest(),'skipped':len(skipped)}
(D/'ARCHIVE.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
