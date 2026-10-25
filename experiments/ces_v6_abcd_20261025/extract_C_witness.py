"""Exact source/window clock witness. No model output is recomputed."""
from pathlib import Path
import argparse,csv,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();O=a.root;A=a.output;A.mkdir()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
def digest(v):return hashlib.sha256(json.dumps(v,separators=(',',':')).encode()).hexdigest()
rows=[]
for name in sorted(read(O/'C_SUMMARY.json')['completed']):
 C=O/'C'/name;cfg=read(C/'config.json');rs=lines(C/'worker_records.jsonl');es=lines(C/'events.jsonl');t0=next(e['t0_perf'] for e in es if e['kind']=='run-start')
 def get(role,window):
  xs=[r for r in rs if r['job']['source_id']=='1993-147149-0020' and r['job']['role']==role and r['job']['end_window']==window];assert len(xs)==1;return xs[0]
 a5,p5,p6=get('authority',5),get('proposal',5),get('proposal',6);j,r=p6['job'],p6['result'];commit=next(e for e in es if e['kind']=='commit' and e['job_id']==a5['job']['job_id'])
 accounts=[e for e in es if e['kind']=='worker-status' and e.get('status')=='batch-accounting']
 oldbatch=next(e for e in accounts if p5['job']['job_id'] in e['job_ids'])
 newbatch=next(e for e in accounts if j['job_id'] in e['job_ids'])
 rows.append({'cell':name,'traffic':cfg['ces_study']['traffic'],'hold':cfg['ces_study']['v6']['authority_hold_seconds'],'repeat':int(name.rsplit('-r',1)[1]),
  'source':j['source_id'],'auth5_enqueued':a5['job']['enqueue_perf']-t0,'auth5_received':a5['result']['received_perf']-t0,'auth5_installed':commit['installed'],
  'private5_received':p5['result']['received_perf']-t0,'private5_batch_drained':oldbatch['batch_drained_perf']-t0,'private5_tokens':len(p5['result']['token_ids']),'private5_cap':p5['result']['hit_token_limit'],
  'private6_enqueued':j['enqueue_perf']-t0,'private6_parent':j['parent'],'private6_prompt_digest':digest(j['prompt_tokens']),'private6_effective_prompt_digest':digest(r['execution_context_audit']['executed_prompt_tokens']),
  'private6_audio_sha':j['prefix_audio_sha256'],'private6_tokens':len(r['token_ids']),'private6_cap':r['hit_token_limit'],'private6_EOS':r['terminated_by_eos'],
  'private6_batch_lease_s':newbatch['batch_result_complete_perf']-newbatch['worker_started_perf'],'auth5_install_before_private6_issue':t0+commit['installed']<=j['enqueue_perf']})
with (A/'C_CRITICAL_SOURCE_CLOCKS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
report={'status':'COMPLETE_RAW_C_SOURCE_CLOCK_WITNESS','rows':rows,'same_source_repeats_are_one_diagnostic_context':True,'physical_batch_lease_not_row_exclusive_cost':True,'new_GPU_calls':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(A/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'rows':len(rows),'mixed_nohold_or15':[{k:r[k] for k in ['repeat','hold','auth5_received','auth5_installed','private5_received','private6_enqueued','private6_parent','private6_tokens','private6_cap','private6_batch_lease_s']} for r in rows if r['traffic']=='mixed' and r['hold'] in [0.,1.5]]}))
