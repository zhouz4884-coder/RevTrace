"""Activate a frozen owned source; save the prior machine-local pointer."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
E=Path(__file__).resolve().parents[1];R=E.parents[1]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
p.add_argument('--manifest',type=Path,required=True);p.add_argument('--tag',required=True)
p.add_argument('--run-record',type=Path);a=p.parse_args()
assert a.tag.replace('_','').isalnum()
source=a.source.resolve(strict=True);m=a.manifest.resolve(strict=True)
assert source.is_relative_to(E.resolve()) and m.is_relative_to(E.resolve())
manifest=json.loads(m.read_bytes());identity=R/'experiments/repository_identity_20261027'
before=E/('CURRENT_BEFORE_'+a.tag+'.json');gate=E/('ROOT_NOARG_'+a.tag+'.json')
assert not before.exists() and not gate.exists()
old=(identity/'CURRENT.json').read_bytes();before.write_bytes(old)
pointer=json.loads(old);pointer.update(source_worktree=str(source),source_commit=manifest['code_commit'],
    source_manifest=str(m),source_manifest_sha256=hashlib.sha256(m.read_bytes()).hexdigest(),
    updated_date='2026-11-02',research_state=str(E/'README.zh.md'),
    scope='New frozen analysis/cost source; does not relabel any historical experiment.',
    previous_pointer=str(before),GPU_queue='SEE_DSN_NATIVE_CONFIRMATION_20261102_ACTIVE_STATE')
(identity/'CURRENT.json').write_bytes((json.dumps(pointer,indent=2)+'\n').encode())
cmd=[sys.executable,'-B',str(identity/'preflight.py'),'--output',str(gate)]
if a.run_record:cmd+=['--run-record',str(a.run_record.resolve(strict=True))]
result=subprocess.run(cmd,cwd=R,capture_output=True)
if result.returncode:
    (identity/'CURRENT.json').write_bytes(old)
    raise RuntimeError(result.stdout.decode(errors='replace')+result.stderr.decode(errors='replace'))
print(result.stdout.decode(),end='')
