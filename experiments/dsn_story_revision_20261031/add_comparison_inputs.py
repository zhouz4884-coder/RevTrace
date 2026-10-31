"""Pin actual already-extracted two-arm inputs without calculating outcomes."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent;S=E/'figure_source_dev'
p=S/'SOURCE_MAP.json';m=json.loads(p.read_bytes())
index=E/'FIG1_COMPARISON_LOCAL_INPUT_INDEX_v1.json';ix=json.loads(index.read_bytes())
need=lambda v:None if v else (_ for _ in ()).throw(ValueError('Input pin mismatch'))
for row in ix['input_files']:
 src=Path(row['path']);data=src.read_bytes();need(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'])
 name=row['arm']+'_'+src.name;dest=S/'inputs'/name;need(not dest.exists());dest.write_bytes(data)
 m['bounded_inputs'].append(dict(key='comparison_'+row['arm']+'_'+src.stem,copy='inputs/'+name,original=str(src),bytes=len(data),sha256=row['sha256']))
for key,src,name in [('comparison_index',index,'COMPARISON_INPUT_INDEX.json'),
 ('comparison_download_inventory',Path(ix['inventory']),'COMPARISON_DOWNLOAD_INVENTORY.json')]:
 data=src.read_bytes();(S/'inputs'/name).write_bytes(data)
 m['bounded_inputs'].append(dict(key=key,copy='inputs/'+name,original=str(src),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
src=R/'experiments/dsn_full_interval_case_20261029/source_v2/interaction_opportunities_v1.py'
data=src.read_bytes();(S/'interaction_opportunities_v1.py').write_bytes(data)
m['dependencies']=[dict(path='interaction_opportunities_v1.py',original=str(src),sha256=hashlib.sha256(data).hexdigest(),
 provenance='Exact pure complete_chain implementation from earlier case extractor; no neural import or main execution')]
p.write_bytes((json.dumps(m,indent=2)+'\n').encode())
cfg=json.loads((S/'CONFIG.json').read_bytes());cfg.update(input_map_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
 scope='Writing artwork plus bounded two-arm actual Consumer-clock extraction; no new neural experiment',
 comparison=dict(offered_F=224000,session_id=7,source_id='3570-5694-0003',policy='Report actual Joint result even if later or unhelpful; no same-event counterfactual'))
(S/'CONFIG.json').write_bytes((json.dumps(cfg,indent=2)+'\n').encode())
print(json.dumps(dict(bound_inputs=len(m['bounded_inputs']),comparison_input_files=len(ix['input_files']),comparison_input_bytes=ix['input_bytes'],new_model_calls=0)))
