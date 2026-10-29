import pathlib,json
P=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f')
for rel,start,end in [('simul_whisper/generation_progress.py',1,500),('simul_whisper/simul_whisper.py',899,927),('simul_whisper/simul_whisper.py',1024,1118)]:
 lines=(P/rel).read_text().splitlines();print(json.dumps(dict(path=rel,lines=[dict(line=i+1,text=lines[i]) for i in range(start-1,min(end,len(lines)))]),ensure_ascii=False))
