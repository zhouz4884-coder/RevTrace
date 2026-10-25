from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
W=Path(__file__).resolve().parent;F=W/'adversarial_frozen_v1';manifest=json.loads((W/'ROLE_PROBE_SOURCE_MANIFEST_v1.json').read_text())
for r in manifest['files']:assert hashlib.sha256((F/r['path']).read_bytes()).hexdigest()==r['sha256']
xml=W/'CPU_ROLE_AND_OPERATOR_FROZEN_v5.xml';root=ET.parse(xml).getroot();s=list(root)[0] if root.tag=='testsuites' else root
assert int(s.attrib['tests'])==19 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
out=W/'ROLE_PROBE_CPU_GATE_v1.json';assert not out.exists()
out.write_text(json.dumps(dict(decision='GO_CPU_PROTOCOL_ONLY_NO_GPU_LAUNCH',harness_commit=manifest['code_commit'],
 core_runtime=manifest['core_runtime'],tests=19,test_xml_sha256=hashlib.sha256(xml.read_bytes()).hexdigest(),
 source_manifest_sha256=hashlib.sha256((W/'ROLE_PROBE_SOURCE_MANIFEST_v1.json').read_bytes()).hexdigest(),
 source_bytes_all_match=True,new_neural_GPU_calls=0,Linux_CPU_gate='PENDING_AFTER_GPU_QUEUE_RELEASE',
 earlier_fixture_failures_retained=['CPU_ROLE_AND_OPERATOR_v3.xml','CPU_ROLE_AND_OPERATOR_FROZEN_v4.xml'],
 claim='source/CPU harness only; not real neural consumption, attack success, prevalence or a canonical vulnerability'),indent=2)+'\n')
print(out.read_text())
