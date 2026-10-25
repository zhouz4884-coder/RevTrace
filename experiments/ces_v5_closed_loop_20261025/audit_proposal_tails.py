"""Observed Proposer row/batch tails, never counterfactual GPU performance."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();O=a.root;D=O/'formal_proposal_tails_v1'
assert not D.exists()
read=lambda p:json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def csvsave(p,rows):
 with p.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=read(O/'formal_SUMMARY.json');audit=read(O/'formal_audit/SUMMARY.json')
assert summary['performance_cells']==72 and audit['cells']==72 and not audit['failures']
D.mkdir();rs=[];bs=[];cells=[];inputs=[]
for name in summary['completed_performance']:
 C=O/'formal'/name;cfg=read(C/'config.json');result=read(C/'result.json')
 with (C/'worker_batch_accounting.jsonl').open() as f:batches={b['batch_id']:b for b in map(json.loads,f)}
 bybatch=defaultdict(list);selected=[]
 with (C/'worker_records.jsonl').open() as f:
  for line in f:
   rec=json.loads(line);j,r=rec['job'],rec['result']
   if j['role']!='proposal':continue
   bid=r['physical_batch_id'];batch=batches[bid];bybatch[bid].append(rec)
   shape=r['model_input_audit']
   row={'cell':name,'method':cfg['ces_study'].get('label',cfg['ces_study']['method']),
     'arrival':name.split('-')[1],'repeat':int(name.rsplit('-r',1)[1]),'job_id':j['job_id'],'session_id':j['session_id'],
     'source_id':j['source_id'],'window':j['end_window'],'parent':j['parent'],'batch_id':bid,
     'audio_end_sample':j['audio_end_sample'],'actual_output_tokens':len(r['token_ids']),
     'hit_token_limit':bool(r['hit_token_limit']),'terminated_by_eos':bool(r['terminated_by_eos']),
     'direct_F2_execution':bool(r.get('execution_context_audit',{}).get('fault_override',False)),
     'declared_input_identity':digest({k:j.get(k) for k in ['source_id','prompt_tokens','chunk_id','audio_start_sample','audio_end_sample','prefix_audio_sha256','interval_audio_sha256','runtime_digest']}),
     'actual_input_audit_digest':digest(shape),'Z_digest':digest(r['token_ids']),'P_digest':digest(r['state_tokens']),
     'worker_start_to_row_render_s':r['completed_perf']-r['started_perf'],
     'physical_batch_rows':len(batch['job_ids']),'physical_batch_lease_s':batch['batch_drained_perf']-batch['worker_started_perf']}
   rs.append(row);selected.append(row)
 for bid,recs in bybatch.items():
  b=batches[bid];bs.append({'cell':name,'method':selected[0]['method'],'arrival':name.split('-')[1],
     'batch_id':bid,'rows':len(recs),'capped_rows':sum(x['result']['hit_token_limit'] for x in recs),
     'max_generated_tokens':max(len(x['result']['token_ids']) for x in recs),
     'lease_s':b['batch_drained_perf']-b['worker_started_perf'],
     'model_phase_wall_s':sum(x['completed_perf']-x['started_perf'] for x in b['phases']),
     'kernel_active_time_not_measured':True})
 bb=[b for b in bs if b['cell']==name]
 cells.append({'cell':name,'method':selected[0]['method'],'arrival':name.split('-')[1],
    'proposal_rows':len(selected),'proposal_caps':sum(x['hit_token_limit'] for x in selected),
    'proposal_batches':len(bb),'total_lease_s':sum(x['lease_s'] for x in bb),
    'cap_associated_batch_count':sum(x['capped_rows']>0 for x in bb),
    'cap_associated_batch_lease_s':sum(x['lease_s'] for x in bb if x['capped_rows']),
    'max_batch_lease_s':max(x['lease_s'] for x in bb),
    'runtime_report_total_token_limit_events':result['token_limit_events'],
    'associated_batch_cost_not_exclusive_cap_cost':True})
 inputs.append({'cell':name,'worker_records_sha256':sha(C/'worker_records.jsonl'),'batch_accounting_sha256':sha(C/'worker_batch_accounting.jsonl')})
csvsave(D/'PROPOSAL_ROWS.csv',rs);csvsave(D/'PROPOSAL_BATCHES.csv',bs);csvsave(D/'CELLS.csv',cells)
# Cross-policy matches are observational, not repeated execution of one chosen batch.
same=defaultdict(list)
for r in rs:same[r['declared_input_identity']].append(r)
mixed=[]
for key,v in same.items():
 if any(x['hit_token_limit'] for x in v) and any(not x['hit_token_limit'] for x in v):
  for r in v:mixed.append(dict(r,match_scope='same declared logical model input across observed histories; physical realized layout/context may differ; no causal effect claim'))
if mixed:csvsave(D/'CAP_DISCORDANT_DECLARED_INPUT_MATCHES.csv',mixed)
report={'status':'PASS_OBSERVED_PROPOSER_TAIL_ACCOUNTING','cells':72,'proposal_rows':len(rs),'physical_proposal_batches':len(bs),
 'proposal_capped_rows':sum(r['hit_token_limit'] for r in rs),'cap_discordant_logical_input_classes':len({r['declared_input_identity'] for r in mixed}),
 'new_GPU_calls':0,'scope':'Observed paid Proposer tails; association is not exclusive cost or a matched alternative GPU execution',
 'script_sha256':sha(Path(__file__)),'inputs':inputs}
(D/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='inputs'}))
