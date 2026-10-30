"""Read-only index of all 28 already computed trial summaries.

This copies existing per-trial results and uses frozen e94 aggregation helpers.
It is neither a raw-event recount, a formal36 analysis launch, nor a neural run.
"""
from __future__ import annotations
import csv
import datetime
import hashlib
import importlib.util
import json
import pathlib
import platform
import sys

sys.dont_write_bytecode = True
F = pathlib.Path(__file__).resolve().parents[1]
R = F.parents[1]
SOURCE = F/'figure_tools_source_v2'
COMMIT = 'e94bf689d672d72d0f81489ee145f37b59cb4357'
RAW = F/'FORMAL_SHORT28_V1_RESULTS_v1'
PLAN = F/'FORMAL_SHORT28_v1_FROZEN.json'
OUT = F/'SHORT28_READONLY_METADATA_INDEX_v1'


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def put(path, value):
    if path.exists(): raise ValueError('do not overwrite metadata evidence')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


if OUT.exists(): raise ValueError('new read-only index output required')
plan, campaign = read(PLAN), read(RAW/'SUMMARY.json')
if (plan['expected_cells'] != 28 or campaign['completed_cells'] != 28
        or campaign['planned_cells'] != 28
        or campaign['status'] != 'PASS_ALL_FROZEN_FORMAL_TRIALS_AND_COMPLETE_TASK_REFERENCE'):
    raise ValueError('complete short28 group required; no prefix table')
spec = importlib.util.spec_from_file_location('metadata_explicit_preflight', R/'experiments/repository_identity_20261027/preflight.py')
preflight = importlib.util.module_from_spec(spec); spec.loader.exec_module(preflight)
manifest = F/'packages/FIGURE_TOOLS_SOURCE_v2.json'
identity = preflight.check(SOURCE, manifest)
if identity['code_commit'] != COMMIT: raise ValueError('wrong frozen helper commit')
sys.path.insert(0, str(SOURCE))
import render_evidence as helper
if pathlib.Path(helper.__file__).resolve().parent != SOURCE.resolve():
    raise ValueError('wrong aggregation helper module')
campaign_cells = {row['cell_id']: row for row in campaign['cells']}
if set(campaign_cells) != {row['cell_id'] for row in plan['cells']}:
    raise ValueError('complete exact short28 ID set differs')
inputs = [PLAN, RAW/'SUMMARY.json', RAW/'COLLECTION_MANIFEST.json']
rows, bindings = [], []
for cell in plan['cells']:
    folder = RAW/'cells'/cell['cell_id']
    frozen_config = F/'formal_short28_v1_configs'/(cell['cell_id']+'.json')
    config, metrics, record = (read(folder/name) for name in ('CONFIG.json', 'SUMMARY.json', 'RUN_RECORD.json'))
    echo = sha(folder/'CONFIG.json')
    binding = helper.verify_config_binding(config, dict(raw_config_sha256=echo), cell, frozen_config)
    if (record['code_commit'] != plan['source_commit']
            or record['frozen_config_sha256'] != echo
            or metrics['primary']['raw_inputs']['config_sha256'] != echo
            or campaign_cells[cell['cell_id']]['frozen_input_sha256'] != cell['config_sha256']
            or campaign_cells[cell['cell_id']]['runtime_config_echo_sha256'] != echo
            or sha(folder/'SUMMARY.json') != campaign_cells[cell['cell_id']]['summary_sha256']):
        raise ValueError('original/echo/summary provenance mismatch')
    cohort = 'short_regression' if cell.get('tier') == 'fixed_prior_source_regression' else 'short_main'
    trial = dict(config=config, metrics=metrics, semantic={}, folder=folder,
        item=dict(cohort=cohort, condition=cell['fault_kind']), config_binding=binding)
    row = helper.trial_row(trial)
    row['precomputed_content'] = metrics['content']
    row['interpretation_scope'] = 'Copies existing complete-group metrics. No raw event or independent semantic recount performed here.'
    rows.append(row)
    bindings.append(dict(cell_id=cell['cell_id'], **binding, summary_sha256=sha(folder/'SUMMARY.json')))
    inputs.extend([frozen_config, folder/'CONFIG.json', folder/'SUMMARY.json', folder/'RUN_RECORD.json'])
if len(rows) != 28 or sum(r['cohort']=='short_main' for r in rows) != 24 or sum(r['cohort']=='short_regression' for r in rows) != 4:
    raise ValueError('main24/regression4 scope differs')
groups = helper.aggregate(rows)
OUT.mkdir()
put(OUT/'CONFIG.json', dict(experiment_id='SC_READONLY_COMPLETE_SHORT28_METADATA_INDEX_V1',
    analysis_phase='index_of_precomputed_metrics_not_raw_recount_or_formal36',
    frozen_helper_source_commit=COMMIT, materialization_script_sha256=sha(pathlib.Path(__file__)),
    input_plan=str(PLAN.resolve()), input_plan_sha256=sha(PLAN),
    complete_short_scope=28, expected_final_scope=36, final_scope_available=False,
    no_neural_calls=True, global_CURRENT_changed=False))
put(OUT/'ENVIRONMENT.json', dict(python=sys.version, platform=platform.platform(), no_model_imports=True))
put(OUT/'EXPLICIT_HELPER_SOURCE_IDENTITY.json', identity)
put(OUT/'ALL28_MACHINE_TABLE.json', rows)
put(OUT/'MAIN24_CONDITION_ARM_AGGREGATES.json', groups)
put(OUT/'REGRESSION4.json', [r for r in rows if r['cohort']=='short_regression'])
put(OUT/'INPUT_BINDINGS.json', bindings)
put(OUT/'INPUT_MANIFEST.json', [dict(path=str(p.resolve()), sha256=sha(p)) for p in sorted(set(inputs))])
with (OUT/'ALL28_MACHINE_TABLE.csv').open('w', encoding='utf8', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows({k: json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)
post = preflight.check(SOURCE, manifest)
put(OUT/'POST_EXPLICIT_HELPER_SOURCE_IDENTITY.json', post)
summary = dict(status='COMPLETE_SHORT28_PRECOMPUTED_METADATA_INDEX_ONLY',
    complete_short_cells=28, main_cells=24, regression_cells=4,
    helper_source_commit=COMMIT, materialization_script_sha256=sha(pathlib.Path(__file__)),
    source_manifest_sha256=sha(manifest), original_plan_sha256=sha(PLAN),
    illegal_install_counts='UNKNOWN_PENDING_INDEPENDENT_ACTUAL_TRACE_AUDIT',
    legal_progress_wrong_rejection_counts='UNKNOWN_PENDING_INDEPENDENT_WITNESS_AUDIT',
    final_formal36_analysis='NOT_STARTED_PENDING_COMPLETE_SUSTAINED8_AND_INDEPENDENT_AUDIT',
    source_preflight=identity['gate'], post_source_preflight=post['gate'],
    newly_executed_model_calls=0, raw_event_recount=False, global_CURRENT_changed=False,
    no_recovery_fault_conditions_NA=['none','duplicate_late'],
    range_scope='Two fresh trials per main condition/arm; ranges are not confidence intervals.',
    output_sha256={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()})
put(OUT/'SUMMARY.json', summary)
put(OUT/'RUN_RECORD.json', dict(config=str((OUT/'CONFIG.json').resolve()), config_sha256=sha(OUT/'CONFIG.json'),
    environment_record=str((OUT/'ENVIRONMENT.json').resolve()), environment_sha256=sha(OUT/'ENVIRONMENT.json'),
    code_commit=COMMIT, wrapper_source_status='Bounded read-only materialization wrapper SHA recorded separately; not represented as part of helper commit.',
    wrapper_sha256=sha(pathlib.Path(__file__)),
    recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    raw_result_location=plan['raw_result_location'],
    aggregate_summary_location=str((OUT/'SUMMARY.json').resolve()),
    gate_decision_location='NO_FORMAL36_OR_RAW_RECOUNT_GATE_CLAIMED'))
print(json.dumps({k:v for k,v in summary.items() if k != 'output_sha256'},indent=2))
