"""Unicode minimum edit identity ledger; LCP is a separate descriptive count."""
from agreement import lcp
import hashlib


def align(a, b, alternate=False):
    m, n = len(a), len(b)
    d = [list(range(n+1))]
    for i in range(1, m+1):
        row = [i] + [0]*n
        for j in range(1, n+1):
            row[j] = min(d[i-1][j]+1, row[j-1]+1, d[i-1][j-1]+(a[i-1] != b[j-1]))
        d.append(row)
    i, j, out = m, n, []
    order = ('I','D','S') if alternate else ('S','D','I')
    while i or j:
        if i and j and a[i-1] == b[j-1] and d[i][j] == d[i-1][j-1]:
            out.append(('M', i-1, j-1)); i -= 1; j -= 1
            continue
        legal = {}
        if i and j and d[i][j] == d[i-1][j-1]+1: legal['S'] = (i-1,j-1)
        if i and d[i][j] == d[i-1][j]+1: legal['D'] = (i-1,j)
        if j and d[i][j] == d[i][j-1]+1: legal['I'] = (i,j-1)
        op = next(k for k in order if k in legal)
        ni,nj = legal[op]; out.append((op,i-1 if op!='I' else None,j-1 if op!='D' else None)); i,j=ni,nj
    out.reverse()
    if sum(op!='M' for op,_,_ in out) != d[m][n]: raise ValueError('edit conservation')
    return out


def ledger(rows, alternate=False, strip=False):
    text, live = '', []
    total = dict(I=0,D=0,S=0,minimum_edit_distance=0,LCP_erased=0,retired_character_seconds=0.,retired_characters=0)
    last = None
    for r in rows:
        t = r['observed']; new = r['text']
        if strip: new = ''.join(c for c in new if not c.isspace())
        if last is not None and t < last: raise ValueError('text clock order')
        path=align(text,new,alternate); target=[]
        for op,i,j in path:
            if op=='M': target.append(live[i])
            else:
                total[op]+=1; total['minimum_edit_distance']+=1
                if op in ('D','S'):
                    total['retired_character_seconds']+=t-live[i][1]
                    total['retired_characters']+=1
                if op in ('I','S'): target.append((new[j],t))
        total['LCP_erased']+=len(text)-len(lcp(text,new))
        text,live,last=new,target,t
        if ''.join(c for c,_ in live)!=text: raise ValueError('aligned identity conservation')
    if total['I']-total['D'] != len(text): raise ValueError('I-D final-length conservation')
    total.update(final_text_code_points=len(text),final_text_sha256=hashlib.sha256(text.encode('utf8')).hexdigest(),
        right_censored_survivor_character_seconds=sum(last-t for _,t in live) if last is not None else 0.,
        alignment='match then I/D/S' if alternate else 'match then S/D/I',
        horizon=last,exposure_scope='Measured display proxy on offline decision output; alignment-dependent, not validated human experience')
    return total
