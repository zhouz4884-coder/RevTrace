"""Record completed encoder decision and method-frozen independent-source phase."""
import datetime, json
from pathlib import Path

T = Path(__file__).resolve().parent
R = T.parents[1]
stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
path = T / 'ACTIVE_STATE.json'
x = json.loads(path.read_text(encoding='utf8'))
x.update(
    status='NATIVE19_AND_ENCODER13_COMPLETE_FINAL_METHOD_FROZEN_NEW_SOURCE_CONFIRMATION_PREPARING',
    updated_utc=stamp,
    gpu_current=None,
    gpu_next='Metadata-first four speaker-disjoint sources, original-full reference only after acquisition; then final unchanged bdfa 16-cell paired service confirmation. No further implementation branches.',
    paper_status='Complete core plus native method/evaluation drafted; 10 technical pages plus references compile. Final independent-source results, argument alignment, clean release and all-page QA pending.',
)
x['encoder_component13'] = {
    'status': 'COMPLETE_FIDELITY_PASS_EAGER_COST_STOP',
    'actual_source_commit': '316b102ac591f3440dcefe4f49f62afa1fd010d5',
    'calls': 13,
    'four_equal_original_encoder_outputs_and_full_C_U_states': True,
    'eager_expected_net_seconds': -0.30507695814594626,
    'component_only_not_serving': True,
    'resources_released': True,
    'report': '../dsn_streamcorrect_encoder_profile_20261029/RESULTS_REPORT.zh.md',
}
x['final_native_method'] = {
    'source_commit': 'bdfa3b1307d267a5a4caf6484e1ad465c39a592e',
    'freeze': '../dsn_streamcorrect_stage_handoff_20261029/FINAL_NATIVE_METHOD_FREEZE_v1.json',
    'freeze_sha256': 'fb6a1f57aba24b4300d84b9c30cfc8828bcb86c0fd011db92d4023ef1519364d',
    'before_new_source_selection': True,
    'no_additional_implementation_search': True,
}
x['final_independent_sources'] = {
    'status': 'METADATA_FROZEN_PUBLIC_RANGE_ACQUISITION_IN_PROGRESS_NO_NEW_NN_YET',
    'metadata_receipt': '../dsn_streamcorrect_independent_20261029/METADATA_SELECTION_v1_FROZEN.json',
    'metadata_sha256': '4bf6249f275cbe5c43099c5283166484e1c6aee3485be8968da08e1d50a3b7ccd',
    'speakers': ['S0908', 'S0916', 'S0913', 'S0905'],
    'selection': 'Fixed metadata-only seed2026102931; 8-9s WAV-size band; no acoustic or neural outcome selection.',
    'planned_service_cells': 16,
    'timed_service_results_exist': False,
}
path.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
p = R / 'experiments/LATEST_RESEARCH.json'
y = json.loads(p.read_text(encoding='utf8'))
y.update(status=x['status'], updated_utc=stamp, scope='Core36+joint24+midpoint12+originalnative14 complete; native3-arm pilot+16 old-source service confirmation complete; actual encoder13 fidelity passes but eager net cost negative, STOP. Preferred full-call bdfa method frozen before metadata-only selection of four new speakers; acquisition/reference/final16 independent service and full paper release pending.')
p.write_text(json.dumps(y, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'status': x['status'], 'updated_utc': stamp}))
