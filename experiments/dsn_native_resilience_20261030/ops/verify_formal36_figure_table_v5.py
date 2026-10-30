"""Bounded final file/semantic/visual-QA record, no neural calls or plot edits."""
import datetime,hashlib,json,pathlib,re,subprocess,xml.etree.ElementTree as X
from pypdf import PdfReader
F=pathlib.Path(__file__).resolve().parents[1];OUT=F/'FIGURE_TABLE_FORMAL36_v5_results'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
audit=read(OUT/'FIGURE_TABLE_AUDIT.json'); rows=read(OUT/'ALL36_MACHINE_TABLE.json')
assert len(rows)==36 and sum(r['cohort']=='short_main' for r in rows)==24 and sum(r['cohort']=='short_regression' for r in rows)==4 and sum(r['cohort']=='sustained' for r in rows)==8
assert all(r['complete_original_task'] and r['illegal_installs']==0 and r['legal_progress_wrong_rejections']==0 for r in rows)
native=read(F/'NATIVE_WORK_RECOUNT_RESULTS_v1/results/SUMMARY.json')
strict=[]
for r in native['results']:
 for e in r['strict_recovery_clock_audits']:
  assert e['original_selected_strict_verified'] is True
  rr=e['original_selected_actual_rows'];assert len(rr)==1 and rr[0]['strict_verified'] is True
  assert rr[0]['model_end_minus_fault']>0 and rr[0]['consumer_observed_perf']==e['strict_first_actual_consume']['consumer_observed_perf']
  strict.append(dict(cell_id=r['cell_id'],model_end_minus_fault=rr[0]['model_end_minus_fault'],actual_certified_advance_samples=rr[0]['actual_certified_frontier']-rr[0]['prefault_actual_certified_frontier']))
assert len(strict)==16
same={}
for name in ['ALL36_MACHINE_TABLE.json','ALL36_MACHINE_TABLE.csv','SHORT24_AGGREGATES.json','reliability_table.tex','SUSTAINED8_MEMORY_DETAILS.json','SUSTAINED8_FRONTIER_AND_CLUSTER_DETAILS.json']:
 same[name]=len({sha(F/('FIGURE_TABLE_FORMAL36_v'+str(v)+'_results')/name) for v in (3,4,5)})==1
assert all(same.values())
svg=X.parse(OUT/'sustained_state_history.svg').getroot();ns={'s':'http://www.w3.org/2000/svg'}
sizes=[]
for element in svg.iter():
 if element.tag.rsplit('}',1)[-1] in ('text','tspan'):
  match=re.search(r'font-size:\s*([\d.]+)px',element.attrib.get('style',''))
  if match:sizes.append(float(match[1]))
assert sizes and min(sizes)==8.5 and len(svg.findall('.//s:image',ns))==0
pdf=PdfReader(OUT/'sustained_state_history.pdf');assert len(pdf.pages)==1
page=pdf.pages[0];dimensions=[float(page.mediabox.width),float(page.mediabox.height)]
assert dimensions==[518.4,216.0]
fonts=[]
for value in page['/Resources']['/Font'].values():
 obj=value.get_object();fonts.append(dict(subtype=str(obj['/Subtype']),basefont=str(obj.get('/BaseFont'))))
 assert obj['/Subtype']!='/Type3'
pdffonts=subprocess.check_output(['pdffonts',str(OUT/'sustained_state_history.pdf')],text=True)
assert 'Type 3' not in pdffonts and 'TrueType' in pdffonts
(F/'FIGURE_TABLE_FORMAL36_v5_PDFFONTS.txt').write_text(pdffonts,encoding='utf8')
positive={'D':[],'C':[]};hist=0;maxterminal=maxunpinned=maxaudit=0;maxwall=0.
for entry in read(F/'FIGURE_TABLE_FORMAL36_v5_INDEX.json')['trials']:
 if entry['cohort']!='sustained':continue
 folder=pathlib.Path(entry['bounded_dir'])
 for line in (folder/'frontiers.jsonl').read_text(encoding='utf8').splitlines():
  row=json.loads(line)
  for key in positive:
   assert row[key] is not None and .3<row[key]<1000;positive[key].append(row[key])
 for line in (folder/'history.jsonl').read_text(encoding='utf8').splitlines():
  row=json.loads(line);h=row['history'];i=h['inbox'];u=i['terminal']-i['pinned_terminals']
  assert 0<=u<=i['terminal_limit'] and all(0<=v<=h['history_limit'] for v in h['audit_retained'].values())
  maxterminal=max(maxterminal,i['terminal']);maxunpinned=max(maxunpinned,u);maxaudit=max(maxaudit,max(h['audit_retained'].values(),default=0));maxwall=max(maxwall,row['t_since_origin']);hist+=1
assert all(len(v)==3500 for v in positive.values())
result=dict(status='PASS_COMPLETE_FORMAL36_TABLE_AND_VECTOR_FIGURE_FILE_AND_VISUAL_QA',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 neural_source_commit='4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47',actual_series_export_source_commit='038ea6eb58a790fd11910ce8030604b5b1097705',
 actual_plot_source_commit='78072870802aab8196e42ff952b1dab1a24eca04',checked_formal_cells=36,checked_canonical_transitions=3976,
 scope='File/plot QA and binding to complete actual-trace audits; does not turn deadline/quality/energy failures into serving PASS.',
 independent_actual_trace_checker='c4dde9ea9c7abf80fae084bc2293e193262c71e6',strict_clock_auditor='359b049a4e26683dcfb38fb7a78ef41c4c235145',
 strict_original_chosen_rows=strict,strict_clock_scope='All16 actual chosen Consumer rows satisfy model_end>fault, newer journal sequence, non-replay and certified-frontier advance. Frozen runtime filter remains >=; qualifying call may already be in flight.',
 numerical_outputs_unchanged_v3_v4_v5=same,PNG_visual_review='Full final PNG inspected; four panels, units, legend clearance, log 2s/8s lines, wall-time drain tails and eight rug rows readable. Full four-panel figure remains artifact rather than a long-serving success claim.',
 PDF_dimensions_points=dimensions,PDF_Type3_fonts=False,PDF_fonts=fonts,SVG_editable_text_nodes=len(svg.findall('.//s:text',ns)),SVG_raster_images=0,SVG_actual_minimum_text_points=min(sizes),
 size_inches=[7.2,3.0],minimum_font_at_7p125_inch_width=8.5*7.125/7.2,
 sustained_frontier_observations={k:dict(count=len(v),min=min(v),max=max(v),nonpositive=0,missing=0) for k,v in positive.items()},
 history_observed_samples=hist,history_max_wall_seconds=maxwall,observed_terminal_peak=maxterminal,observed_unpinned_terminal_peak=maxunpinned,observed_individual_audit_retained_peak=maxaudit,
 history_scope='All8 original1Hz samples; terminal-pinned<=64 and each audit class<=64. Total terminal may exceed64. No sums of separate maxima or total-RSS-constant claim.',
 complete_sustained_D2_C8_passes=sum(r['original_D2_C8_pass'] for r in rows if r['cohort']=='sustained'),
 outputs={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()},new_model_calls=0,global_CURRENT_changed=False)
target=F/'FIGURE_TABLE_FORMAL36_v5_VISUAL_QA_GATE.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('outputs','strict_original_chosen_rows')},ensure_ascii=False,indent=2))
