from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent
p=Path(r'D:\StreamTxn\outputs\revtrace_dsn_sixweek_20261018\e1_collected\e1_v1\authority-clean.json');x=json.loads(p.read_text());ds=[]
for j in x['jobs']:
 if j['language']!='English' or len(j['prompt_tokens'])<=8:continue
 ds.append({'id':str(j.get('probe_case_id',j['job_id'])),'tokens':j['prompt_tokens'],'source_id':j['source_id']})
assert len(ds)>=6
(W/'DONORS.json').write_text(json.dumps({'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'selection':'all English nonempty old E1 current-parent prompts in original order; no outcome filter','donors':ds},indent=2)+'\n');print('Frozen donor contexts',len(ds))
