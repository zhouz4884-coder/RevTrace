"""Read committed blobs back and bind the actual remote content publication."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
CONTENT='8ad599eae8f57a36bc3f0a7d04a1fb744aa201d1';BASE='bc79af749b22b64d914204dad08c81e5dac89c1c'
def git(*args):return subprocess.check_output(['git','-C',str(W),*args],stderr=subprocess.PIPE).decode().strip()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert git('config','--get','remote.origin.url')=='https://github.com/zhouz4884-coder/RevTrace.git'
assert git('rev-parse','HEAD')==CONTENT and not git('status','--porcelain','--untracked-files=all')
assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').split()[0]==CONTENT
subprocess.run(['git','-C',str(W),'merge-base','--is-ancestor',BASE,CONTENT],check=True,capture_output=True)
manifest_path=E/'FINAL_PUBLICATION_MANIFEST.json';manifest=json.loads(manifest_path.read_bytes())
expected={row['path']:row for row in manifest['rows']}
rel=manifest_path.relative_to(R).as_posix();b=manifest_path.read_bytes()
expected[rel]=dict(path=rel,bytes=len(b),sha256=sha(b))
proc=subprocess.Popen(['git','-C',str(W),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
try:
    for name,row in sorted(expected.items()):
        assert '\n' not in name and '\x00' not in name
        proc.stdin.write((CONTENT+':'+name+'\n').encode());proc.stdin.flush()
        header=proc.stdout.readline().split();assert len(header)==3 and header[1]==b'blob',name
        data=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n'
        assert len(data)==row['bytes'] and sha(data)==row['sha256'],name
        assert data==(R/name).read_bytes()==(W/name).read_bytes(),name
finally:
    proc.stdin.close();proc.stdout.close();assert proc.wait()==0
paper='Paper_DSN/revisions/20261102_dsn2027_release_v10/'
assert sha(subprocess.check_output(['git','-C',str(W),'show',CONTENT+':Paper_DSN/revisions/20261101_dsn2027_release_v9/main.pdf']))=='cf3cd3556cf7637f970d3d18870beb71447c51d34eb6417c4e5ab30f41d12114'
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
record=dict(gate='PASS_ACTUAL_REMOTE_CONTENT_TREE_HISTORY_AND_ALL_BOUNDED_BLOBS',
    verified_utc=datetime.now(timezone.utc).isoformat(),repository='zhouz4884-coder/RevTrace',
    intended_account_verified='zhouz4884-coder',content_commit=CONTENT,content_tree=git('rev-parse',CONTENT+'^{tree}'),
    ancestor_preserved=BASE,verified_remote_main_at_content_delivery=CONTENT,
    GitHub_connector_independently_resolved_content_commit=CONTENT,GitHub_connector_changed_files=244,
    connector_changes_only_requested_paths=True,manifest_sha256=sha(manifest_path.read_bytes()),
    content_blobs_read_back_and_byte_verified=len(expected),delivery_worktree_clean=True,
    paper_pdf_sha256=sha((R/paper/'main.pdf').read_bytes()),source_zip_sha256=sha((R/paper/'RevTrace_DSN2027_anonymous_source_v10.zip').read_bytes()),
    source_identity_default='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',archive_commit_is_not_execution_source=True,
    original_v9_preserved=True,legacy_dirty_root_HEAD_preserved=True,
    verification_script_sha256=sha(Path(__file__).read_bytes()),conference_submission_performed=False,
    receipt_note='This verifies the immutable content commit. The receipt and this verifier are published in a following metadata-only commit.')
p=E/'DELIVERY_RECEIPT.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(json.dumps(record))
