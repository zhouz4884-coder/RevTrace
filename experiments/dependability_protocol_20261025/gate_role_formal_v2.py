from pathlib import Path
import json,hashlib
W=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
files=['role_pilot_primary_v2/SUMMARY.json','ROLE_PILOT_WAL_COST_AUDIT_v3.json','ROLE_PILOT_ASSET_REPLAY_v2.json','ROLE_MEASUREMENT_REPAIR_SAME_INPUT_v1.json','ROLE_PROBE_SOURCE_MANIFEST_v2.json','role_pilot_collected_v2/PILOT_RELEASE.json','role_pilot_collected_v2/LINUX_CPU_GATE.json']
a=read(W/files[0]);assert a['case_count']==8 and a['status'].startswith('PASS')
assert all(p['pre_injection_actual_input_and_native_Z_matched'] for p in a['pairs'])
assert all(r['actual_private_chain_consumer_violations']==0 for r in a['cases'])
assert all(r['selected_6s_matches_actual_FP32_reference'] for r in a['cases'] if r['method']!='renderer_only')
b=read(W/files[1]);assert len(b['cases'])==8 and b['status'].startswith('PASS')
assert all(r['full_operator_window_energy_measured'] for r in b['cases'])
c=read(W/files[2]);assert c['status']=='PASS_ACTUAL_BASE_INPUT_AND_NATIVE_CORRUPT_PHI_ASSET_REPLAY' and c['cases']==8
assert read(W/files[3])['status']=='PASS'
assert read(W/files[4])['code_commit']=='b08fa4262d1c3ab7e07137eea340d0bb92be200c'
assert len(read(W/files[5])['owned'])==16
assert read(W/files[6])['tests']==20
out=W/'ROLE_FORMAL_INDEPENDENT_GATE_v2.json';assert not out.exists()
out.write_text(json.dumps(dict(decision='GO_BOUNDED_ROLE_PROBE',harness_commit='b08fa4262d1c3ab7e07137eea340d0bb92be200c',
 required_local_sha256={f:hashlib.sha256((W/f).read_bytes()).hexdigest() for f in files},
 required_remote_sha256={'pilot/SUMMARY.json':hashlib.sha256((W/'role_pilot_collected_v2/pilot/SUMMARY.json').read_bytes()).hexdigest(),
  'pilot/FREEZE.json':hashlib.sha256((W/'role_pilot_collected_v2/pilot/FREEZE.json').read_bytes()).hexdigest(),
  'PILOT_ASSET_REPLAY_v2.json':hashlib.sha256((W/files[2]).read_bytes()).hexdigest(),
  'PILOT_RELEASE.json':hashlib.sha256((W/files[5]).read_bytes()).hexdigest()},
 permits64formal=True,scope='fixed4sources x4actualmethods x2conditions x2freshrepeats; prepared-input operator, not online serving; no natural prevalence or independent metadata GPU case',
 measurement_repeat_native_inputs_and_Z_P_Y_Stop_equal=True,full_power_support=True,
 CPU_reprocessed_actual_base_batches=sum(r['actual_base_input_batches_reprocessed'] for r in c['runs'])),indent=2)+'\n')
print(out.read_text())
