from pathlib import Path
import hashlib,json,tarfile
W=Path(__file__).resolve().parent;archive=W/'n5_postfault_cpu_bounded_v1.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='4f98557e1a16124235d3564188cfed4137c374d9ec7922bb0040419739bb6c02'
O=W/'n5_postfault_collected_v1';O.mkdir(exist_ok=False)
with tarfile.open(archive) as t:
 for m in t.getmembers():
  assert m.isfile();(O/m.name).resolve().relative_to(O.resolve())
 t.extractall(O,filter='data')
for r in json.loads((O/'FAULT_CPU_BOUNDED_INDEX_v1.json').read_text())['files']:
 p=O/r['path'];assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
read=lambda p:json.loads(p.read_text())
assert read(O/'postfault_cpu_v2/SUMMARY.json')['status']=='PASS21_FORMAL_RECOVERY_WAL_PRIMARY_AND_ACTUAL_ASSETS'
primary=read(O/'postfault_cpu_v2/PRIMARY_v1.json');assert len(primary['episodes'])==21
for r in primary['episodes']:
 for key in ['unauthorized_admissions','stale_as_fresh','root_incompatible_views','false_certified_mode_views','acknowledged_input_loss_samples']:assert r[key]==0
 assert r['original_deadlines_retained'] and r['certified_coverage']==1.
wal=read(O/'postfault_cpu_v2/WAL_REPLAY_v1.json');assert len(wal['checks'])==21
assert all(r['audit']['restart_epochs']==1 and r['audit']['decision']=='PASS_READ_ONLY_WAL_REPLAY' for r in wal['checks'])
assets=read(O/'postfault_cpu_v2/ASSETS_v1.json');assert len(assets['runs'])==42 and assets['new_neural_GPU_calls']==0
assert assets['status']=='PASS_CPU_CRASH_TRACE_ASSET_RENDER_AND_FULL_INPUT_REPLAY'
assert len(read(O/'postfault_cpu_v2/RELEASE.json')['handles'])==84
assert read(O/'postfault_cpu_v1/STOP.json')['completed']==['WAL21'],'deployment failure must remain explicit'
paths=['postfault_cpu_v2/SUMMARY.json','postfault_cpu_v2/PRIMARY_v1.json','postfault_cpu_v2/WAL_REPLAY_v1.json',
 'postfault_cpu_v2/ASSETS_v1.json','formal_fault/SUMMARY.json','formal_fault/FREEZE.json']
gate=dict(decision='GO_BOUNDED_ROLE_PILOT_ONLY',harness_commit='f0eaae69323fbaa10b3892761a8ac2c149181013',
 runtime_commit='408d75624104e7e11af3f0f2832263c632b10ed8',formal_recovery_episodes=21,
 required_upstream_sha256={p:hashlib.sha256((O/p).read_bytes()).hexdigest() for p in paths},
 limits='process-group cold restart only; this gate permits8operator pilot cases, NOT64formal or online optimization',
 completed_rows_asset_replayed=sum(r['rendered_actual_completed_rows'] for r in assets['runs']),
 no_unknown_output_invented=True)
out=W/'ROLE_PROBE_UPSTREAM_N5_INDEPENDENT_GATE_v1.json';assert not out.exists();out.write_text(json.dumps(gate,indent=2)+'\n')
groups=read(O/'fault_aggregation_v1/SUMMARY.json')['groups']
print(json.dumps(dict(gate={k:v for k,v in gate.items() if k!='required_upstream_sha256'},
 groups=[{k:r[k] for k in ['method','repeats','whole_dual_P99_passes','kill_to_all_previous_certified_consumed_seconds_median',
 'canonical_journal_recovery_seconds_median','all_offered_audio_goodput_2_8_median','all_offered_WER_percent_median']} for r in groups]),indent=2))
