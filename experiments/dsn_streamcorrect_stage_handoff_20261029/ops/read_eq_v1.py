import pathlib,json,hashlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_stage_handoff_20261029';h=json.loads((O/'EQ_HANDLE_v1.json').read_text());proc=pathlib.Path('/proc')/str(h['pid']);alive=proc.exists() and int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])==h['start_ticks'] and hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()==h['cmdline_sha256'];r=dict(exact_controller_alive=alive,pid=h['pid'],out=h['out'],ready=(O/'equivalence_v1/READY.json').exists(),files={})
for name in ('PROGRESS.json','GATE.json','SUMMARY.json','failure.txt'):
 p=O/'equivalence_v1'/name
 if p.exists():r['files'][name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),value=json.loads(p.read_text()) if p.suffix=='.json' else p.read_text()[-8000:])
log=O/'equivalence_v1.log'
if log.exists():
 with log.open('rb') as f:f.seek(max(0,log.stat().st_size-5000));r['log_tail']=f.read().decode('utf-8',errors='replace')
print(json.dumps(r,ensure_ascii=False,indent=2))
