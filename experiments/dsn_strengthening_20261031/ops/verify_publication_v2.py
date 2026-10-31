"""Post-push independent critical-blob identity and remote-main check."""
import hashlib,json,pathlib,subprocess
R=pathlib.Path(__file__).resolve().parents[3];E=R/'experiments/dsn_strengthening_20261031'
W=pathlib.Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
commit='4411513e6273e48f814b2e5a34f3dce38a6dd299'
def git(*a):return subprocess.check_output(['git','-C',str(W),*a])
assert git('rev-parse','HEAD').decode().strip()==commit
assert git('-c','http.version=HTTP/1.1','ls-remote','origin','refs/heads/main').decode().split()[0]==commit
assert not git('status','--porcelain','--untracked-files=all').strip()
paths=['Paper_DSN/revisions/20261031_dsn2027_release_v2/main.pdf','Paper_DSN/revisions/20261031_dsn2027_release_v2/RevTrace_DSN2027_anonymous_source_v2.zip','Paper_DSN/CURRENT.md','experiments/dsn_strengthening_20261031/FINAL_RESEARCH_AND_PAPER_REPORT_20261031.zh.md','experiments/dsn_strengthening_20261031/FINAL_ROUND_AND_PAPER_GATE_v2.json']
rows=[]
for name in paths:
    actual=git('show',commit+':'+name);assert actual==(R/name).read_bytes()
    rows.append(dict(path=name,sha256=hashlib.sha256(actual).hexdigest(),bytes=len(actual)))
legacy=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip();assert legacy=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
record=dict(status='PASS_VERIFIED_REMOTE_MAIN_AND_POST_COMMIT_RELEASE_IDENTITIES',commit=commit,tree=git('rev-parse','HEAD^{tree}').decode().strip(),delivery_worktree_clean=True,legacy_HEAD_preserved=legacy,actual_default_NN_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',records=rows,source_identity_is_separate_from_archive_HEAD=True)
p=E/'PUBLICATION_VERIFIED_20261031_v2.json';assert not p.exists();p.write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record,indent=2))
