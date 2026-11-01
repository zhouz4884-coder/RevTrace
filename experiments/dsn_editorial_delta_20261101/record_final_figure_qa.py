"""Bind numeric/source checks to completed actual PDF and grayscale review."""
from pathlib import Path
import hashlib,json,subprocess,datetime,re,xml.etree.ElementTree as ET
E=Path(__file__).resolve().parent;S=E/'final_source_v1';O=E/'FIGURES_FINAL'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
sm=read(S/'SOURCE_MAP.json');manifest=read(E/'FIGURE_SOURCE_FINAL.json')
c=subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()
assert c==manifest['code_commit']=='0040aa8b0a6bef71670776e6f4fa7581cf16e67d'
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain','--untracked-files=all']).strip()
for row in manifest['files']:assert sha(S/row['path'])==row['sha256'] and (S/row['path']).stat().st_size==row['bytes']
for row in sm['bounded_inputs']:assert sha(S/row['copy'])==row['sha256'] and sha(row['original'])==row['sha256']
for row in sm['protected']:assert sha(row['path'])==row['sha256']
assert read(O/'CONTROL_HASHES_BEFORE.json')==read(O/'CONTROL_HASHES_AFTER.json')
for path,value in read(O/'CONTROL_HASHES_AFTER.json').items():assert sha(Path(path))==value
old=next(S/r['copy'] for r in sm['bounded_inputs'] if r['key']=='original_numeric_values')
assert read(O/'MAIN_EFFECT_NUMERIC_VALUES.json')==read(old)
comparison=next(S/r['copy'] for r in sm['bounded_inputs'] if r['key']=='actual_interval_comparison')
assert (O/'ACTUAL_INTERVAL_COMPARISON.json').read_bytes()==comparison.read_bytes()
for row in read(E/'V2_OUTPUTS_BEFORE_FINAL_RENDER.json'):assert sha(row['path'])==row['sha256']
names=['timely_interval_comparison','coordination_protocol','core_interaction','native_content'];figures=[]
for name in names:
 q=read(O/(name+'.QA.json'));assert not q['out_of_canvas_text'] and q['minimum_font_pt']>=8.5 and q['Type3_fonts']==0
 assert q['SVG_editable_text_nodes']>0 and all(r['embedded_bytes']>0 for r in q['PDF_fonts'])
 figures.append(dict(name=name,width_inches=q['width_inches'],height_inches=q['height_inches'],minimum_font_pt=q['minimum_font_pt'],pdf_sha256=sha(O/(name+'.pdf')),svg_sha256=sha(O/(name+'.svg')),actual_PDF_preview_sha256=sha(O/(name+'_PDF_PAGE.png')),actual_grayscale_preview_sha256=sha(O/(name+'_GRAYSCALE_QA.png'))))
words=[]
for node in ET.parse(O/'coordination_protocol.svg').findall('.//{http://www.w3.org/2000/svg}text'):
 words.extend(w for w in re.findall(r'[A-Za-z]+(?:/[A-Za-z]+)*',''.join(node.itertext())) if len(w)>1 and w not in {'EL','AU','SUP'})
assert len(words)<=60
result=dict(gate='PASS_APPROVED_FOUR_FIGURE_SOURCE_NUMERIC_VECTOR_AND_ACTUAL_VISUAL_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=c,source_manifest_sha256=sha(E/'FIGURE_SOURCE_FINAL.json'),actual_interval_analysis_commit=sm['actual_interval_analysis_commit'],original_interval_neural_source='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',native_original_neural_source='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',new_model_calls=0,actual_reader_calls=0,inputs_verified=len(sm['bounded_inputs']),protected_v7_and_original_artwork_files_verified=len(sm['protected']),all_inputs_and_controls_before_after_unchanged=True,source_clean_complete_manifest=True,numeric_objects_exactly_equal_v7=True,comparison_JSON_byte_identical=True,prior_v2_30_outputs_unchanged=True,actual_PDF_previews_viewed=4,actual_grayscale_previews_viewed=4,mechanism_english_tokens_excluding_math_and_judgment_tags=len(words),minimum_figure_label_pt=8.5,mechanism_event_numbers=dict(parentP2_and_SUP=1,subsequent_installedP3=2),input_icon_meanings=['immutable audio/source','target/EOS binding','complete frozen feedback state','model/decoder contract'],colour_meanings=dict(purple='original computation',blue='selected state/fact',teal='provisional whole view and supported retention',amber='unresolved eligibility or deadline excess',warm_red='withdrawal action; selected P2 remains blue'),core_line_interpretation='categorical factor contrasts; pooled 3-cohort totals; no confidence intervals',core_coverage_axis_percent=[85,100],native_single_column_width_inches=3.48,native_pass_column_removed=True,time_first_rail_legend_gap_pt=read(O/'timely_interval_comparison.QA.json')['details']['legend_to_first_chip_gap_pt'],final_paper_visual_review='Parent responsibility at actual LaTeX scale',prior_development_records=dict(first_formal_renderer='FAIL metadata input alias path; original data and source unchanged',second_third_formal_renderers='numeric/vector pass but not final beauty acceptance',approved_style='changed following explicit user preferences; no data or runtime changes'),figures=figures)
with (E/'FIGURE_QA_FINAL.json').open('x',encoding='utf8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='figures'}))
