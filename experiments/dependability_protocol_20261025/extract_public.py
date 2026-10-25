"""Bounded read-only extraction of published protocol sources and summaries."""
from pathlib import Path
import hashlib,json,subprocess
W=Path(__file__).resolve().parent;repo=W.parent/'online_admission_20261022/git_delivery_stage_v1';index=json.loads((W/'PUBLIC_TREE_INDEX.json').read_text());ref=index['commit'];out=W/'source_archive';assert not out.exists();out.mkdir();copied=[]
for r in index['files']:
 name=r['path'];p=Path(name);base=p.name.lower()
 reports=p.suffix.lower()=='.md'
 runtime=('/runtime/' in name or '/source/' in name) and p.suffix.lower() in {'.py','.toml','.ini','.json','.txt','.md'}
 summary=p.suffix.lower() in {'.json','.csv'} and any(x in base for x in ['summary','audit','evidence','manifest','freeze','groups','claim','decision','state']) and r['bytes']<2_000_000
 if not (reports or runtime or summary) or r['bytes']>2_000_000:continue
 data=subprocess.check_output(['git','-C',str(repo),'show',ref+':'+name]);assert len(data)==r['bytes']
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==r['git_blob']
 target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 copied.append({**r,'sha256':hashlib.sha256(data).hexdigest()})
(W/'PUBLIC_EXTRACT_MANIFEST.json').write_text(json.dumps({'commit':ref,'files':copied,'not_a_new_experiment':True},indent=2)+'\n')
prefixes={}
for r in copied:prefixes[r['path'].split('/')[1]]=prefixes.get(r['path'].split('/')[1],0)+1
print(json.dumps({'files':len(copied),'bytes':sum(r['bytes'] for r in copied),'by_campaign':prefixes}))
