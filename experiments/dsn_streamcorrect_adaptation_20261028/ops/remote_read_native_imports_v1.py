import pathlib,json
P=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f')
for rel in ['simul_whisper/simul_whisper.py','simul_whisper/config.py','requirements.txt']:
 p=P/rel
 if not p.exists():continue
 lines=p.read_text().splitlines()
 selected=[]
 for i,line in enumerate(lines):
  if line.startswith(('import ','from ')) or ('corrector_processor(' in line):
   selected.extend([(j+1,lines[j]) for j in range(max(0,i-1),min(len(lines),i+8))])
 print(json.dumps(dict(path=rel,lines=selected),ensure_ascii=False))
