set -eu
B=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9
P="$B/projects/revtrace_dependability_20261025/ck5_v6"
O="$B/results/revtrace/dependability_20261025/ck5_v6"
nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader
"$B/envs/revbatch-cu128/bin/python" - "$P" "$O" <<'PY'
import pathlib,json,sys,importlib.util
p,o=map(pathlib.Path,sys.argv[1:])
print('packages',{n:importlib.util.find_spec(n) is not None for n in ['flash_attn','qwen_asr','transformers']})
for name in ['INDEPENDENT_MANIFEST_v1.json','SOURCE_MANIFEST.json']:
 f=(p/name) if name!='SOURCE_MANIFEST.json' else p/'runtime'/name
 if f.exists():
  x=json.loads(f.read_text());print(name,{k:v for k,v in x.items() if k in ['code_commit','manifest_sha256']})
for stage in ['normal','fault','boundary']:
 done=json.loads((o/stage/'SUMMARY.json').read_text());name=done['completed'][0];d=o/stage/name/'attempt0'
 print('sample',stage,str(d))
 for filename in ['events.jsonl','worker_records.jsonl','consumer.jsonl','config.json']:
  f=d/filename
  if f.exists():
   if f.suffix=='.jsonl':
    rows=[]
    for line in f.read_text().splitlines():
     try:r=json.loads(line)
     except json.JSONDecodeError:continue
     if filename=='events.jsonl' and r.get('kind') not in ['display','canonical-display','commit','worker-return','row-complete','job-result','batch-result','dispatch']:continue
     rows.append(r)
     if len(rows)==2:break
    print(filename,json.dumps(rows)[:14000])
   else:
    x=json.loads(f.read_text());print(filename,{k:v for k,v in x.items() if k in ['proposal_barrier','fine_window_seconds','fine_seconds','authority_ratio','rho','online_selection_mode','max_new_tokens','model_adapter']})
PY
