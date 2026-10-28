"""Read-only old-development inventory; never reads H3 held-out outcomes."""
import json
from pathlib import Path
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9')
O=B/'results/revtrace/physical_retirement_20261028'
P=B/'projects/revtrace_physical_retirement_20261028'
p=json.loads((P/'CONFIRMATION_DEV_PLAN_v3_FROZEN.json').read_text())
for c in p['cells']:
    if c['adapter']!='qwen':continue
    d=Path(c['output'])
    print('CELL',c['cell_id'])
    print('FILES',sorted(str(x.relative_to(d)) for x in d.rglob('*') if x.is_file()))
    s=json.loads((d/'SUMMARY.json').read_text())
    print('INDEPENDENT',json.dumps(s['independent_summary']))
    a=d/'attempt0'
    for f in a.glob('*.jsonl'):
        print('JSONL',f.name)
        with f.open() as h:
            for i,line in enumerate(h):
                if i<3:print(line[:3000].rstrip())
                else:break
