"""Publication QA: numeric bindings, venue pages, embedded fonts and rendering."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import fitz
E=Path(__file__).resolve().parents[1];R=E.parents[1]
paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v10';pdf=paper/'main.pdf'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=E/'cost/FINAL_AGGREGATE/PAPER_DATA.json';x=json.loads(data.read_bytes())
assert x['status']=='PASS_COMPLETE_CPU12_NN16_UNSUBTRACTED_COST_ACCOUNTING' and x['pair_selected_program_equal']
assert x['CPU_fresh_replays']==12 and x['NN_trials']==16 and x['off_on_pairs']==8
independent=E/'review/FINAL_COST_INDEPENDENT/GATE.json';ig=json.loads(independent.read_bytes())
assert ig['status']=='PASS_INDEPENDENT_COST_RECOUNT' and ig['completed_cells']==28 and ig['NN_off_on_pairs']==8
c4=E/'cost/FINAL_C4_CLOSURE/ROOT_ACTUAL_TRACE_RECHECK_CLOSURE.json';cg=json.loads(c4.read_bytes())
closure_summary=c4.parent/'SUMMARY.json';cs=json.loads(closure_summary.read_bytes())
assert cg['root_actual_trace_recheck_pending'] is False and cs['passed_cells']==16 and cs['failed_cells']==0
assert sha(closure_summary)==cg['closure_summary_sha256'] and sha(c4.parent/'GATE.json')==cg['closure_gate_sha256']
rows=[r for r in x['coarse_table'] if r['phase']=='nn']
specs=[('Durable full-state commit','WAL.complete_fact_commit','owner'),('Owner fsync','IO.actual_os_fsync','owner'),('Whole-view Consumer application','SUP.complete_consumer_apply','supervisor_consumer')]
tex=(paper/'sections/05_protocol_cost.tex').read_text(encoding='utf-8');bindings=[]
for title,label,role in specs:
    matches=[r for r in rows if r['family']==label and r['role']==role]
    assert len(matches)==4 and all(r['fresh_runs']==2 for r in matches)
    lo=min(r['observed_run_mean_wall_ms_min'] for r in matches);hi=max(r['observed_run_mean_wall_ms_max'] for r in matches)
    text=f'{lo:.2f}--{hi:.2f}';assert text in tex
    bindings.append(dict(operation=title,family=label,role=role,per_run_means=8,minimum_ms=lo,maximum_ms=hi,latex=text))
owners={(r['source_id'],r['policy'],r['family']):r for r in rows if r['role']=='owner'}
sync_bounds=[]
for sid,policy,_ in list(owners):
    w=owners[(sid,policy,'WAL.complete_fact_commit')];s=owners[(sid,policy,'IO.actual_os_fsync')]
    assert w['call_counts_by_run']==s['call_counts_by_run']=='17,17'
    sync_bounds.append(s['observed_run_mean_wall_ms_min']/w['observed_run_mean_wall_ms_max'])
assert min(sync_bounds)>.5,'most commit wall time would not be supported'
prior=R/'experiments/dsn_strengthening_20261031/PAIRED32_V2_RESULTS/SUMMARY.json'
prior_final=[r for r in json.loads(prior.read_bytes())['cells'] if r['version']=='final']
assert len(prior_final)==16 and sum(r['semantic']['checked_steps'] for r in prior_final)==272
assert all(r['semantic']['actual_NN_source_commit']=='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47' and r['semantic']['status']=='PASS_COMPLETE_SELECTED_TRACE_REFERENCE' for r in prior_final)
doc=fitz.open(pdf);assert len(doc)==12
texts=[p.get_text() for p in doc];assert texts[-1].lstrip().startswith('REFERENCES')
assert not any(t.lstrip().startswith('REFERENCES') for t in texts[:-1])
bib=(paper/'main.bbl').read_text(encoding='utf-8');citations=re.findall(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}',bib)
assert len(citations)==len(set(citations))==31
log=(paper/'main.log').read_text(errors='replace')
assert not any(s in log for s in ['Overfull','undefined references','multiply defined','LaTeX Error'])
alltex='\n'.join(p.read_text(encoding='utf-8') for p in paper.rglob('*.tex'))
for word in ['zhouz4884','LENOVO','VLA_QWEN','github.com/zhou']:
    assert word.lower() not in alltex.lower() and word.lower() not in '\n'.join(texts).lower()
assert 'Anonymous submission' in alltex
font_cmd=shutil.which('pdffonts');assert font_cmd
fonts=subprocess.check_output([font_cmd,str(pdf)],text=True)
font_lines=[line for line in fonts.splitlines()[2:] if line.strip()]
assert font_lines and all(line.split()[-5]=='yes' for line in font_lines)
out=E/'paper_qa'/('final_render_'+sha(pdf)[:12]);out.mkdir(exist_ok=True)
renders=[]
for i,p in enumerate(doc):
    target=out/f'page_{i+1:02d}.png';p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(target)
    renders.append(dict(page=i+1,path=target.relative_to(E).as_posix(),sha256=sha(target)))
gray=E/'paper_qa'/('grayscale_'+sha(pdf)[:12]);gray.mkdir(exist_ok=True)
for i,p in enumerate(doc):
    if p.get_images() or any(key in texts[i] for key in ['Fig. 1.','Fig. 2.','Fig. 3.','Fig. 4.']):
        p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),colorspace=fitz.csGRAY,alpha=False).save(gray/f'page_{i+1:02d}.png')
assert sha(R/'Paper_DSN/revisions/20261101_dsn2027_release_v9/main.pdf')=='cf3cd3556cf7637f970d3d18870beb71447c51d34eb6417c4e5ab30f41d12114'
record=dict(gate='PASS_NUMERIC_BINDINGS_ANONYMOUS_SOURCE_FONTS_AND_11_PLUS_1_LAYOUT',pdf_sha256=sha(pdf),
            pages=12,technical_pages=11,reference_pages=1,cited_references=31,embedded_font_records=len(font_lines),
            cost_data_sha256=sha(data),cost_independent_gate_sha256=sha(independent),actual_trace_closure_sha256=sha(c4),
            numeric_bindings=bindings,conservative_min_fsync_fraction_bound=min(sync_bounds),
            final_native_16_case_272_transition_binding_sha256=sha(prior),
            baseline_v9_preserved=True,rendered_pages=renders,visual_acceptance='PENDING_DIRECT_INSPECTION')
visual=E/'paper_qa/VISUAL_REVIEW_v10.json'
if visual.exists():
    v=json.loads(visual.read_bytes())
    assert v['pdf_sha256']==record['pdf_sha256'] and v['color_pages_inspected']==list(range(1,13)) and not v['issues_remaining']
    record.update(visual_acceptance=v['gate'],visual_review_sha256=sha(visual))
(E/'paper_qa/FINAL_QA.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
(E/'paper_qa/PDFFONTS.txt').write_bytes(fonts.encode())
print(json.dumps({k:v for k,v in record.items() if k not in {'numeric_bindings','rendered_pages'}}))
