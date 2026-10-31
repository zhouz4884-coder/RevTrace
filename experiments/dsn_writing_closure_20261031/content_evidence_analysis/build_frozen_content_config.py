"""Build a concrete config from existing bounded indices after source/env freeze.

This script never opens SSH or launches the frozen runner. Required hash/commit
arguments prevent placeholders being mistaken for a launchable experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'experiments/dsn_strengthening_20261031'
HERE=Path(__file__).resolve().parent
B='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9'
P=B+'/projects/revtrace_dsn_writing_closure_20261031'
O=B+'/results/revtrace/dsn_writing_closure_20261031'

def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--environment-path',required=True);p.add_argument('--environment-sha256',required=True)
    p.add_argument('--root-gate-path',required=True);p.add_argument('--root-gate-sha256',required=True)
    p.add_argument('--mode',choices=['controls','complete20'],required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--suffix',default='v1');a=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',a.source_commit)
    assert all(re.fullmatch('[0-9a-f]{64}',x) for x in (a.manifest_sha256,a.environment_sha256,a.root_gate_sha256))
    assert all(v.startswith(B+'/') for v in (a.environment_path,a.root_gate_path))
    assert re.fullmatch('[a-z0-9_]+',a.suffix)
    audit=read(HERE/'COMPLETED_METADATA_CONTENT_INDEX.json')
    inputs=[{k:r[k] for k in ('path','bytes','sha256')} for r in audit['future_CPU_recount_input_candidates']]
    paired=read(E/'PAIRED32_V2_RESULTS/SUMMARY.json')['cells'];resident=read(E/'RESIDENT4_V2_RESULTS/SUMMARY.json')['cells']
    cells=[]
    for phase,rows,cohort in [('PAIRED32_V2_RESULTS',[r for r in paired if r['version']=='final'],'paired'),('RESIDENT4_V2_RESULTS',resident,'resident')]:
        idx=read(E/phase/'RAW_INDEX.json');bounded=read(E/phase/'BOUNDED_INDEX.json')
        for r in rows:
            cid=r['cell_id'];arm=r['strategy'] if cohort=='paired' else r['arm'];rep=r['repeat']
            config=read(E/'paired_resident_inputs_v2'/('paired32_v2_configs' if cohort=='paired' else 'resident4_v2_configs')/(cid+'.json'))
            # The runtime CONFIG is separately inventory-pinned and checked
            # against the durable genesis by the runner. The local preregistered
            # template can have orchestration metadata differences; it supplies
            # only the immutable source identities below, which are rechecked.
            sources={s['source_id']:s for s in config['settings']['sources']}
            prefix='cells/'+cid+'/'
            owners=sorted({item['path'][len(prefix):].split('/')[0] for item in idx['files'] if item['path'].startswith(prefix+'owner_e')})
            cells.append(dict(cell_id=cid,cohort=cohort,arm=arm,repeat=rep,raw_root=idx['raw_root']+'/cells/'+cid,
                owner_directories=owners,source_ids=sorted(sources),expected_sources=[{k:sources[sid][k] for k in ('source_id','frames','audio_sha256')} for sid in sorted(sources)]))
        inputs.append(dict(path=bounded['raw_manifest'],bytes=(E/phase/'RAW_INDEX.json').stat().st_size,sha256=sha(E/phase/'RAW_INDEX.json')))
    label='content_cpu_controls' if a.mode=='controls' else 'final4f_existing20_content_cpu'
    name=label+'_'+a.suffix;out=O+'/'+name
    cfg=dict(experiment_id='SC_FINAL4F_EXISTING20_CONTENT_'+a.mode.upper()+'_'+a.suffix.upper(),mode=a.mode,
        analysis_source_commit=a.source_commit,analysis_source_manifest_sha256=a.manifest_sha256,
        analysis_source_root=P+'/content_source_'+a.suffix,analysis_source_manifest=P+'/CONTENT_SOURCE_'+a.suffix+'.json',
        environment_record=a.environment_path,environment_record_sha256=a.environment_sha256,
        root_noarg_preflight=a.root_gate_path,root_noarg_preflight_sha256=a.root_gate_sha256,
        lease_path=O+'/leases/'+name+'.lock',stdout_path=O+'/'+name+'.stdout.json',stderr_path=O+'/'+name+'.stderr.log',
        intended_output=out,aggregate_summary_location=out+'/SUMMARY.json',gate_decision_location=out+'/GATE.json',
        minimum_free_bytes=512*1024*1024,max_input_bytes=256*1024*1024,max_output_bytes=8*1024*1024,
        max_elapsed_seconds=1800,acoustic_source_ids=sorted({sid for c in cells for sid in c['source_ids']}),
        cells=sorted(cells,key=lambda c:c['cell_id']),inputs=inputs,
        original_raw_inventories=[dict(path=read(E/phase/'BOUNDED_INDEX.json')['raw_manifest'],sha256=sha(E/phase/'RAW_INDEX.json')) for phase in ('PAIRED32_V2_RESULTS','RESIDENT4_V2_RESULTS')],
        endpoint_contract=dict(actual_text='LCP versioned Unicode code-point occurrences, raw and whitespace_stripped',
            support='Whole first actual view at actual G, selected Canonical transcript keyed by source/G; mismatch and unknown separate',
            requests='Original per-request REQUEST_ORIGINS plus ledger/ingress; all offered 500ms and EOS; original D2/C8',
            continuity='Verified actual complete dependency paths and Consumer updates; same tip merges across compatible boundaries; last actual same-source observation right-censored',
            unknown='Missing G remains unknown; missing causal path fails without zero-error claim',
            no_new_model_calls=True),
        prior_bounded_metadata_index_sha256=sha(HERE/'COMPLETED_METADATA_CONTENT_INDEX.json'))
    assert len(cells)==20 and len(inputs)==330 and sum(r['bytes'] for r in inputs)<=cfg['max_input_bytes']
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf8',newline='\n') as f:json.dump(cfg,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(config=str(a.out),sha256=sha(a.out),cells=len(cells),input_files=len(inputs),input_bytes=sum(r['bytes'] for r in inputs),intended_output=out)))

if __name__=='__main__':main()
