"""Download only completed C event/row metadata for local actionability audit."""
from pathlib import Path
import importlib.util,json,hashlib,os,argparse
parser=argparse.ArgumentParser();parser.add_argument('--accounting-only',action='store_true');args=parser.parse_args()
W=Path(__file__).resolve().parent;R=W/'precollection';remote='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/ces_v6_abcd_20261025'
spec=importlib.util.spec_from_file_location('approved',r'C:\Users\LENOVO\.codex\local-tools\contractkv_ssh_credential.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
c=helper.ssh_client();s=c.open_sftp();s.get_channel().settimeout(55);records=[]
try:
 summary=json.loads(s.open(remote+'/C_SUMMARY.json').read());assert summary['cells']==18 and summary['GPU_queue_closed']
 if not args.accounting_only:
  assert not (R/'C_SUMMARY.json').exists();(R/'C_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
 else:assert json.loads((R/'C_SUMMARY.json').read_text())==summary
 for name in summary['completed']:
  assert '/' not in name and '..' not in name
  folder=R/'C'/name;folder.mkdir(parents=True,exist_ok=args.accounting_only)
  for file in (['worker_batch_accounting.jsonl'] if args.accounting_only else ['worker_records.jsonl','events.jsonl','sessions.json','config.json']):
   source=remote+'/C/'+name+'/'+file;size=s.stat(source).st_size;assert size<15_000_000
   target=folder/file;assert not target.exists();partial=target.with_suffix(target.suffix+'.partial');s.get(source,str(partial));assert partial.stat().st_size==size;partial.rename(target)
   records.append({'source':source,'path':str(target.relative_to(R)),'bytes':size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 (R/('EARLY_C_ACCOUNTS.json' if args.accounting_only else 'EARLY_C_INPUTS.json')).write_text(json.dumps({'status':'DOWNLOADED_COMPLETED_C_RAW_SUBSET','files':records,'CPU_remote_model_calls':0},indent=2)+'\n')
 print(json.dumps({'files':len(records),'bytes':sum(x['bytes'] for x in records),'remote_analysis_or_model_calls':0}))
finally:c.close()
