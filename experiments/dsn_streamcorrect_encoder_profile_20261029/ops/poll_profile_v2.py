import hashlib,json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dsn_streamcorrect_encoder_profile_20261029'
h=json.loads((O/'HANDLE_v2.json').read_text());proc=pathlib.Path('/proc')/str(h['pid']);result=dict(pid=h['pid'],exact_live=False)
if proc.exists():
 stat=(proc/'stat').read_text().rsplit(') ',1)[1].split();cmd=(proc/'cmdline').read_bytes()
 result.update(exact_live=stat[19]==h['start_ticks'] and hashlib.sha256(cmd).hexdigest()==h['command_sha256'],process_state=stat[0])
out=O/'profile_v2'
for name in ('PROGRESS.json','GATE.json','FAILURE.json'):
 p=out/name
 if p.exists():result[name]=json.loads(p.read_text())
if (out/'READY.json').exists():result['both_model_workers_ready']=True
if (out/'SUMMARY.json').exists():
 s=json.loads((out/'SUMMARY.json').read_text());result['SUMMARY']=dict(status=s['status'],decision=s['decision'],calls=s['actual_original_infer_calls'],economics=s['economics'])
if not result['exact_live'] or (out/'FAILURE.json').exists():
 p=pathlib.Path(h['log']);b=p.read_bytes();result['log_tail']=b[-7000:].decode(errors='replace')
print(json.dumps(result))
