"""Read-only dirty-worktree identity, not a research run or a backup stash."""
from pathlib import Path
import subprocess,json,hashlib,sys,time
R=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
mode=sys.argv[1];out=D/(mode+'.json');assert not out.exists()
paths=[x.decode('utf8') for x in git('diff','--name-only','-z').split(b'\0') if x]
staged=[x.decode('utf8') for x in git('diff','--cached','--name-only','-z').split(b'\0') if x]
record=dict(observed_unix=time.time(),repo=str(R),head=git('rev-parse','HEAD').decode().strip(),
    branch=git('symbolic-ref','--short','HEAD').decode().strip(),index_sha256=digest(R/'.git/index'),
    tracked_dirty=[dict(path=p,sha256=digest(R/p),bytes=(R/p).stat().st_size if (R/p).is_file() else None) for p in sorted(set(paths+staged))],
    staged_paths=staged,untracked=git('ls-files','--others','--exclude-standard','--directory').decode().splitlines())
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(path=str(out),head=record['head'],dirty_files=len(record['tracked_dirty']),staged=staged)))
