from pathlib import Path
import hashlib,json
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
P=B/'projects/revtrace_physical_retirement_20261028'
plan=json.loads((P/'DSN_JOINT_PLAN_v1_FROZEN.json').read_text())
rows=[]
for cell in plan['cells']:
 frozen=json.loads((Path(cell['output'])/'FREEZE.json').read_text())['frozen_config']
 rows.append(dict(cell_id=cell['cell_id'],planned_manifest_sha256=cell['manifest_sha256'],actual_frozen_original_manifest_sha256=frozen.get('original_manifest_sha256'),planned_fixture_sha256=cell['fixture_sha256'],actual_frozen_fixture_sha256=frozen.get('fixture_sha256'),all_frozen_config_keys=sorted(frozen),actual_manifest_path=cell['manifest'],actual_manifest_file_sha256=hashlib.sha256(Path(cell['manifest']).read_bytes()).hexdigest(),actual_fixture_path=cell['fixture'],actual_fixture_file_sha256=hashlib.sha256(Path(cell['fixture']).read_bytes()).hexdigest()))
print(json.dumps(rows))
