"""Independent cap/termination and sampled GPU-memory disclosure, no inference."""
from pathlib import Path
import argparse,csv,hashlib,json
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--stage',default='formal_normal')
 ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(exist_ok=False)
 done=read(a.root/a.stage/'SUMMARY.json');assert len(done['completed'])==done['cells']==done['expected']
 out=[]
 for name in done['completed']:
  E=a.root/a.stage/name;D=E/'attempt0';r=read(D/'result.json');records=lines(D/'worker_records.jsonl');events=lines(D/'events.jsonl')
  caps=[]
  for x in records:
   j=x['job'];v=x['result'];m=v['model_input_audit'];Z=v['token_ids'];stops=[i for i,t in enumerate(Z) if t in m['eos_token_ids']]
   assert stops==[len(Z)-1] or (not stops and len(Z)==m['max_new_tokens'])
   cap=not stops;assert v['hit_token_limit']==cap and v['terminated_by_eos']==bool(stops)
   if cap:caps.append(dict(job_id=j['job_id'],role=j['role'],session_id=j['session_id'],frontier=j['audio_end_sample']))
  assert len(caps)==r['token_limit_events']
  admitted={e['job_id'] for e in events if e['kind']=='commit'}
  power=read(E/'EPISODE_POWER.json');memory={}
  for gpu in [0,1]:
   xs=[v['memory_mib'] for v in power['samples'] if v['gpu']==gpu]
   memory[str(gpu)]=max(xs) if xs else None
  out.append(dict(episode=name,proposal_cap_rows=sum(x['role']=='proposal' for x in caps),authority_cap_rows=sum(x['role']=='authority' for x in caps),
   budget_truncated_authority_admissions=sum(x['role']=='authority' and x['job_id'] in admitted for x in caps),
   complete_rows=len(records),sampled_GPU0_memory_peak_MiB=memory['0'],sampled_GPU1_memory_peak_MiB=memory['1'],cap_records=caps))
 result=dict(status='PASS_FULL_RECORDED_ROW_TERMINATION_RECOUNT',episodes=out,
  limits='cap admission certifies provenance, not completeness; NVML memory peaks are sampled, not exact allocator peaks; no CPU power/total RSS measurement',
  checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_neural_GPU_calls=0)
 (a.output/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
 with (a.output/'BUDGETS.csv').open('w',newline='') as f:
  rs=[{k:v for k,v in x.items() if k!='cap_records'} for x in out];w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 print(json.dumps(dict(cells=len(out),authority_caps=sum(x['authority_cap_rows'] for x in out),admitted_caps=sum(x['budget_truncated_authority_admissions'] for x in out))))
if __name__=='__main__':main()
