"""CPU-only postflight after the sequential GPU queue is completely finished."""
import hashlib,json,subprocess,sys,time,tarfile
from pathlib import Path
B=Path(sys.argv[1]);P=B/'projects/revtrace_phaseD_20261021';O=B/'results/revtrace/phaseD_20261021';N=B/'projects/revtrace_phaseN_20261021';S=P/'d1_v1'
while not (O/'FINAL_STUDIES_SUMMARY.json').exists():
 if (O/'FINAL_STUDIES_STOP.json').exists() or (O/'D_CONTROLLER_STOP.json').exists():raise RuntimeError('GPU stage failure, do not certify completeness')
 time.sleep(10)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
tasks=[['audit_downstream_v5.py',str(B)],['audit_final_studies_v3.py',str(B)],['audit_text_visibility.py',str(B)],['audit_asset_guards.py',str(B)],['audit_prior_freeze.py',str(B)],['audit_reparent_inputs.py',str(B)]]
for command in tasks:subprocess.run([sys.executable,str(P/command[0]),*command[1:]],check=True)
# Retained independent certificate/WAL/clock audit is rerun, not read as a PASS.
jobs=[]
for stage in ['R2_pilot','R2_cost','R4_scout','R4_formal']:
 jobs.append([sys.executable,str(P/'audit_phase_n_original.py'),'--sdk',str(S),'--root',str(O/stage),'--manifest',str(B/'datasets/revtrace/phaseD_20261021/manifest.json')])
for stage in ['R2_continuity','R2_strong_async','R2_transfer','R4_strict']:
 jobs.append([sys.executable,str(P/'audit_phase_n_original.py'),'--sdk',str(P/'continuity_v6'),'--root',str(O/stage),'--manifest',str(B/('datasets/revtrace/phaseD_20261021/manifest.json' if stage in ['R2_transfer','R4_strict'] else 'datasets/tc_live_20260906/manifest.json'))])
jobs.append([sys.executable,str(P/'audit_phase_n_original.py'),'--sdk',str(P/'r1_v1'),'--root',str(O/'R1_gpu'),'--manifest',str(B/'datasets/tc_live_20260906/manifest.json')])
checks=[]
for i,c in enumerate(jobs):
 with (O/('POSTFLIGHT_V6_CHECK_'+str(i)+'.log')).open('w') as f:r=subprocess.run(c,stdout=f,stderr=subprocess.STDOUT)
 checks.append({'command':c,'exit_code':r.returncode})
 if r.returncode:raise RuntimeError('Independent raw audit failed; see preserved log '+str(i))
idx=[]
for p in sorted(O.rglob('*')):
 if p.is_file() and p.name not in ['RAW_EVIDENCE_INDEX.json','POSTFLIGHT_SUMMARY.json','BOUNDED_EVIDENCE.tar.gz'] and not p.name.startswith('POSTFLIGHT_CONTROLLER'):
  with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  idx.append({'path':str(p),'bytes':p.stat().st_size,'sha256':h})
(O/'RAW_EVIDENCE_INDEX.json').write_text(json.dumps({'files':idx,'evidence_tiers':'actual GPU, artificial delivery/context intervention, CPU replay and source derivation kept distinct'},indent=2)+'\n')
# Compress large mandatory CSV tables, never drop scientific rows.
import gzip
for p in list(O.rglob('*.csv')):
 if p.stat().st_size>1_500_000:
  with gzip.open(p.with_suffix('.csv.gz'),'wb') as f:f.write(p.read_bytes())
# Bounded evidence only; do NOT copy audio, weights or large serving traces.
paths=[]
for p in sorted(O.rglob('*')):
 if not p.is_file():continue
 if p.name in ['events.jsonl','worker_records.jsonl','power_samples.json','consumer.jsonl'] or p.suffix=='.wal':continue
 if p.name.endswith('.log') or p.name=='BOUNDED_EVIDENCE.tar.gz':continue
 if p.stat().st_size>2_000_000:continue
 paths.append(p)
with tarfile.open(O/'BOUNDED_EVIDENCE.tar.gz','w:gz') as f:
 for p in paths:f.add(p,arcname=p.relative_to(O).as_posix())
state={'status':'PASS_ALL_INDEPENDENT_POSTFLIGHT_CHECKS','checks':checks,'raw_index_files':len(idx),'bounded_files':len(paths),'bounded_archive_sha256':hashlib.sha256((O/'BOUNDED_EVIDENCE.tar.gz').read_bytes()).hexdigest(),'gpu_compute_processes':subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'gpu_status':subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader'],text=True).splitlines(),'no_more_gpu_jobs':True}
(O/'POSTFLIGHT_SUMMARY.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state))
