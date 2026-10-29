"""Select next native execution source; never relabel completed f0 runs."""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2];I=R/'experiments/repository_identity_20261027'
S=R/'experiments/dsn_streamcorrect_adaptation_20261028'
old=I/'CURRENT.json';backup=S/'CURRENT_BEFORE_NATIVE_v6_20261029.json'
assert not backup.exists()
previous=json.loads(old.read_text());assert previous['source_commit']=='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf'
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
backup.write_bytes(old.read_bytes())
manifest=S/'packages/SOURCE_v6_LOCAL_PREFLIGHT.json'
assert json.loads(manifest.read_text())['source_commit']=='a720d02a8cb81db6545d7d9ec6bdc31419dd091d'
current=dict(previous,updated_date='2026-10-29',source_worktree=str(S/'source_v6'),
    source_commit='a720d02a8cb81db6545d7d9ec6bdc31419dd091d',source_manifest=str(manifest),
    source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
    research_state=str(S/'CURRENT_STATUS.json'),GPU_queue='NATIVE_V6_NEXT_AFTER_JOINT24_OFFLINE_IO_RELEASE',
    previous_pointer=str(backup),scope='Machine-local next-source pointer only. Prior f0 service runs retain their original source/config records; this selection is not native GPU execution or resource allocation.')
old.write_text(json.dumps(current,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:current[k] for k in ['source_commit','source_manifest_sha256','source_worktree','GPU_queue']}))
