"""Read-only final artwork identity and numeric QA after actual image inspection."""
from pathlib import Path
import datetime,hashlib,json,subprocess
E=Path(__file__).resolve().parent;O=E/'FIGURES_v3';S=E/'figure_source_v3'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary=read(O/'SUMMARY.json');gate=read(O/'GATE.json');m=read(E/'FIGURE_SOURCE_v3.json')
assert gate['gate']=='PASS_FROZEN_WRITING_FIGURE_SOURCE_NUMERIC_AND_VECTOR_QA'
assert summary['actual_figure_source_commit']==m['code_commit']=='aaa13a008772700a2befb0b0d8022e1098f7d7e5'
assert summary['actual_interval_analysis_source_commit']=='73026a11f6db202d723e6028ad85e6833888ec78'
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain']).strip()
for r in m['files']:assert sha(S/r['path'])==r['sha256'] and (S/r['path']).stat().st_size==r['bytes']
source_map=read(S/'SOURCE_MAP.json')
for r in source_map['bounded_inputs']:assert sha(S/r['copy'])==r['sha256']==sha(Path(r['original']))
for r in source_map['protected_v4_files']:assert sha(Path(r['path']))==r['sha256']
for r in source_map['protected_v2_artwork']:assert sha(Path(r['path']))==r['sha256'] and Path(r['path']).stat().st_size==r['bytes']
changed=[];identical=[]
for qa in summary['figure_QA']:
 name=qa['figure']
 same=all((E/'FIGURES_v2'/(name+suffix)).read_bytes()==(O/(name+suffix)).read_bytes() for suffix in ['_PDF_PAGE.png','_GRAYSCALE_QA.png'])
 (identical if same else changed).append(name)
assert set(changed)=={'coordination_protocol','composition_and_content'}
assert (O/'CONTROL_HASHES_BEFORE.json').read_bytes()==(O/'CONTROL_HASHES_AFTER.json').read_bytes()
assert (O/'ACTUAL_INTERVAL_COMPARISON.json').read_bytes()==(E/'FIGURES_v1/ACTUAL_INTERVAL_COMPARISON.json').read_bytes()
assert sha(O/'ACTUAL_INTERVAL_COMPARISON.json')=='7df3c385a14c8842f745a66c8fb4f3635fee7cd916aad6d1e23af7cfdc80fd94'
core=read(S/'inputs/CORE_RUNS_110.json')
headline=[r for r in core if r['phase']=='primary' and r['adapter']=='qwen' and r['rho']==1 and r['arrival']=='staggered']
assert len(headline)==15 and all(r['display_P99']>2 for r in headline)
main=read(O/'MAIN_EFFECT_NUMERIC_VALUES.json')
assert [(r['withdrawals'],round(r['credit'],3)) for r in main['core']]==[(12,654.115),(1,628.435),(17,664.15),(0,680.76)]
assert len([c for r in main['core'] for c in r['cohorts']])==12
assert len(main['native'])==4 and all(abs(r['offered']-66.33975)<1e-9 and abs(sum(r[k] for k in ['matching','unmatched','untimely'])-r['offered'])<1e-9 for r in main['native'])
old48=read(S/'inputs/RUN_ENDPOINTS_48.json');new48=read(O/'PLOTTED_NUMERIC_VALUES.json')
for key,rows in new48.items():
 assert len(rows)==48
 expected={r['cell_id']:r[key] for r in old48}
 assert all(r['raw']==expected[r['cell_id']] for r in rows)
figures=[]
for qa in summary['figure_QA']:
 name=qa['figure'];assert qa['minimum_font_pt']>=8.5 and qa['width_inches']==7.125 and qa['Type3_fonts']==0 and not qa['out_of_canvas_text']
 assert all(r['embedded_bytes']>0 for r in qa['PDF_fonts']) and qa['SVG_editable_text_nodes']>0
 paths=[O/(name+s) for s in ['.pdf','.svg','.png','_PDF_PAGE.png','_GRAYSCALE_QA.png']]
 assert all(p.is_file() for p in paths)
 figures.append(dict(name=name,width_inches=qa['width_inches'],height_inches=qa['height_inches'],minimum_source_label_pt=qa['minimum_font_pt'],
  reviewed_pdf_preview=str(paths[3].relative_to(E)),reviewed_grayscale_preview=str(paths[4].relative_to(E)),
  source_files=[dict(path=str(p.relative_to(E)),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]))
assert len(figures)==6
record=dict(gate='PASS_SOURCE_NUMERIC_VECTOR_AND_ACTUAL_ARTWORK_VISUAL_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 actual_plot_source_commit=m['code_commit'],actual_interval_analysis_commit='73026a11f6db202d723e6028ad85e6833888ec78',
 source_manifest_sha256=sha(E/'FIGURE_SOURCE_v3.json'),original_neural_source_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',
 actual_figure_visual_review_coverage=6,changed_PDF_previews_viewed=2,changed_grayscale_previews_viewed=2,
 unchanged_previews_byte_identical_to_previously_viewed_v2=identical,new_model_calls=0,real_interval_reader_repeated=False,
 original15headline_runs_all_D2_fail=True,original12cohort_rows_retained=True,original48runs_all_values_retained=True,
 native4partitions_match_user_proposal_and_frozen_summary=True,all26pinned_inputs_after_SHA_unchanged=True,
 protected25v4files_unchanged=True,source_clean_and_full_manifest_match=True,frozen_control_hashes_before_after_match=True,
 protected53previous_v2_artwork_files_unchanged=True,
 prior_formal_plot_failure_preserved='FIGURES_v1/GATE.json',
 notes=['Text-only cold-read fixes: explicit UNKNOWN run/buffer, original Correct/Update complete result and checked parent, matching-content headline and Matched trials.',
  'Changed two PDF/grayscale previews were viewed; other four are byte-identical to actually viewed v2 images.',
  'Comparison ticks stay inside plot and both panels share their actual time/grid limits.',
  'Actual Joint F16 remains visible; Joint first coverage D2+27.4ms explicitly shown.','Only source-label font size is checked; math subscripts receive separate visual review.',
  'Marker/line/hatching/text cues remain readable in grayscale.','Final-paper placement and all-page review remain Root responsibility.'],figures=figures)
with (E/'FIGURE_QA_v3.json').open('x',encoding='utf8',newline='\n') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in record.items() if k!='figures'}))
