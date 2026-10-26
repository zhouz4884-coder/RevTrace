"""Decode already-recorded P/Z/Y; CPU tokenization only, no model loading/calls."""
from pathlib import Path
import argparse,hashlib,json,re
from transformers import AutoProcessor
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--model',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
assert not a.output.exists();done=json.loads((a.root/'formal/SUMMARY.json').read_text());assert done['cells']==64
tok=AutoProcessor.from_pretrained(a.model,local_files_only=True).tokenizer;rows=[]
def has(s):return dict(substring='violet saturn alder' in s.casefold(),whole_words=bool(re.search(r'\bviolet\s+saturn\s+alder\b',s,re.I)))
for name in done['completed']:
 D=a.root/'formal'/name;plan=json.loads((D/'CASE_PLAN.json').read_text());native={}
 for path in D.glob('worker-*-receipts.jsonl'):
  for line in path.read_text().splitlines():
   x=json.loads(line)
   if x['kind']=='row-complete':
    m=x['message'];assert hashlib.sha256(m['payload_json'].encode()).hexdigest()==m['payload_digest'];r=json.loads(m['payload_json']);native[r['job_id']]=r
 calls=json.loads((D/'PHYSICAL_CALLS.json').read_text())['calls'];decoded=[]
 for c in calls:
  j=c['job'];r=c['result'];n=native[j['job_id']];proof=n.get('online_verification',{})
  origin=('coherent lowtrust injectedZ, not neural output' if c['purpose']=='candidate-at-6s' and plan['traffic']=='coherent-proposer' else
   'unchecked candidate copy, no trusted neural selection' if proof.get('unsafe_no_FP32_selection') else
   'full correct-context verified selection' if proof.get('mode')=='strict' and not proof.get('fallback_used') else 'actual native neural generation')
  decoded.append(dict(job_id=j['job_id'],purpose=c['purpose'],role=j['role'],origin=origin,
   input_P=has(tok.decode(j['prompt_tokens'],skip_special_tokens=False)),
   original_worker_Z=has(tok.decode(n['token_ids'],skip_special_tokens=True)),
   owner_Z=has(tok.decode(r['token_ids'],skip_special_tokens=True)),
   owner_P=has(tok.decode(r['state_tokens'],skip_special_tokens=False)),owner_Y=has(r['text'])))
 rows.append(dict(case=name,method=plan['method'],traffic=plan['traffic'],source_id=plan['source_id'],repeat=plan['repeat'],jobs=decoded))
out=dict(status='PASS_RECORDED_P_Z_Y_CPU_DECODE_ONLY',cases=64,runs=rows,new_neural_GPU_calls=0,
 checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='decoding actual IDs, not new-parent generation, model reexecution or a neural amplifier test')
a.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(cases=64,decoded_jobs=sum(len(r['jobs']) for r in rows),new_neural_GPU_calls=0,
 future_authority_native_Z_marker=sum(j['original_worker_Z']['substring'] for r in rows for j in r['jobs'] if j['purpose']=='future-real-authority-continuation'),
 future_private_native_Z_marker=sum(j['original_worker_Z']['substring'] for r in rows for j in r['jobs'] if j['purpose']=='future-private-at-8s-before-authority-install'))))
