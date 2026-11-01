"""Read-only destination/account check using the existing Git credential route.

No credentials are printed, persisted, or passed on command lines. This does
not configure authentication and does not write to GitHub.
"""
from pathlib import Path
import json
import os
import subprocess
import urllib.request

W=Path(r'C:\Users\LENOVO\.codex\worktrees\revtrace-dsn-evidence\RevTrace')
OUT=Path(__file__).with_name('GITHUB_DESTINATION_VERIFIED_v1.json')
def git(*args):
    return subprocess.check_output(['git','-C',str(W),*args],text=True).strip()
assert git('remote','get-url','origin')=='https://github.com/zhouz4884-coder/RevTrace.git'
assert not git('status','--porcelain','--untracked-files=all')
credential=subprocess.run(['git','-C',str(W),'credential','fill'],
    input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='never'),timeout=30)
assert credential.returncode==0, 'Existing credential route unavailable'
fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
assert fields.get('password'), 'Existing route returned no credential'
def get(path):
    req=urllib.request.Request('https://api.github.com/'+path,headers={
        'Authorization':'Bearer '+fields['password'],
        'Accept':'application/vnd.github+json','User-Agent':'RevTrace-artifact-verification'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
account=get('user');repo=get('repos/zhouz4884-coder/RevTrace')
assert account['login']=='zhouz4884-coder' and repo['full_name']=='zhouz4884-coder/RevTrace'
assert repo['permissions']['push'] is True
record=dict(gate='PASS_EXISTING_ACCOUNT_AND_DESTINATION',login=account['login'],
    repository=repo['full_name'],repository_private=repo['private'],push_permission=True,
    current_local_commit=git('rev-parse','HEAD'),current_branch=git('branch','--show-current'),
    credential_route='existing Git credential.helper=manager; credential not persisted',
    source_tree_clean=True,read_only=True)
with OUT.open('x',encoding='utf8',newline='\n') as stream:json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps(record))
