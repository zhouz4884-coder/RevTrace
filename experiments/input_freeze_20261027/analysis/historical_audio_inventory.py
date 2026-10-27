"""Bounded retained-archive inventory, never calls a model or changes source."""
from pathlib import Path
import hashlib,json,re,subprocess
S=Path(r'D:\VLA_QWEN\RevTrace\.execution\archive_main')
O=Path(__file__).parent
files=subprocess.check_output(['git','-C',str(S),'ls-files','-z'],text=True).split('\0')
pattern=re.compile(r'(?<!\d)(\d{2,6})-(\d{2,8})-(\d{4})(?!\d)')
sources={};checked=[];excluded=[]
for name in files:
    if not name or Path(name).suffix.lower() not in {'.json','.jsonl','.csv','.md','.py','.txt','.yaml','.yml'}:continue
    p=S/name
    if not p.is_file():excluded.append({'path':name,'reason':'absent'});continue
    if p.stat().st_size>16000000:excluded.append({'path':name,'bytes':p.stat().st_size,'reason':'size-bound'});continue
    b=p.read_bytes();txt=b.decode('utf8',errors='replace')
    ids=sorted({'-'.join(x) for x in pattern.findall(txt)})
    if ids:
        checked.append({'path':name,'sha256':hashlib.sha256(b).hexdigest(),'source_ids':ids})
        for sid in ids:sources.setdefault(sid,[]).append(name)
result={'archive_commit':subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip(),'scan':'all bounded tracked text in retained current evidence archive; regex identifiers, not asserted exhaustive unavailable raw history','source_ids':sorted(sources),'speaker_ids':sorted({s.split('-')[0] for s in sources}),'matched_files':checked,'excluded':excluded,'metadata_before_model_selection':True}
dest=O/'HISTORICAL_AUDIO_INVENTORY.json'
assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'sources':len(sources),'speakers':len(result['speaker_ids']),'matched_files':len(checked),'excluded':len(excluded),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))
