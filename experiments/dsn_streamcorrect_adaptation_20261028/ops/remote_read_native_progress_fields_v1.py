import pathlib,json,hashlib
P=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f')
for rel in ['simul_whisper/simul_whisper.py','simul_whisper/generation_progress.py']:
 p=P/rel;b=p.read_bytes();lines=b.decode().splitlines();selected=set()
 for i,line in enumerate(lines):
  if ('progress' in line.lower() or 'time.' in line or 'perf_counter' in line or 'g[' in line or 'def infer' in line):
   selected.update(range(max(0,i-2),min(len(lines),i+5)))
 print(json.dumps(dict(path=rel,sha256=hashlib.sha256(b).hexdigest(),lines=[dict(line=i+1,text=lines[i]) for i in sorted(selected)]),ensure_ascii=False))
