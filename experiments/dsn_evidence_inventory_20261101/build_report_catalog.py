"""Read-only, bounded entry-point catalog; does not execute research code."""
from pathlib import Path
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
TOKENS = {
    'causality': r'causal|propagat|downstream|later.input|content.only',
    'recovery': r'cold|recover|accepted.debt|old.fact|new.fact',
    'retirement': r'retire|drain|physical|lease|cancel',
    'service': r'D2|C8|SLO|deadline|coverage|Goodput|withdraw',
    'cost': r'overhead|CPU|energy|fsync|microsecond',
    'formal': r'counterexample|TLC|TLAPS|refinement|model.check',
    'decision': r'NO.GO|GO.NO|gate|decision|INSUFFICIENT',
}
EXCLUDED = {'runtime', 'source', 'source_v2', 'source_v3', 'source_v4',
            'source_v5', 'source_v6', 'source_bundles', 'collected',
            'exports', 'delivery_final', 'vendor', 'runtime_source'}

def eligible(p):
    rel = p.relative_to(ROOT)
    parts = rel.parts
    if parts[0] == 'experiments':
        return (parts[1] != OUT.name and len(parts) <= 5
                and not any(x in EXCLUDED or x.startswith('source_') for x in parts[2:-1]))
    return parts[0] in {'docs', 'results', 'Paper_TC', 'Paper'} and len(parts) <= 5

paths = sorted(p for top in ('experiments','docs','results','Paper_TC','Paper')
               for p in (ROOT / top).rglob('*.md') if eligible(p))
rows, unique, headings = [], {}, {}
for p in paths:
    b = p.read_bytes()
    if len(b) > 400_000:
        continue
    body = b.decode('utf-8-sig', errors='replace')
    sha = hashlib.sha256(b).hexdigest()
    rel = p.relative_to(ROOT).as_posix()
    family = rel.split('/')[1] if rel.startswith('experiments/') else rel.split('/')[0]
    tags = [name for name, pat in TOKENS.items() if re.search(pat, body, re.I)]
    lines = body.splitlines()
    rows.append({'path': rel, 'family': family, 'bytes': len(b), 'lines': len(lines),
                 'sha256': sha, 'duplicate_of': unique.get(sha, ''),
                 'tags': ';'.join(tags)})
    if sha not in unique:
        unique[sha] = rel
        hs = [{'line': i + 1, 'text': line[:240]} for i, line in enumerate(lines)
              if line.startswith('#')]
        headings[rel] = hs

with (OUT / 'REPORT_CATALOG.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
(OUT / 'REPORT_HEADINGS.json').write_text(json.dumps(headings, ensure_ascii=False, indent=2), encoding='utf-8')
stats = {'scope': 'Shallow Markdown entry points only; lexical text scan and hash deduplication, not human full reading or result revalidation.',
         'catalogued_files': len(rows), 'unique_byte_contents': len(unique),
         'bytes_scanned': sum(r['bytes'] for r in rows),
         'excluded': sorted(EXCLUDED), 'max_depth_parts': 5, 'max_bytes_each': 400000,
         'family_counts': {x: sum(r['family'] == x for r in rows) for x in sorted(set(r['family'] for r in rows))}}
(OUT / 'CATALOG_STATS.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(stats, ensure_ascii=False))
