from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;R=W/'runtime'
# Mechanical preservation of the imported file's CRLF convention.
p=R/'src/revtrace/live_qwen.py';p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
subprocess.run(['git','-c','core.whitespace=cr-at-eol','diff','--check'],cwd=R,check=True)
subprocess.run(['git','add','.gitignore','src/revtrace/live_qwen.py','src/revtrace/late_delivery.py',
    'scripts/run_tc_live_qwen.py','tests/test_post_compute_order.py'],cwd=R,check=True)
subprocess.run(['git','commit','-m','Add immutable post-compute order broker and single freshness ablation'],cwd=R,check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
files=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')
rows=[{'path':s,'bytes':(R/s).stat().st_size,'sha256':hashlib.sha256((R/s).read_bytes()).hexdigest()} for s in files if s]
manifest={'measured_baseline':'2bc71af5457de5d065ff9e771d2fad428c5c6ed9','code_commit':commit,'files':rows}
(W/'N1_SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(W/'SOURCE_N1_v1.tar.gz','w:gz') as out:
    for row in rows:out.add(R/row['path'],arcname='runtime/'+row['path'])
    out.add(W/'N1_SOURCE_MANIFEST.json',arcname='runtime/SOURCE_MANIFEST.json')
print(json.dumps({'commit':commit,'files':len(rows),'archive_sha256':hashlib.sha256((W/'SOURCE_N1_v1.tar.gz').read_bytes()).hexdigest()}))
