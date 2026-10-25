from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;archive=W/'n5_postnormal_cpu_bounded_v1.tar.gz';expected='ea4fd7091dadbbf8a095c56a9689996737d00d44e7626d8dfaa51d2ee640a68e'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
O=W/'n5_postnormal_collected_v1';O.mkdir(exist_ok=False)
with tarfile.open(archive) as t:
 for m in t.getmembers():
  assert m.isfile();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
index=json.loads((O/'CPU_BOUNDED_INDEX_v1.json').read_text())
for r in index['files']:
 p=O/r['path'];assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
read=lambda p:json.loads(p.read_text())
primary=read(O/'postnormal_cpu_v1/primary/SUMMARY.json');assert primary['cells']==len(primary['episodes'])==105
for r in primary['episodes']:
 for field in ['unauthorized_admissions','stale_publications','root_incompatible_actual_views','certified_only_violations']:
  assert r[field]==0,(r['episode'],field)
 assert r['final_certified_audio_coverage']==1.0 and r['unfinished_sources']==r['rejected_sessions']==0
assert primary['metadata']['runtime_commit']=='408d75624104e7e11af3f0f2832263c632b10ed8'
wal=read(O/'postnormal_cpu_v1/NORMAL_WAL_REPLAY_v1.json');assert len(wal['checks'])==105
assert all(r['audit']['decision']=='PASS_READ_ONLY_WAL_REPLAY' for r in wal['checks'])
assets=read(O/'postnormal_cpu_v1/NORMAL_ASSET_REPLAY_v1.json');assert len(assets['runs'])==105 and assets['new_neural_GPU_calls']==0
recovery=read(O/'postnormal_cpu_v1/RECOVERY_ASSET_REPLAY_v1.json');assert len(recovery['runs'])==4 and recovery['new_neural_GPU_calls']==0
assert recovery['status']=='PASS_CPU_CRASH_TRACE_ASSET_RENDER_AND_FULL_INPUT_REPLAY'
local_recovery=read(W/'N5_RECOVERY_INDEPENDENT_AUDIT_v3.json');local_wal=read(W/'N5_RECOVERY_CANONICAL_WAL_REPLAY_v1.json')
assert len(local_recovery['episodes'])==len(local_wal['checks'])==2
for r in local_recovery['episodes']:
 assert r['acknowledged_input_loss_samples']==0 and r['original_deadlines_retained']
 for field in ['unauthorized_admissions','stale_as_fresh','root_incompatible_views','false_certified_mode_views']:assert r[field]==0
assert read(O/'postnormal_cpu_v1/SUMMARY.json')['status']=='PASS105_PRIMARY_WAL_ASSETS_AND_RECOVERY_ASSETS'
required=['postnormal_cpu_v1/SUMMARY.json','postnormal_cpu_v1/primary/SUMMARY.json',
 'postnormal_cpu_v1/NORMAL_WAL_REPLAY_v1.json','postnormal_cpu_v1/NORMAL_ASSET_REPLAY_v1.json',
 'postnormal_cpu_v1/RECOVERY_ASSET_REPLAY_v1.json','formal_normal/SUMMARY.json','formal_normal/FREEZE.json']
gate=dict(decision='GO_SAFETY_ONLY',runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8',
 scope='105normal recorded safety/actual inputs/Consumer/WAL plus2development process-recovery gates; not a CDE performance promotion',
 required_file_sha256={p:hashlib.sha256((O/p).read_bytes()).hexdigest() for p in required},
 local_independent_recovery_sha256=hashlib.sha256((W/'N5_RECOVERY_INDEPENDENT_AUDIT_v3.json').read_bytes()).hexdigest(),
 local_independent_recovery_WAL_sha256=hashlib.sha256((W/'N5_RECOVERY_CANONICAL_WAL_REPLAY_v1.json').read_bytes()).hexdigest(),
 normative_normal_runs=105,normal_actual_complete_rows=sum(r['rendered_complete_rows'] for r in assets['runs']),
 normal_full_batch_inputs_reprocessed=sum(r['exact_reprocessed_physical_batches'] for r in assets['runs']),
 recovery_actual_complete_rows_reprocessed=sum(r['rendered_actual_completed_rows'] for r in recovery['runs']),
 control_decision='all strong safe controls retained; no new metric superiority claimed')
out=W/'N5_RECOVERY_DEVELOPMENT_INDEPENDENT_GATE_v1.json';assert not out.exists();out.write_text(json.dumps(gate,indent=2)+'\n')
print(json.dumps({k:v for k,v in gate.items() if k!='required_file_sha256'}))
