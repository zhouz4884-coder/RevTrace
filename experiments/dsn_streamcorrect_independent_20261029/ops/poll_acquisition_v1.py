import hashlib,json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_independent_20261029';h=json.loads((O/'HANDLE_v1.json').read_text());p=pathlib.Path('/proc')/str(h['pid']);r=dict(pid=h['pid'],exact_live=False)
if p.exists():
 st=(p/'stat').read_text().rsplit(') ',1)[1].split();cmd=(p/'cmdline').read_bytes();r['exact_live']=st[19]==h['start_ticks'] and hashlib.sha256(cmd).hexdigest()==h['command_sha256']
for name in ('GATE.json','FAILURE.json','SUMMARY.json'):
 f=O/'acquisition_v1'/name
 if f.exists():r[name]=json.loads(f.read_text())
if (O/'acquisition_v1/PROGRESS.json').exists():r['completed_sources']=json.loads((O/'acquisition_v1/PROGRESS.json').read_text())['completed_sources']
print(json.dumps(r))
