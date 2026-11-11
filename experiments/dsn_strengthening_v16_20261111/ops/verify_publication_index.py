"""Verify the actual Git index blobs, not just the copied worktree bytes."""
from pathlib import Path
import hashlib,json,subprocess
E=Path(__file__).resolve().parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
prefix='experiments/'+E.name+'/'
def git(*a):return subprocess.check_output(['git','-C',str(W),*a])
manifest=W/prefix/'DELIVERY_MANIFEST.json';m=json.loads(manifest.read_bytes())
paths={p.decode()for p in git('diff','--cached','--name-only','-z').split(b'\0')if p}
expected={prefix+r['path']for r in m['files']}|{prefix+'DELIVERY_MANIFEST.json'}
assert paths<=expected and prefix+'DELIVERY_MANIFEST.json' in paths,(len(paths),len(expected))
assert not any(l.startswith(b'160000 ')for l in git('ls-files','--stage',prefix).splitlines())
for row in m['files']:
    raw=git('show',':'+prefix+row['path'])
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],row['path']
assert git('show',':'+prefix+'DELIVERY_MANIFEST.json')==manifest.read_bytes()
paper=W/'Paper_DSN/revisions/20261105_dsn2027_release_v15/main.pdf'
assert hashlib.sha256(paper.read_bytes()).hexdigest()=='b5c410b6c6fd08cec08535398910b49398dc0dc78cde497638eb537b661db750'
(E/'DELIVERY_MANIFEST.json').write_bytes(manifest.read_bytes())
print(json.dumps(dict(status='PASS_ALL_INDEX_BLOBS_MATCH_BOUNDED_MANIFEST',staged_files=len(paths),complete_snapshot_files=len(expected),bytes=m['bytes'],v15_PDF_unchanged=True,no_gitlinks=True)))
