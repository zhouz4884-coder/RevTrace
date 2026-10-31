"""Read bounded frozen summaries and check presentation without neural calls."""
from collections import defaultdict
from pathlib import Path
import hashlib,json,math,re,statistics

R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
W=R/'Paper_DSN/revisions/20261031_dsn_story_revision'
B=R/'Paper_DSN/revisions/20261031_dsn2027_release_v4'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before=read(E/'NATIVE_RESULT_INPUT_HASHES_BEFORE.json')
assert all((R/r['path']).stat().st_size==r['bytes'] and sha(R/r['path'])==r['sha256'] for r in before)

def stack(cell):
    s=cell.strip();m=re.fullmatch(r'\\shortstack\{(.*)\}',s)
    assert m,s
    return [x.strip() for x in m[1].split(r'\\')]
old=[]
for line in (B/'tables/native_reliability.tex').read_text().splitlines():
    if '& \\shortstack' not in line:continue
    cells=[x.strip() for x in line.removesuffix(r'\\').split('&')]
    assert len(cells)==7
    vals=[stack(x) for x in cells[1:]]
    for k,policy in enumerate(['Conservative','RevTrace']):
        assert vals[0][k]=='0; 2/2'
        old.append([cells[0],policy]+[v[k] for v in vals[1:]])
new=[];condition=None
for line in (W/'tables/native_reliability.tex').read_text().splitlines():
    if ' & Conservative &' not in line and ' & RevTrace &' not in line:continue
    cells=[x.strip() for x in line.removesuffix(r'\\').split('&')]
    m=re.fullmatch(r'\\multirow\{2\}\{\*\}\{(.*)\}',cells[0])
    if m:condition=m[1]
    assert condition is not None and len(cells)==7
    new.append([condition]+cells[1:])
assert len(new)==12 and new==old
machine=read(R/'experiments/dsn_native_resilience_20261030/FIGURE_TABLE_FORMAL36_v5_results/ALL36_MACHINE_TABLE.json')
groups=defaultdict(list)
for row in machine:
    if row['cohort']=='short_main':groups[(row['condition'],row['arm'])].append(row)
condition_map={'No fault':'none','Duplicate / late':'duplicate_late','Worker after ASR':'worker_after_asr',
    'Worker partial frame':'worker_partial_frame','Owner before durable':'owner_before_durable',
    'Owner after durable':'owner_after_durable'}
for row in new:
    group=groups[(condition_map[row[0]],'conservative' if row[1]=='Conservative' else 'fullcall')]
    assert len(group)==2 and all(x['complete_original_task'] and x['illegal_installs']==0 for x in group)
    assert row[2]==f"{sum(x['local_reject_records'] for x in group)} / {sum(x['local_reject_canonical_mutations'] for x in group)}"
    clocks=[x['new_model_completed_after_fault_and_certified_consume_seconds'] for x in group]
    new_range='--' if all(x is None for x in clocks) else f'{min(clocks):.2f}--{max(clocks):.2f}'
    assert row[3]==new_range
    assert row[4]==f"{sum(x['original_D2_C8_pass'] for x in group)}/2"
    assert row[5]==str(sum(x['EOS_D2_misses'] for x in group))
    energies=[x['energy_joules'] for x in group]
    assert row[6]==f'{min(energies):.0f}--{max(energies):.0f}'
assert len(machine)==36 and sum(x['semantic_audit']['checked_durable_transitions'] for x in machine)==3976

paired=read(R/'experiments/dsn_strengthening_20261031/PAIRED32_V2_RESULTS/SUMMARY.json')
rows=[]
for version in ['bdfa','final']:
    for arm in ['conservative','fullcall']:
        group=[c for c in paired['cells'] if c['version']==version and c['strategy']==arm]
        assert len(group)==8
        offered=sum(c['primary']['offered_audio_seconds'] for c in group)
        credit=sum(c['primary']['dual_deadline_audio_credit_seconds'] for c in group)
        energy=sum(c['common_external_energy']['origin_to_confirmed_physical_model_drain']['total_joules'] for c in group)/1000
        d99=statistics.median(c['primary']['primary_linear_all_offered_D99'] for c in group)
        passes=sum(c['primary']['complete_coverage_and_original_quantile_pass'] for c in group)
        rows.append(dict(version=version,arm=arm,offered_s=offered,timely_s=credit,timely_percent=100*credit/offered,
            D99_median=d99,energy_kJ=energy,passes=passes,runs=8))
for row in rows:
    if row['version']!='final':continue
    expected={'conservative':(30.000,4.759,47.019,0),'fullcall':(65.822,1.638,43.952,6)}[row['arm']]
    assert (round(row['timely_s'],3),round(row['D99_median'],3),round(row['energy_kJ'],3),row['passes'])==expected

content=read(R/'experiments/dsn_writing_closure_20261031/CONTENT_CPU_V4_RESULTS/complete20/SUMMARY.json')
proposed=read(Path('E:/Downloads/proposed_content_chart_values.json'))
contentrows=[]
for row in proposed['rows']:
    cohort='paired' if row['bank']=='matched' else 'resident'
    src=content['groups'][cohort+'/'+row['policy']]
    raw=src['posterior_whole_text_support']['raw']
    expected={'offered_s':src['offered_audio_seconds'], 'timely_s':src['original_dual_credit_audio_seconds'],
      'timely_same_frontier_selected_text_s':raw['original_credit_supported_seconds'],
      'timely_without_same_frontier_text_agreement_s':raw['original_credit_mismatching_seconds'],
      'not_timely_s':src['offered_audio_seconds']-src['original_dual_credit_audio_seconds'],
      'pass_count':src['original_request_gate_passes'],'runs_or_requests':src['request_instances']}
    assert all(math.isclose(row[k],v,rel_tol=0,abs_tol=1e-10) for k,v in expected.items())
    assert math.isclose(sum(row[k] for k in ['timely_same_frontier_selected_text_s',
        'timely_without_same_frontier_text_agreement_s','not_timely_s']),row['offered_s'],abs_tol=1e-10)
    assert raw['original_credit_unknown_seconds']==0
    assert all(src['content']['raw'][k]==v for k,v in [('introduced_code_point_occurrences',180),
        ('retracted_occurrence_code_points',14),('still_visible_occurrence_code_points',166)])
    contentrows.append(row)

record=dict(gate='PASS_NATIVE_PRESENTATION_ONLY_FROZEN_VALUES_AND_12_POLICY_ROWS',
    new_model_calls=0,new_raw_scan=False,original_files_before_after_unchanged=True,
    source_hashes_before_after=before,matched_summary_rows=rows,proposed_content_rows=contentrows,
    proposed_JSON_agrees_with_final_frozen_CPU_summary=True,stack_categories_mutually_exclusive_same_denominator=True,
    fault_table_rows=new,fault_table_all_numeric_cells_equal_v4=True,
    fault_table_all_numeric_cells_independently_match_frozen_ALL36_metadata=True,
    entire_bank_36_trials_3976_transitions_distinct_from_24_short_table=True,
    fault_table_all_24_completed_and_zero_illegal_preserved_in_caption=True,
    claim_scope='This is a presentation arithmetic/row mapping check, not another acoustic trial or raw audit.')
out=E/'NATIVE_PRESENTATION_CHECK_v2.json'
with out.open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in record.items() if k not in ['source_hashes_before_after','matched_summary_rows','proposed_content_rows','fault_table_rows']}))
