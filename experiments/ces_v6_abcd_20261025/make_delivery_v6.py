"""Build one bounded additive GitHub artifact only after complete local audit."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
W=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 assert not p.exists();p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def copy(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copy2(src,dest);assert sha(src)==sha(dest)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();D=a.output
 assert not D.exists();review=json.loads((W/'local_review_v2/SUMMARY.json').read_text());assert review['status']=='PASS_ALL_V6_LOCAL_EVENT_QUALITY_ENERGY_RECOMPUTATION' and review['serving_cells']==98
 assert json.loads((W/'FINAL_DECISIONS.json').read_text())['complete_requested_scope'] is True
 assert (W/'RESEARCH_REPORT.zh.md').is_file() and (W/'CONTRIBUTION_EVIDENCE.md').is_file()
 D.mkdir(parents=True)
 # Root helper/protocol/report/test files only; never recursively include CPU tmp,
 # early raw copies, Git directories, models, datasets or personal credentials.
 extensions={'.py','.sh','.md','.txt','.json','.csv','.xml','.bundle'}
 for f in W.iterdir():
  if f.is_file() and (f.suffix in extensions or f.name.startswith('SOURCE_') and f.name.endswith('.tar.gz')):copy(f,D/f.name)
 for name,manifest in [('runtime','SOURCE_MANIFEST.json'),('runtime_A','A_SOURCE_MANIFEST.json'),('runtime_D','D_SOURCE_MANIFEST.json')]:
  m=json.loads((W/manifest).read_text())
  for r in m['files']:
   f=W/name/r['path'];assert sha(f)==r['sha256'];copy(f,D/name/r['path'])
  copy(W/manifest,D/name/'SOURCE_MANIFEST.json')
 for folder in ['collection','local_review','local_review_v2','C_actionability_final','C_witness_final','D_opportunities_final','private_tail_audit','A_snapshot_benchmark_v1','A_snapshot_benchmark_v2']:
  src=W/folder;assert src.is_dir()
  for f in src.rglob('*'):
   if f.is_file():
    assert not f.is_symlink();copy(f,D/folder/f.relative_to(src))
 # Operation metadata can prove commands were scoped without publishing repeated
 # SSH output or the local credential store. Full raw commands remain in evidence.
 save(D/'OPERATIONS_INDEX.json',{'records':[{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted((W/'operations').glob('*.json'))],
  'transport':'Existing authorized known-host SSH helper; no credentials included'})
 (D/'.gitattributes').write_bytes(b'* -text\n')
 files=[]
 for f in sorted(D.rglob('*')):
  if not f.is_file():continue
  assert f.stat().st_size<40_000_000,(f,f.stat().st_size)
  data=f.read_bytes()
  # Exact credential token formats only; words in tests/docs are not secrets.
  import re
  if f.suffix in extensions or f.name=='.gitattributes':
   assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----)',data),f
  files.append({'path':f.relative_to(D).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
   'git_blob_sha1':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
 save(D/'DELIVERY_FILES.json',{'experiment_id':'REVTRACE-CES-V6-ABCD-20261025','files':files,'previous_evidence_must_be_preserved':True,'manuscript_modified':False,'max_file_bytes':40_000_000})
 print(json.dumps({'files':len(files)+1,'bytes':sum(r['bytes'] for r in files),'manifest_sha256':sha(D/'DELIVERY_FILES.json')}))
if __name__=='__main__':main()
