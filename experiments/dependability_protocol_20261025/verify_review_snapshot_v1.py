from pathlib import Path
import hashlib,json,zipfile,subprocess,sys
W=Path(__file__).resolve().parent;O=W/'review_snapshot_v1';m=json.loads((O/'MANIFEST.json').read_text())
with zipfile.ZipFile(W/'review_snapshot_v1.zip') as z:
 for r in m['files']:
  a=z.read(r['path']);assert len(a)==r['bytes'] and hashlib.sha256(a).hexdigest()==r['sha256']
  assert a==(O/r['path']).read_bytes()
 assert len(z.namelist())==len(m['files'])+1
 assert z.read('MANIFEST.json')==(O/'MANIFEST.json').read_bytes()
cmd=[sys.executable,str(O/'audit_role_probe_v2.py'),'--root',str(W/'role_formal_collected_v2'),'--stage','formal',
 '--source-manifest',str(O/'ROLE_PROBE_SOURCE_MANIFEST_v2.json'),'--output',str(W/'review_snapshot_primary_recheck_v1')]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
cmd=[sys.executable,str(O/'audit_role_costs_wal_v3.py'),'--root',str(W/'role_formal_collected_v2'),'--stage','formal',
 '--require-full-power','--output',str(W/'REVIEW_SNAPSHOT_COST_RECHECK_v1.json')]
p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,p.stderr
out=dict(status='PASS_ZIP_ALL_BYTES_AND_SNAPSHOT_CHECKER64_PRIMARY_WAL_COST',files=len(m['files'])+1,
 archive_sha256=hashlib.sha256((W/'review_snapshot_v1.zip').read_bytes()).hexdigest(),
 no_neural_calls=True,large_normal_raw_not_included=True,anonymous_web_host_not_updated=True)
(W/'REVIEW_SNAPSHOT_RECHECK_v1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
