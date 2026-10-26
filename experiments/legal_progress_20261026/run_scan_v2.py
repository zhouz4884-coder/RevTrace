from pathlib import Path
import json,subprocess,sys,time,hashlib,os
P=Path(__file__).resolve().parent;B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025/lp1_20261026'
s=json.loads((P/'SCAN_SOURCE_v2.json').read_text())
for f in s['files']:assert hashlib.sha256((P/f['path']).read_bytes()).hexdigest()==f['sha256']
done=[]
try:
    for study in ['ck5','n5']:
        dest=O/('scan_'+study+'_v2');assert not dest.exists()
        cmd=[sys.executable,str(P/'scan_historical_views_v2.py'),'--study',study,'--output',str(dest)]
        (O/'SCAN_V2_PROGRESS.json').write_text(json.dumps(dict(status='RUNNING_CPU',study=study,completed=done,source=s['code_commit'],command=cmd))+'\n')
        with (O/('scan_'+study+'_v2.log')).open('xb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
        if r.returncode:raise RuntimeError(study+' CPU scanner failed; GPU unaffected; inspect retained STOP/log')
        done.append(study)
    (O/'SCAN_V2_COMPLETE.json').write_text(json.dumps(dict(status='COMPLETE_BOTH_CPU_STUDIES',completed=done,source=s['code_commit'],new_GPU_calls=0))+'\n')
except BaseException as e:
    (O/'SCAN_V2_STOP.json').write_text(json.dumps(dict(error=str(e),completed=done,new_GPU_calls=0))+'\n');raise
