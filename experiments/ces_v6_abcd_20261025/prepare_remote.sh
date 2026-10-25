set -euo pipefail
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
"$B/envs/revbatch-cu128/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,time
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');P=B/'projects/revtrace_ces_v6_abcd_20261025';O=B/'results/revtrace/ces_v6_abcd_20261025'
assert not P.exists() and not O.exists(),'Read existing state before resuming; do not create duplicate study'
P.mkdir();O.mkdir()
old=B/'results/revtrace/ces_v5_closed_loop_20261025'
case_candidates=[];mismatches=[];seen=set()
for cell in sorted((old/'formal').iterdir()):
 if not (cell/'worker_records.jsonl').is_file():continue
 cfg=json.loads((cell/'config.json').read_text());batches={}
 for line in (cell/'worker_records.jsonl').read_text().splitlines():
  row=json.loads(line);j,r=row['job'],row['result']
  if j['role']!='authority' or j['ces_operation']!='verify':continue
  proof=r['online_verification'];c=j['candidate_token_ids'];p=proof['predicted_token_ids'];first=next((i for i,(a,b) in enumerate(zip(c,p)) if a!=b),None)
  if proof['fallback_used']:mismatches.append({'cell':cell.name,'job_id':j['job_id'],'first_mismatch':first,'candidate_length':len(c),'fallback_length':len(r['token_ids']),'matching_prefix_in_fresh_fallback':next((i for i,(a,b) in enumerate(zip(c,r['token_ids'])) if a!=b),min(len(c),len(r['token_ids'])))})
  batches.setdefault(r['physical_batch_id'],[]).append(row)
 for bid,rs in batches.items():
  failed=[i for i,x in enumerate(rs) if x['result']['online_verification']['fallback_used']]
  if not 0<len(failed)<len(rs):continue
  signature=hashlib.sha256(json.dumps([{k:x['job'].get(k) for k in ['source_id','prompt_tokens','chunk_id','audio_end_sample','candidate_token_ids']} for x in rs],sort_keys=True).encode()).hexdigest()
  if signature in seen:continue
  seen.add(signature);valid=max(sum(rs[i]['result']['model_input_audit']['attention_mask']) for i in failed)
  width=rs[0]['result']['model_input_audit']['prompt_width'];gap=width-valid
  case_candidates.append({'source_cell':cell.name,'batch_id':bid,'jobs':[x['job'] for x in rs],
   'old_input_audits':[x['result']['model_input_audit'] for x in rs],'old_Z':[x['result']['token_ids'] for x in rs],
   'cfg':cfg,'failed_indices':failed,'prompt_padding_gap':gap,'signature':signature})
case_candidates.sort(key=lambda x:(-x['prompt_padding_gap'],x['source_cell'],x['batch_id']))
selected=[]
for x in case_candidates:
 if len(selected)<6:selected.append(x)
(O/'B_CASES.json').write_text(json.dumps({'selection':'largest observed failed-subset prompt padding gaps; diagnostic operator cases, not serving or held-out','cases':selected},indent=2)+'\n')
(O/'B_FIRST_MISMATCHES.json').write_text(json.dumps({'rows':mismatches,'unique_input_batches':len(case_candidates),'selected_cases':len(selected),'new_GPU_calls':0},indent=2)+'\n')
inventory={}
for n in ['datasets/revtrace','datasets/tc_live_20260906','datasets/sources']:
 d=B/n
 if d.exists():inventory[n]=[str(p.relative_to(d)) for p in sorted(d.glob('*'))][:35]
print(json.dumps({'project':str(P),'output':str(O),'B_cases':len(selected),'fallback_rows':len(mismatches),'dataset_inventory':inventory}))
PY
