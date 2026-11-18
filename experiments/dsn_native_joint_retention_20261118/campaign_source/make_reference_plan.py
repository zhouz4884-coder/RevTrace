"""Freeze the short-reference plan only after metadata/audio selection; no NN."""
from __future__ import annotations
import argparse, copy,pathlib
from ref_common import NN4F,PARENT_RUNTIME, need, read, put, sha, inventory, sources_from_receipt,verify_source

def main():
    p = argparse.ArgumentParser()
    for name in ('manifest','template', 'selection-receipt', 'environment', 'base-source', 'base-manifest',
                 'asset-byte-gate', 'gpu-uuid', 'cache-root', 'raw-out', 'out'):
        p.add_argument('--'+name, required=True)
    p.add_argument('--gpu', type=int, choices=(0, 1), default=0)
    a = p.parse_args();generator=verify_source(pathlib.Path(__file__).parent,a.manifest);base=verify_source(a.base_source,a.base_manifest,NN4F);template = read(a.template); receipt = read(a.selection_receipt)
    sources = sources_from_receipt(receipt)
    settings = template['settings']; need(settings['source_commit'] in (PARENT_RUNTIME,NN4F), 'warmup template has unknown source')
    warm = copy.deepcopy(settings['warmup'])
    candidates = [s for s in settings['model_sources'] if s['source_id'] == warm['source_id']]
    need(len(candidates) == 1 and warm['original_reference_start_state']['frontier'] == 24000,
         'original fixed neural warmup is missing/changed')
    env = read(a.environment); need('packages' in env and 'executable' in env,
                                  'frozen actual environment needs interpreter and package versions')
    inputs = inventory([a.manifest,a.template, a.selection_receipt, a.environment, a.base_manifest, a.asset_byte_gate])
    plan = dict(experiment_id='REVTRACE-V16-EXISTING-FIRST4-NEW-RUNTIME-REFERENCE-V2',generator=generator,actual_NN=base,
        actual_NN_source_commit=NN4F, base_source=a.base_source, base_manifest=a.base_manifest,
        selection_receipt=a.selection_receipt, selection_receipt_sha256=sha(a.selection_receipt),
        template=a.template, template_sha256=sha(a.template), environment_record=a.environment,
        environment_sha256=sha(a.environment), environment_python=env['executable'],
        asset_byte_gate=a.asset_byte_gate, asset_byte_gate_sha256=sha(a.asset_byte_gate),
        inputs=inputs, sources=sources, expected_sources=len(sources),
        expected_original_steps=sum(len(range(8000, s['frames'], 8000))+1 for s in sources),
        backend=copy.deepcopy(settings['backend']), warmup=warm, warmup_source=copy.deepcopy(candidates[0]),
        gpu=a.gpu, gpu_uuid=a.gpu_uuid, cache_root=a.cache_root, raw_result_location=a.raw_out,
        runtime_environment={'PYTORCH_CUDA_ALLOC_CONF': 'expandable_segments:True'},
        original_seed=1701, original_FP32=True, original_TF32=False,
        continuous_no_between_step_restore=True, restored_repeats_per_edge=2,
        first_failure_controls=dict(same_input_adapter_repeats=2, original_continuous_prefix_repeats=1,
                                    first_failed_boundary_per_source=True),
        source_replacement_after_reference_forbidden=True,
        on_reference_exception='preserve pending input, run first-failure controls, stop remaining sources',
        reference_only=True, actual_serving_runs=0,
        source_marker_policy='actualv3 runtime in newly executed continuous and restored paths; no old4f/BDFA result relabel',
        resource_closure='Root externally verifies process exit/startticks and CUDA empty before service')
    put(a.out, plan)

if __name__ == '__main__': main()
