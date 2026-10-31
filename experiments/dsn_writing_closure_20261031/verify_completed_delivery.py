"""Verify the actual published commit and critical artifacts without rewriting it."""
from pathlib import Path
import argparse,hashlib,json,subprocess

R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--out',required=True)
p.add_argument('--ancestor',required=True);a=p.parse_args()
def git(*args):return subprocess.check_output(['git','-C',str(W),*args]).decode().strip()
def sha(b):return hashlib.sha256(b).hexdigest()
receipt=json.loads((R/'experiments/dsn_manuscript_update_20261028'/('PUBLICATION_'+a.stage+'.json')).read_bytes())
head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
assert head==receipt['commit'] and tree==receipt['tree']
assert not git('status','--porcelain','--untracked-files=all')
remote=git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]
assert remote==head
subprocess.run(['git','-C',str(W),'merge-base','--is-ancestor',a.ancestor,head],check=True,capture_output=True)
base='Paper_DSN/revisions/20261031_dsn2027_release_v4/'
critical=[base+'main.pdf',base+'main.tex',base+'PACKAGING_PROVENANCE.json',
    base+'RevTrace_DSN2027_anonymous_source_v4.zip','Paper_DSN/CURRENT.md','experiments/LATEST_RESEARCH.json',
    'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261031_v4.json',
    'experiments/dsn_writing_closure_20261031/FINAL_WRITING_AND_RESEARCH_REPORT.zh.md',
    'experiments/dsn_writing_closure_20261031/FINAL_CLOSURE_GATE_v1.json',
    'experiments/dsn_writing_closure_20261031/CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json',
    'experiments/dsn_writing_closure_20261031/CONTENT_CPU_V4_RESULTS/complete20/GATE.json',
    'experiments/dsn_writing_closure_20261031/ANONYMOUS_COLD_BUILD_REVIEW_v4.json',
    'Paper_DSN/revisions/20261031_dsn2027_release_v2/main.pdf']
rows=[]
for rel in critical:
    expected=(R/rel).read_bytes()
    actual=subprocess.check_output(['git','-C',str(W),'show',head+':'+rel])
    assert actual==expected and (W/rel).read_bytes()==expected, rel
    rows.append(dict(path=rel,bytes=len(actual),sha256=sha(actual),committed_blob_matches=True))
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
record=dict(gate='PASS_ACTUAL_REMOTE_MAIN_COMMIT_TREE_HISTORY_AND_CRITICAL_BYTES',
    stage=a.stage,remote_main=head,tree=tree,ancestor_preserved=a.ancestor,
    delivery_worktree_clean=True,legacy_dirty_head_preserved=True,critical_artifacts=rows,
    publisher_checked_all_staged_source_blobs_before_commit=True,
    publisher_bounded_snapshot_files=receipt['files'],publisher_bounded_snapshot_bytes=receipt['bytes'],
    scope='The remote ref resolves to this exact local commit/tree. Critical committed blobs were read back byte-for-byte; full snapshot blob identity gate ran before commit.',
    venue_submission_performed=False)
out=E/a.out;assert out.parent==E and not out.exists()
with out.open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in record.items() if k!='critical_artifacts'}))
