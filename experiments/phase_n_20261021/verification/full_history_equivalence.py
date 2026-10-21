"""Cross-run equivalence of all canonical transitions, not only terminal P."""
import argparse,hashlib,json
from collections import defaultdict
from pathlib import Path
def normalized(cell):
    rows=defaultdict(list)
    for line in (cell/'events.jsonl').read_text().splitlines():
        e=json.loads(line)
        if e['kind']=='commit':
            rows[e['session_id']].append({k:e[k] for k in ['parent','version','audio_start_sample','audio_end_sample',
                'segment_id','segment_tokens','next_prompt_tokens']})
    return {str(sid):sorted(v,key=lambda r:r['version']) for sid,v in sorted(rows.items())}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    groups=defaultdict(list);output=[]
    for cell in sorted(a.root.iterdir()):
        if not (cell/'result.json').exists():continue
        config=json.loads((cell/'config.json').read_text());history=normalized(cell)
        digest=hashlib.sha256(json.dumps(history,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        groups[config['rho']].append(digest);output.append({'cell':cell.name,'rho':config['rho'],'canonical_transition_content_sha256':digest,
            'transitions':sum(len(v) for v in history.values())})
    checks={str(k):len(set(v))==1 for k,v in groups.items()}
    a.out.write_text(json.dumps({'all_same_rho_histories_exact':all(checks.values()),'by_rho':checks,'cells':output,
        'excluded':'wall clocks, contract/runtime hashes for declared scheduling policy, inter-session interleaving and speculative invalidation metadata'},indent=2)+'\n')
    print(json.dumps({'same_rho':checks,'cells':len(output)}));assert all(checks.values()),'Canonical content differs: investigate actual input/batch and repeat controls'
