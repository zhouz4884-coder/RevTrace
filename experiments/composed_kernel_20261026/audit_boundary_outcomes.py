"""Real applied P8 outcomes, not compatibility labels alone. Read-only."""
from pathlib import Path
import json,csv,hashlib
P=Path(__file__).resolve().parent
B=Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9');O=B/'results/revtrace/dependability_20261025'/P.name
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def main():
    out=[]
    for stage in ['boundary_pilot','boundary']:
        done=read(O/stage/'SUMMARY.json');cells=read(O/stage/'FREEZE.json')['cells']
        for name,c in zip(done['completed'],cells):
            D=O/stage/name/'attempt0';probe=read(D/'BOUNDARY_PROBE.json')
            events=rows(D/'events.jsonl');views=rows(D/'consumer.jsonl');records=rows(D/'worker_records.jsonl')
            lookup={(r['session_id'],r['source_kind'],r['server_time']):r for r in views}
            for w in probe['witnesses']:
                sid=w['session_id'];p8=[r for r in records if r['job']['role']=='proposal' and r['job']['session_id']==sid and r['job']['end_window']==4]
                assert len(p8)==1;pr=p8[0]
                es=[e for e in events if e['kind']=='display' and e.get('job_id')==pr['job']['job_id']]
                assert len(es)==1;e=es[0];view=lookup[sid,'display',e['displayed']]
                assert view['certified_frontier']==96000 and view['canonical_version']==3
                assert not view['joined_suffix']
                if w['P6_equals_A6']:
                    assert view['valid_visible_frontier']==128000
                    assert view['visible_text']==pr['result']['text']
                else:
                    assert view['valid_visible_frontier']==view['certified_frontier']
                    assert view['visible_text']==view['certified_text']
                out.append(dict(stage=stage,episode=name,adapter=c['adapter'],method=c['method'],condition=c['probe'],repeat=c['repeat'],
                    session_id=sid,source_id=pr['job']['source_id'],birth_parent=pr['job']['parent'],applied_root_version=view['canonical_version'],
                    actual_private_complete_frontier=pr['job']['audio_end_sample'],actual_certified_frontier=view['certified_frontier'],
                    actual_applied_visible_frontier=view['valid_visible_frontier'],root_projection_compatible=w['P6_equals_A6'],
                    outcome='legal provisional progress preserved' if w['P6_equals_A6'] else 'incompatible private view withdrawn, no fresh credit',
                    joined_certified_suffix=False,new_GPU_private_result=True,
                    source_tier='controlled completion/installation/delivery order, not natural prevalence'))
    dest=O/'BOUNDARY_ACTUAL_OUTCOMES_v1.json';assert not dest.exists()
    formal=[r for r in out if r['stage']=='boundary']
    dest.write_text(json.dumps(dict(status='PASS_ACTUAL_LATE_PRIVATE_PROGRESS_AND_WITHDRAWAL',rows=out,
        formal_observations=len(formal),formal_compatible_ahead=sum(r['root_projection_compatible'] for r in formal),
        formal_incompatible_withdrawn=sum(not r['root_projection_compatible'] for r in formal),
        formal_unique_sources=len({r['source_id'] for r in formal}),not_independent_samples_per_row=True),indent=2)+'\n')
    with (O/'BOUNDARY_ACTUAL_OUTCOMES_v1.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print(json.dumps(dict(status='PASS',formal=len(formal),compatible=sum(r['root_projection_compatible'] for r in formal))))
if __name__=='__main__':main()
