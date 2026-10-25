from pathlib import Path
import hashlib,json,platform,subprocess,sys
W=Path(__file__).resolve().parent;R=W/'degradation'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
files=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0');rows=[]
for name in files:
 if not name:continue
 raw=(R/name).read_bytes();blob=subprocess.check_output(['git','cat-file','blob','HEAD:'+name],cwd=R)
 assert raw==blob,name
 rows.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
(W/'CDE_CPU_SOURCE_IDENTITY_v1.json').write_text(json.dumps({'status':'PASS_CPU_PROTOTYPE_BYTE_SNAPSHOT',
 'code_snapshot_commit':commit,'snapshot_timing':'post-test byte snapshot of the unchanged tested code, not an earlier GPU execution commit',
 'files':rows,'python':sys.version,'platform':platform.platform(),'CPU_tests':25,'new_GPU_calls':0,
 'live_integration_complete':False,'recovery_reservation_and_rejection_semantics_pending':True},indent=2)+'\n')
print(json.dumps({'commit':commit,'files':len(rows),'CPU_tests':25,'live_integration_complete':False}))
