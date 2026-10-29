"""Read-only, bounded immediate directory inventory. No audio reads/downloads."""
import datetime,json,pathlib
B=pathlib.Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
paths=[B/'datasets',B/'datasets/revtrace',B/'datasets/revtrace/streamcorrect_adaptation_20261028',
       B/'datasets/revtrace/streamcorrect_adaptation_20261028/audio',
       B/'cache/revtrace_streamcorrect_20261028']
out=[]
for p in paths:
    if not p.is_dir():out.append(dict(path=str(p),exists=False));continue
    rows=[]
    for i,c in enumerate(sorted(p.iterdir())):
        if i>=100:raise RuntimeError('bounded directory inventory limit exceeded')
        st=c.stat();rows.append(dict(name=c.name,directory=c.is_dir(),bytes=st.st_size))
    out.append(dict(path=str(p),exists=True,entries=rows))
print(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='five immediate directories, stat only; no recursive scan or audio reads',
    directories=out,downloaded=False,model_calls=False)))
