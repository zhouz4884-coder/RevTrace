from pathlib import Path
import copy,hashlib,json,xml.etree.ElementTree as ET
W=Path(__file__).resolve().parent;read=lambda p:json.loads(p.read_text())
primary=read(W/'role_pilot_audit_v1/SUMMARY.json');assert len(primary['cases'])==8
assert all(p['pre_injection_actual_input_and_native_Z_matched'] for p in primary['pairs'])
assets=read(W/'ROLE_PILOT_ASSET_REPLAY_v1.json');assert assets['status']=='PASS8_ACTUAL_BASE_INPUT_AND_NATIVE_CORRUPT_PHI_ASSET_REPLAY' and len(assets['runs'])==8
costs=read(W/'ROLE_PILOT_WAL_COST_AUDIT_v2.json');assert len(costs['cases'])==8
assert all(c['read_only_WAL']['decision']=='PASS_READ_ONLY_WAL_REPLAY' for c in costs['cases'])
x=ET.parse(W/'CPU_ROLE_POWER_V2_v1.xml').getroot();s=list(x)[0] if x.tag=='testsuites' else x
assert int(s.attrib['tests'])==20 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
m=read(W/'ROLE_PROBE_SOURCE_MANIFEST_v2.json');assert m['code_commit']=='b08fa4262d1c3ab7e07137eea340d0bb92be200c'
for r in m['files']:assert hashlib.sha256((W/'adversarial_frozen_v2'/r['path']).read_bytes()).hexdigest()==r['sha256']
gate=copy.deepcopy(read(W/'ROLE_PROBE_UPSTREAM_N5_INDEPENDENT_GATE_v1.json'));gate['harness_commit']=m['code_commit']
gate.update(decision='GO_BOUNDED_ROLE_PILOT_ONLY',measurement_repair_only=True,
 required_same_input_repeat_cases=8,permits64formal=False,
 previous8_source_WAL_actual_input_and_consumer_checks=True,previous_energy_scope='observed support only; original files unchanged',
 verified_inputs_sha256={p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in ['role_pilot_audit_v1/SUMMARY.json','ROLE_PILOT_ASSET_REPLAY_v1.json','ROLE_PILOT_WAL_COST_AUDIT_v2.json','CPU_ROLE_POWER_V2_v1.xml']})
out=W/'ROLE_PROBE_MEASUREMENT_GATE_v2.json';assert not out.exists();out.write_text(json.dumps(gate,indent=2)+'\n')
print(json.dumps({k:v for k,v in gate.items() if k not in ['required_upstream_sha256','verified_inputs_sha256']}))
