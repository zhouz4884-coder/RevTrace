"""Root source-identity gate for the separately frozen local recount."""
import hashlib,json,subprocess,sys
from pathlib import Path
I=Path(__file__).resolve().parents[1];R=I.parents[1]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=I/'packages/ANALYSIS_SOURCE_v2.json';source=I/'analysis_source_v2'
assert sha(manifest)=='5333a4669a28066e7d10268bfe255420af8d1a1c85cd619cb5d3270aaf305f70'
assert read(manifest)['source_commit']=='b473d9dc47c21d5cc7f88d7871f37497398895fb'
assert sha(I/'SERVICE_RESULTS_v1/COLLECTION_MANIFEST.json')=='598a30d07422d12f328990a4acd926bda8f91e78a6f3ab5c46c10fc547d15607'
pointer=R/'experiments/repository_identity_20261027/CURRENT.json';backup=I/'CURRENT_BEFORE_FINAL_ANALYSIS_v2.json'
assert not backup.exists();backup.write_bytes(pointer.read_bytes());x=read(pointer)
x.update(source_worktree=str(source),source_manifest=str(manifest),source_manifest_sha256=sha(manifest),source_commit=read(manifest)['source_commit'],research_state=str(I/'FINAL_ANALYSIS_STATUS.json'),GPU_queue='LOCAL_CPU_ONLY_FINAL16_INDEPENDENT_RECOUNTS_NO_NEURAL',scope='Actual local analysis source only; neural executions retain bdfa and separate raw source manifests.',previous_pointer=str(backup))
pointer.write_text(json.dumps(x,indent=2)+'\n',encoding='utf8')
r=subprocess.run([sys.executable,'-B',str(R/'experiments/repository_identity_20261027/preflight.py')],capture_output=True,check=True)
identity=json.loads(r.stdout);assert identity['gate']=='SOURCE_IDENTITY_PASS' and identity['code_commit']==read(manifest)['source_commit']
(I/'FINAL_ANALYSIS_ROOT_NOARG_PREFLIGHT_v2.json').write_bytes(r.stdout)
print(json.dumps(identity))
