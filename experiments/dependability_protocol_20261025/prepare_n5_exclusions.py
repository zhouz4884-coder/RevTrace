"""Conservative prior-source exclusion, no model output or held-out generation."""
from pathlib import Path
import hashlib,json,re
W=Path(__file__).resolve().parent;ids=set();audio=set();count=0
pattern=re.compile(r'(?<!\d)(\d{1,5}-\d{1,7}-\d{4})(?!\d)')
roots=[W/'source_archive_v3',W/'public_tables',W/'historical_20261020',W/'n5_pilot_collected_v1/DEVELOPMENT_MANIFEST.json']
def scan(value,key=''):
    if isinstance(value,dict):
        for k,v in value.items():scan(v,k)
    elif isinstance(value,list):
        for v in value:scan(v,key)
    elif isinstance(value,str):
        ids.update(pattern.findall(value))
        if 'audio' in key.lower() and 'sha' in key.lower() and len(value)==64:audio.add(value)
for root in roots:
    files=[root] if root.is_file() else list(root.rglob('*'))
    for p in files:
        if not p.is_file() or p.stat().st_size>2_000_000:continue
        if p.suffix.lower()=='.json':
            try:scan(json.loads(p.read_text(encoding='utf8')));count+=1
            except (ValueError,UnicodeError):pass
        elif p.suffix.lower() in ['.csv','.md']:ids.update(pattern.findall(p.read_text(encoding='utf8',errors='replace')))
out=dict(protocol='REVTRACE-N5-INDEPENDENT-SOURCES-20261026',excluded_native_ids=sorted(ids),
    excluded_speakers=sorted({i.split('-')[0] for i in ids}),excluded_audio_digests=sorted(audio),
    source_scope='conservative public prior evidence/metadata, may exclude unused predeclared pools too',
    files_scanned_JSON=count,selection_seed='REVTRACE-N5-HELDOUT-20261026',
    duration_bounds_seconds=[16,28],requested=32,
    planned_rule='metadata/hash selection only;32 distinct speakers preferred;source-disjoint required;unseen speaker claim only if verified',
    neural_GPU_calls=0)
p=W/'N5_SOURCE_EXCLUSIONS_v1.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'excluded_ids':len(ids),'speakers':len(out['excluded_speakers']),'audio_hashes':len(audio)}))
