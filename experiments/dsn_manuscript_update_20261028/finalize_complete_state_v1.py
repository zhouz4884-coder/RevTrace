"""Close mutable status indexes only after research and complete manuscript release pass."""
import datetime,hashlib,json,subprocess
from pathlib import Path
T=Path(__file__).resolve().parent;R=T.parents[1];I=T.parent/'dsn_streamcorrect_independent_20261029';H=T.parent/'dsn_streamcorrect_stage_handoff_20261029'
def read(p):return json.loads(p.read_bytes())
def put(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
release=read(T/'FINAL_RELEASE_RECORD_v1.json');assert release['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
primary=read(I/'FINAL_PRIMARY_RESULTS_v2/SUMMARY.json');content=read(I/'FINAL_CONTENT_RESULTS_v2/SUMMARY.json')
assert primary['all_original_full_C_ID_state_quality_preserved'] and primary['cells']==16
assert read(I/'NATURAL_EVENT_ROOT_REPEAT_RESULTS_v1/GATE.json')['compatible_cross_Root_actual_whole_view_preservation_observations']==1
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f'
x=read(T/'ACTIVE_STATE.json');x.update(status='COMPLETE_RESEARCH_AND_DSN2027_MANUSCRIPT_RELEASE',updated_utc=stamp,gpu_current=None,gpu_next=None,paper_new=release['release'],paper_working_input='Paper_DSN/revisions/20261028_dsn2027_progress',paper_status='Complete selected manuscript,10technical+1references;139wordabstract;all11pages visually inspected;fonts/citations/source/anonymity checks pass;sourceZIP verified.',final_report='FINAL_RESEARCH_REPORT.zh.md',pending_required_work=[],current_launch_pointer_scope='Last actual CPU natural-event source dd2; final neural method remains bdfa. Execution sources remain distinct from the GitHub archive HEAD.')
x['final_independent_sources'].update(status='COMPLETE_ALL16_STRICT_ORIGINAL_TASK_PAIRED_RECOUNTS_AND_NATURAL_EVENTS_PASS',timed_service_results_exist=True,actual_completed_service_cells=16,offered_audio_seconds_per_arm=66.33975,frontiers_per_arm=136,all_full_original_start_end_C_ID_steps=272,credit_seconds={'conservative':37.0,'fullcall':66.33975},whole_D2_C8_pass={'conservative':'0/8','fullcall':'8/8'},same_actual_G_fulltext_supported_credit={'conservative':29.0,'fullcall':51.518125},service_energy_reduction_percent=11.134042263272569,positive_speaker_two_repeat_sums='4/4',positive_within_source_timing_pairs='8/8',unique_quality_CER='5/81 both arms',report='../dsn_streamcorrect_independent_20261029/FINAL_INDEPENDENT_RESULTS_v2.zh.md',natural_witnesses={'compatible_whole_view_and_inflight_preservation':1,'necessary_withdrawals':2,'independent_acoustic_withdrawal_patterns':1,'wrong_completed_full_results_never_installed':2},resources_released=True)
put(T/'ACTIVE_STATE.json',x)
y=read(R/'experiments/LATEST_RESEARCH.json');y.update(status=x['status'],updated_utc=stamp,scope='All original scopes, native implementation selection, encoder13 STOP, final speaker-disjoint16 and strict CPU analyses complete. Complete DSN manuscript release and all-page QA/sourceZIP complete. No experiment queue or required pending work.',paper=release['release']+'/main.pdf',report='dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT.zh.md')
put(R/'experiments/LATEST_RESEARCH.json',y)
p=I/'CURRENT_STATUS.json';old=read(p);backup=I/'CURRENT_ACQUISITION_STATUS_BEFORE_COMPLETE_RELEASE_v1.json'
assert not backup.exists();backup.write_bytes(p.read_bytes())
put(p,dict(status='COMPLETE_FINAL16_NEW_SPEAKER_SERVICE_STRICT_RECOUNTS_AND_NATURAL_WITNESSES',updated_utc=stamp,actual_neural_source_commit='bdfa3b1307d267a5a4caf6484e1ad465c39a592e',reference_generator_source_commit='66abab7b8ce668a1a1ddefb65f6115af45e99cec',analysis_source_commit='b473d9dc47c21d5cc7f88d7871f37497398895fb',natural_event_source_commit='dd2cb7e7816fcfd7d6be5194f8f883c98dba1f78',acquisition_source_commit=old['source_commit'],selection_source_commit=old['selection_source_commit'],acoustic_speakers=4,timing_pairs=8,serving_cells_completed=16,offline_reference_calls=68,complete_original_task_steps_checked=272,resources_released=True,pending_required_work=[],report='FINAL_INDEPENDENT_RESULTS_v2.zh.md',paper='../../'+release['release']+'/main.pdf',historical_acquisition_status=backup.name))
p=I/'FINAL_ANALYSIS_STATUS.json';z=read(p);z.update(status='COMPLETE_BOTH_FROZEN_INDEPENDENT_RECOUNTS_AND_ALL_NATURAL_EVENT_CHECKS',actual_service_recount_executed=True,pending_required_work=[],report='FINAL_INDEPENDENT_RESULTS_v2.zh.md');put(p,z)
p=H/'CURRENT_STATUS.json';z=read(p);z.update(status='COMPLETE_DEVELOPMENT_SELECTION_AND_CONFIRMATION_WITH_SEPARATE_NEW4_CONFIRMATION_COMPLETE',updated_utc=stamp,actual_serving_cells=19,current_campaign_completed=16,remote_resources_released=True,next_action='No further experiment queue; see complete DSN release and new4 final confirmation.',final_independent_family='../dsn_streamcorrect_independent_20261029',final_independent_completed_cells=16,paper='../../'+release['release']+'/main.pdf');put(p,z)
p=R/'Paper_DSN/revisions/20261028_dsn2027_progress/DRAFT_STATE.json';z=read(p)
assert hashlib.sha256((p.parent/'main.tex').read_bytes()).hexdigest()==z['main_baseline_sha256']
assert hashlib.sha256((p.parent/'main.pdf').read_bytes()).hexdigest()==z['pdf_baseline_sha256']
z.update(status='WORKING_INPUT_ARCHIVED_COMPLETE_RELEASE_AVAILABLE',updated_utc=stamp,pending=None,entrypoint='core_draft.tex',final_release=release['release'],final_pdf_sha256=release['pdf_sha256'],final_technical_pages=10,final_reference_pages=1,main_and_current='Working main.tex/main.pdf preserved as old baseline; Paper_DSN/CURRENT now selects the new clean release.',preliminary_pdf_scope='Historical working preview, not the final release PDF.')
put(p,z)
current="""# Current RevTrace DSN manuscript — 2026-10-29

- [Complete manuscript PDF](revisions/20261029_dsn2027_release_v1/main.pdf)
- [Main LaTeX source](revisions/20261029_dsn2027_release_v1/main.tex)
- [Audited source package](revisions/20261029_dsn2027_release_v1/RevTrace_DSN2027_anonymous_source_v1.zip)
- [Research decisions and final results](../experiments/dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT.zh.md)
- [Source, PDF, package and all-page QA record](../experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_v1.json)

Title: **RevTrace: Preserving Valid Progress across Trusted Feedback Revisions**

10 technical pages plus one references-only page; 139-word abstract; 19 cited references.
All eleven pages visually reviewed. All fonts embedded, no Type3, no undefined references or overfull boxes.
The package contains exactly the reachable manuscript sources, figures, selected bibliography, provenance and PDF; build logs, local QA files, audio and models are excluded.

Final new-speaker confirmation: four metadata-selected speakers, two fresh repeats per policy,16 actual service runs.
Complete original start/end states, correction selections and token IDs match at all272 Canonical transitions.
Whole-run D2/C8 passes: conservative0/8,full-call8/8. Original credit37.0→66.33975s per66.33975s offered.
Content support, accuracy and energy retain separate definitions; full offered credit is not a claim of entirely correct new text.

The20261008 revision is preserved. Actual experiment source commits are recorded separately from evidence-archive commits.
This is a complete research manuscript release; conference submission has not been performed.
"""
(R/'Paper_DSN/CURRENT.md').write_bytes(current.encode('utf8'))
print(json.dumps(dict(status=x['status'],paper=release['release'],pdf_sha256=release['pdf_sha256'],pending_required_work=[])))

