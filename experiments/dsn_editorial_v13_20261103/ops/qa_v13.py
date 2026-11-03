"""Bind editorial claims/figures to frozen evidence and render every final page."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess
import fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1]
P=R/'Paper_DSN/revisions/20261103_dsn2027_release_v13'
OLD=R/'Paper_DSN/revisions/20261102_dsn2027_release_v12'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def put(p,j):Path(p).write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
b=read(E/'baseline/FROZEN_INPUTS.json')
for row in b['frozen_v12_files']:
 p=R/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
oldfreeze=R/'experiments/dsn_v11_closure_20261102/baseline/FROZEN_V11_INPUTS.json'
assert sha(oldfreeze)==b['frozen_v11_manifest_sha256']
for row in read(oldfreeze)['rows']:
 p=R/row['path'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==b['legacy_root_head']
protected={}
for tag in ['proposition','proof','equation']:
 pattern=r'\\begin\{'+tag+r'\}.*?\\end\{'+tag+r'\}'
 blocks=lambda root:[x for p in sorted(root.rglob('*.tex')) for x in re.findall(pattern,p.read_text(encoding='utf-8'),re.S)]
 assert blocks(P)==blocks(OLD),tag
 protected[tag]=len(blocks(P))
native=read(R/'experiments/dsn_native_confirmation_20261102/confirmation/FINAL_REPORT/PAPER_DATA.json')
assert native['status']=='PASS_COMPLETE_NEW8_CONFIRMATION_REPORT' and native['trials']==32 and native['independent_speakers']==8
assert native['checked_original_steps']==564 and native['original_task_equal_all_trials']
nt=(P/'sections/05_native_retention.tex').read_text(encoding='utf-8');main=(P/'main.tex').read_text(encoding='utf-8')
for policy,v in native['policies'].items():
 for token in [f"{v['credit_audio_s']:.3f}",f"{v['per_run_D99']['median_seconds']:.3f}",f"{v['J_per_offered_audio_s']:.3f}",f"{v['D2_C8_passes']}/16"]:
  assert token in nt,(policy,token)
 assert f"{v['duration_weighted_coverage_percent']:.1f}\\%" in main
ci=native['bootstrap']['intervals']['duration_weighted_ratio_gain_pp']
for token in [f"{ci['point_estimate']:.1f}",f"[{ci['lower95']:.1f}, {ci['upper95']:.1f}]"]:
 assert token in main and token in nt
assert all(x['paired_gain_pp']>0 for x in native['source_pairs']) and len(native['source_pairs'])==8
cost=read(R/'experiments/dsn_continuity_cost_20261102/cost/FINAL_AGGREGATE/PAPER_DATA.json')
ct=(P/'sections/05_protocol_cost.tex').read_text(encoding='utf-8')
for family,role in [('WAL.complete_fact_commit','owner'),('IO.actual_os_fsync','owner'),('SUP.complete_consumer_apply','supervisor_consumer')]:
 rows=[x for x in cost['coarse_table'] if x['phase']=='nn' and x['family']==family and x['role']==role]
 assert len(rows)==4
 lo=min(x['observed_run_mean_wall_ms_min'] for x in rows);hi=max(x['observed_run_mean_wall_ms_max'] for x in rows)
 assert f'{lo:.2f}--{hi:.2f}' in ct
fig=E/'figures/EXPORT_v2';fs=read(fig/'SUMMARY.json');assert fs['new_model_calls']==fs['raw_service_readers']==0
for name in ['timely_full_interval_case','coordination_protocol','core_interaction','native_content']:
 assert sha(P/'figures'/(name+'.pdf'))==sha(fig/(name+'.pdf'))
 assert not fitz.open(P/'figures'/(name+'.pdf'))[0].get_images(),'Raster figure embedded'
fq={x['name']:x for x in fs['figures']}
assert fq['native_content']['details']['rows']==read(R/'experiments/dsn_native_confirmation_20261102/figures/INPUTS_v11.json')['rows']
assert fq['core_interaction']['details']['core_totals']==read(R/'experiments/dsn_story_revision_20261031/FIGURES_v3/MAIN_EFFECT_NUMERIC_VALUES.json')['core']
assert fq['source8_paired_effects']['details']['overall_speaker_paired_CI']==ci
assert fq['source8_paired_effects']['details']['individual_points_not_CI']
abstract=main.split('\\begin{abstract}',1)[1].split('\\end{abstract}',1)[0]
words_space=len(abstract.split());words_token=len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",abstract))
assert words_space<=150 and words_token<=150
doc=fitz.open(P/'main.pdf');texts=[p.get_text() for p in doc];assert len(doc)==12 and texts[-1].lstrip().startswith('REFERENCES')
assert not any(t.lstrip().startswith('REFERENCES') for t in texts[:-1]);assert 'AI TOOL USAGE' in texts[-2]
assert all(tuple(p.rect)==(0,0,612,792) for p in doc)
bib=(P/'main.bbl').read_text(encoding='utf-8');keys=re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',bib)
assert len(keys)==len(set(keys))==31
assert 'arXiv:2601.21337' in bib and '611--626' in bib
alltex='\n'.join(p.read_text(encoding='utf-8') for p in P.rglob('*.tex'))
for token in ['zhouz4884','LENOVO','VLA_QWEN','github.com/zhou']:
 assert token.lower() not in (alltex+'\n'.join(texts)).lower()
for token in ['Overfull','undefined references','multiply defined','LaTeX Error']:
 assert token not in (P/'main.log').read_text(errors='replace'),token
fontdata=subprocess.check_output([shutil.which('pdffonts'),str(P/'main.pdf')],text=True)
fontlines=[l for l in fontdata.splitlines()[2:] if l.strip()];assert fontlines and all(l.split()[-5]=='yes' for l in fontlines)
pdf_sha=sha(P/'main.pdf');out=E/'paper_qa'/('render_'+pdf_sha[:12]);out.mkdir(exist_ok=True);images=[]
for i,p in enumerate(doc):
 name=f'page_{i+1:02}.png';p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(out/name)
 p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),colorspace=fitz.csGRAY,alpha=False).save(out/(f'page_{i+1:02}_gray.png'))
 images.append(dict(page=i+1,color_sha256=sha(out/name),grayscale_sha256=sha(out/(f'page_{i+1:02}_gray.png'))))
record=dict(gate='PASS_FROZEN_EVIDENCE_NUMERICS_ANONYMITY_FONTS_AND_11_PLUS_1_LAYOUT',pdf_sha256=pdf_sha,pages=12,technical_pages=11,reference_pages=1,references=31,abstract_words_whitespace=words_space,abstract_words_alphanumeric=words_token,all_frozen_v12_files_preserved=len(b['frozen_v12_files']),all_frozen_v11_evidence_files_preserved=b['frozen_v11_verified_files'],legacy_dirty_HEAD_preserved=True,unchanged_formal_blocks=protected,independent_speakers=8,trials=32,selected_transitions=564,paired_CI=ci,all_eight_gains_positive=True,figure_source_commit=fs['source_commit'],figure_numeric_values_unchanged=True,new_GPU_runs=0,new_model_calls=0,embedded_font_records=len(fontlines),render_directory=str(out),rendered_pages=images,visual_review='PENDING_INDEPENDENT_AND_ROOT_INSPECTION')
put(E/'paper_qa/FINAL_QA.json',record);(E/'paper_qa/PDFFONTS.txt').write_text(fontdata,encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ['rendered_pages','paired_CI']}))
