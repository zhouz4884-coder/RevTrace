"""Read-only small native terminal summaries; no experiments or model imports."""
from pathlib import Path
import json, hashlib, subprocess
O=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_20261028')
for q in [O/'native_campaign_v8_continuation_auditfix_v1/GATE.json',O/'native_postanalyses_v8/SUMMARY.json',O/'native_postanalyses_v8/primary_quantiles/SUMMARY.json',O/'native_postanalyses_v8/feedback_characterization/SUMMARY.json',O/'ready_opportunity_v1/SUMMARY.json']:
    if not q.exists():
        print(json.dumps(dict(path=str(q),exists=False)));continue
    b=q.read_bytes();v=json.loads(b)
    def compact(x):
        if isinstance(x,dict):
            return {k:(len(z) if isinstance(z,list) and k in ('pairs','records','events','calls','updates','same_input_pairs','sources','cases','matched_pairs') else compact(z)) for k,z in x.items()}
        if isinstance(x,list):return [compact(z) for z in x]
        return x
    keep=compact(v)
    print(json.dumps(dict(path=str(q),sha256=hashlib.sha256(b).hexdigest(),data=keep),ensure_ascii=False))
print(json.dumps(dict(GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip())))
