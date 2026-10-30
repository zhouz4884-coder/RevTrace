"""Close only the completed research/paper scope, preserving historical records."""
import datetime
import hashlib
import json
from pathlib import Path

T = Path(__file__).resolve().parent
R = T.parents[1]
F = R / 'experiments/dsn_native_resilience_20261030'
P = R / 'Paper_DSN/revisions/20261030_dsn2027_release_v1'

def read(path):
    return json.loads(path.read_bytes())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

execution = read(F/'FINAL_EXECUTION_AUDIT_GATE_v1.json')
release = read(T/'FINAL_RELEASE_RECORD_20261030_v1.json')
assert execution['status'] == 'COMPLETE_FROZEN_REFERENCE_AND_ALL36_ACTUAL_RUNS_AND_INDEPENDENT_AUDITS'
assert execution['NN_source_commit'] == '4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47'
assert execution['complete_scope'] == dict(continuous_original=875, restored_edges=875,
    short_actual_trials=28, sustained_actual_trials=8, selected_original_C_U_transitions=3976)
assert execution['NN_queue_closed'] and execution['machine_CURRENT_restored_to_NN']
for item in execution['gates'].values():
    data = Path(item['path']).read_bytes()
    assert sha(data) == item['sha256']
    actual = json.loads(data)
    assert actual.get('status', actual.get('gate')) == item['status']
assert execution['scientific_decisions']['long_realtime_quality'] == 'NO_GO_LONG_REALTIME_QUALITY'
assert release['gate'] == 'PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
assert release['technical_pagination']['technical_pages'] == 11
assert release['technical_pagination']['references_start_page'] == 12
assert release['pdf_sha256'] == sha((P/'main.pdf').read_bytes())
assert release['archive_sha256'] == sha((R/release['archive']).read_bytes())
assert release['submission_performed'] is False

source_table = F/'FIGURE_TABLE_FORMAL36_v5_results/reliability_table.tex'
paper_table = P/'tables/native_reliability.tex'
expected = source_table.read_bytes().replace(b'Illegal / done', b'Illegal; done').replace(b'0 / 2/2', b'0; 2/2')
assert paper_table.read_bytes() == expected
binding = dict(scope='Pure manuscript separator typography; all numeric table values unchanged.',
    source=source_table.relative_to(R).as_posix(), source_sha256=sha(source_table.read_bytes()),
    target=paper_table.relative_to(R).as_posix(), target_sha256=sha(paper_table.read_bytes()),
    replacements=[['Illegal / done', 'Illegal; done'], ['0 / 2/2', '0; 2/2']],
    NN_source=execution['NN_source_commit'], actual_series_export_source=execution['analysis_sources']['actual_B_export'],
    final_artifact_plot_source='78072870802aab8196e42ff952b1dab1a24eca04')
asset_record = F/'PAPER_ASSET_BINDINGS_v1.json'
assert not asset_record.exists()
write(asset_record, binding)

backup = F/'ACTIVE_STATE_BEFORE_FINAL_20261030.json'
assert not backup.exists()
backup.write_bytes((F/'ACTIVE_STATE.json').read_bytes())
write(F/'ACTIVE_STATE.json', dict(
    schema='revtrace-complete-research-and-paper-index-v2',
    status='COMPLETE_DECLARED_RESEARCH_AND_PAPER_RELEASE',
    updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    execution_gate='FINAL_EXECUTION_AUDIT_GATE_v1.json',
    execution_gate_sha256=sha((F/'FINAL_EXECUTION_AUDIT_GATE_v1.json').read_bytes()),
    NN_source_commit=execution['NN_source_commit'], NN_manifest_sha256=execution['NN_source_manifest_sha256'],
    environment_sha256=execution['environment_sha256'], analysis_sources=execution['analysis_sources'],
    complete_scope=execution['complete_scope'], decisions=execution['scientific_decisions'],
    NN_queue_closed=True, remaining_declared_experiments=[],
    paper_release=P.relative_to(R).as_posix(), paper_QA_gate=release['gate'],
    paper_pdf_sha256=release['pdf_sha256'], paper_archive_sha256=release['archive_sha256'],
    report='../dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT_20261030.zh.md',
    publication_stage='dsn2027_resilience_complete_release_v1',
    publication_protocol='The final publisher requires exact Git blobs and matching remote main before reporting delivery success; archive HEAD is not the NN source.',
    raw_results='Designated8TB only; bounded evidence is the Git publication scope.',
    historical_state=backup.name, conference_submission_performed=False))
write(R/'experiments/LATEST_RESEARCH.json', dict(
    date='2026-10-30', status='COMPLETE_DECLARED_RESEARCH_AND_PAPER_RELEASE',
    state='dsn_native_resilience_20261030/ACTIVE_STATE.json',
    report='dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT_20261030.zh.md',
    paper=P.relative_to(R).as_posix()+'/main.pdf',
    paper_QA_record='dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261030_v1.json',
    actual_NN_source=execution['NN_source_commit'],
    new_formal_trials=36, original_selected_transitions=3976,
    decisions=execution['scientific_decisions'],
    previous_completed_report='dsn_manuscript_update_20261028/FINAL_RESEARCH_REPORT.zh.md',
    previous_complete_paper='Paper_DSN/revisions/20261029_dsn2027_release_v1/main.pdf',
    remaining_declared_experiments=[], conference_submission_performed=False))
print(json.dumps(dict(status='PASS_COMPLETED_GATES_AND_FINAL_RELEASE_IDENTITIES',
    NN_source=execution['NN_source_commit'], formal_trials=36,
    pdf_sha256=release['pdf_sha256'], archive_sha256=release['archive_sha256']), indent=2))
