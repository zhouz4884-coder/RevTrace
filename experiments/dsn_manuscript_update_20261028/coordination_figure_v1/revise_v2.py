import hashlib,json,subprocess
from pathlib import Path
F=Path(__file__).resolve().parent;R=F.parents[2];A=F/'source_v1';S=F/'source_v2'
S.mkdir(exist_ok=False)
for p in A.iterdir():
    if p.is_file():(S/p.name).write_bytes(p.read_bytes())
p=S/'plot.py';text=p.read_text(encoding='utf8')
changes=[
 ("['Arial','Helvetica','DejaVu Sans']","['Arial','DejaVu Sans']"),
 ("[(3.45,'#EDF3F9',BLUE),(2.72,'#EDF6F1',GREEN)]","[(3.45,'#EDF3F9',BLUE),(2.65,'#EDF6F1',GREEN)]"),
 ("ax.add_patch(FancyBboxPatch((5.28,yy),1.59,.47,","ax.add_patch(FancyBboxPatch((5.28,yy),1.59,.47 if color==BLUE else .62,"),
 ("'S: whole provisional view\\nretain if compatible',8.3,GREEN,box=(5.29,2.73,1.57,.45)","'S: whole provisional view\\nkeep compatible ahead\\nelse show Canonical',8.3,GREEN,box=(5.29,2.66,1.57,.60)"),
 ("text(6.075,3.31,'independent lanes'","text(6.075,3.34,'independent lanes'"),
 ("text(.14,1.75,'b  Coverage exit and actual physical release'","text(.14,1.83,'b  Coverage exit and actual physical release'"),
 ("    text(.17,1.54,'K',9.,BLUE,'bold',ha='left')", "    arrow([(1.895,1.45),(1.895,1.55),(4.11,1.55),(4.11,1.45)],GRAY,.9,'--')\n    text(3.03,1.66,'completion race',8.0,GRAY)\n    text(.17,1.54,'K',9.,BLUE,'bold',ha='left')")]
for old,new in changes:
    assert text.count(old)==1,old
    text=text.replace(old,new)
p.write_text(text,encoding='utf8',newline='\n')
def git(*args,cwd=S):return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()
def proof(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
git('init','-b','codex/coordination-figure-v2');git('config','core.autocrlf','false');git('add','.');git('commit','-m','Clarify whole-view fallback and completion race in coordination figure')
commit=git('rev-parse','HEAD')
write(F/'SOURCE_v2.json',dict(code_commit=commit,files=[dict(path=n,**proof(S/n)) for n in git('ls-files').splitlines()]))
git('bundle','create',str(F/'SOURCE_v2.bundle'),'--all');git('fetch',str(F/'SOURCE_v2.bundle'),'HEAD:refs/heads/codex/coordination-figure-v2',cwd=R)
config=json.loads((F/'CONFIG_v1.json').read_text(encoding='utf8'));config.update(experiment_id='REVTRACE-DSN-COORDINATION-METHOD-FIGURE-20261029-V2',plot_source_commit=commit,source_manifest_sha256=proof(F/'SOURCE_v2.json')['sha256'],output=str(F/'FIGURES_v2'))
write(F/'CONFIG_v2.json',config);write(F/'FREEZE_RECEIPT_v2.json',dict(plot_source_commit=commit,source_manifest=proof(F/'SOURCE_v2.json'),frozen_config=proof(F/'CONFIG_v2.json'),changes='whole-view fallback, completion race, remove missing-font fallback; no semantic or performance change'))
print(json.dumps(dict(plot_source_commit=commit)))
