"""Finite-horizon equality is neither equal WER nor permanent convergence."""
import re,unicodedata

def validate_runtime_manifest(data):
    rows=data.get('sessions',[])
    if not rows or len({r.get('source_id') for r in rows})!=len(rows):raise ValueError('unique native source records required')
    for r in rows:
        if any(k not in r for k in ['path','source_id','audio_sha256','language','duration','reference']):raise ValueError('missing worker manifest fields')
        if r['language']!='English' or not 30<=r['duration']<=60:raise ValueError('outside frozen R3 source contract')
    return True

def edit_distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def quality(reference,hypothesis):
    normalize=lambda s:unicodedata.normalize('NFKC',s).lower()
    words=lambda s:re.findall(r"[a-z0-9']+",normalize(s))
    chars=lambda s:[x for x in normalize(s) if x.isalnum()]
    rw,hw=words(reference),words(hypothesis);rc,hc=chars(reference),chars(hypothesis)
    return {'word_errors':edit_distance(rw,hw),'reference_words':len(rw),
            'char_errors':edit_distance(rc,hc),'reference_chars':len(rc)}

def trajectory_summary(windows,fault_window,*,censor_reason='source_end'):
    post=[w for w in windows if w['window']>fault_window]
    out={'fault_window':fault_window,'observed_future_windows':len(post),'censor_reason':censor_reason}
    for kind in ['P','Z','Y']:
        eq=[w[kind+'_equal'] for w in post];first=next((i+1 for i,v in enumerate(eq) if v),None)
        red=[i+1 for i,v in enumerate(eq) if first is not None and i+1>first and not v]
        out[kind]={'first_equal_K':first,'first_equal_right_censored':first is None,
                   'redivergence_windows':red,'equal_at_observed_endpoint':eq[-1] if eq else None,
                   'permanent_convergence_not_claimed':True}
    return out
