"""Explicit deployment declaration for equivalent native/light renderers.

Preparing the declaration is a trusted CPU build step. Selected backend is
startup metadata; the same allowed-program contract must exist before the
precrash WAL is created. Old WAL contracts are not upgraded by this module.
"""
import importlib.metadata,json,platform,unicodedata
from pathlib import Path
from .light_render import file_sha,canonical_sha,FUNCTIONS,FIXED_OPERATIONS
from .startup_overlap import require_loaded_renderer_match


def eos_from_assets(model):
    value=json.loads((Path(model)/'generation_config.json').read_text())['eos_token_id']
    ids=[value] if type(value) is int else value
    if not isinstance(ids,list) or not ids or any(type(v) is not int or v<0 for v in ids):
        raise ValueError('unsupported generation EOS declaration')
    return ids


def prepare_use(bundle,comparison,model):
    """Inspect actual completed CPU proof files and native EOS before approval."""
    bundle=Path(bundle);comparison=Path(comparison)
    d=json.loads((bundle/'descriptor.json').read_text());proof=json.loads((comparison/'RESULT.json').read_text())
    if proof['gate']!='GO_CPU_COMPONENT_CONFORMANCE_NOT_SERVING_RTO' or proof['mismatched_fields']:
        raise ValueError('component conformance gate did not pass')
    freeze=json.loads((comparison/'FREEZE.json').read_text())
    for mode in ['native','light','negative']:
        parent=comparison.parent/mode
        if file_sha(parent/'RESULT.json')!=freeze['input_sha256'][mode]:raise ValueError('conformance proof input changed')
        f=json.loads((parent/'FREEZE.json').read_text())
        if f['descriptor_sha256']!=file_sha(bundle/'descriptor.json'):raise ValueError('proof belongs to another program')
        if f['source_commit']!=proof['source_commit']:raise ValueError('conformance source mismatch')
    from transformers import GenerationConfig
    native_eos=GenerationConfig.from_pretrained(model,local_files_only=True).eos_token_id
    native_eos=[native_eos] if type(native_eos) is int else native_eos
    if native_eos!=eos_from_assets(model):raise ValueError('native/config EOS mismatch')
    return dict(schema='verified-owner-render-program-use-v1',descriptor_sha256=file_sha(bundle/'descriptor.json'),
        conformance_result_sha256=file_sha(comparison/'RESULT.json'),conformance_source_commit=proof['source_commit'],
        native_reference_contract_sha256=canonical_sha(d['native_reference_contract']),
        native_generation_eos_ids=native_eos,integration_module_sha256=file_sha(__file__),
        allowed_backends=['native','light'],scope='trusted prepared program; explicit shared new WAL contract; not a stored text cache or model-truth proof')


def verify_use(bundle,expected_descriptor_sha,manifest,expected_manifest_sha,native_contract,model):
    """No framework imports and no output publication in this validation."""
    bundle=Path(bundle)
    if file_sha(manifest)!=expected_manifest_sha or file_sha(bundle/'descriptor.json')!=expected_descriptor_sha:
        raise ValueError('owner-render deployment manifest/program changed')
    u=json.loads(Path(manifest).read_text());d=json.loads((bundle/'descriptor.json').read_text())
    if u['schema']!='verified-owner-render-program-use-v1' or u['allowed_backends']!=['native','light']:
        raise ValueError('unsupported renderer allowlist')
    if u['integration_module_sha256']!=file_sha(__file__):raise ValueError('renderer integration implementation changed')
    if u['descriptor_sha256']!=expected_descriptor_sha or u['native_reference_contract_sha256']!=canonical_sha(native_contract):
        raise ValueError('renderer reference/program mismatch')
    if d['native_reference_contract']!=native_contract:raise ValueError('wrong native reference')
    if d['fixed_operations']!=FIXED_OPERATIONS or d['encode_special_tokens'] is not False or tuple(d['parser_functions'])!=FUNCTIONS:
        raise ValueError('unsupported rendering operations')
    if d['python_version']!=platform.python_version() or d['unicode_version']!=unicodedata.unidata_version:
        raise ValueError('renderer interpreter mismatch')
    for name,v in d['packages'].items():
        if importlib.metadata.version(name)!=v:raise ValueError('renderer dependency version changed')
    for r in d['dependency_files']:
        if file_sha(r['path'])!=r['sha256']:raise ValueError('renderer dependency file changed')
    if file_sha(Path(__file__).with_name('light_render.py'))!=d['light_module_sha256']:
        raise ValueError('light implementation changed')
    program=bundle/d['program_file']
    if not program.resolve().is_relative_to(bundle.resolve()) or file_sha(program)!=d['program_sha256']:
        raise ValueError('compiled tokenizer program changed')
    if u['native_generation_eos_ids']!=eos_from_assets(model):raise ValueError('renderer EOS changed')
    return dict(schema=u['schema'],descriptor_sha256=expected_descriptor_sha,use_manifest_sha256=expected_manifest_sha,
        conformance_result_sha256=u['conformance_result_sha256'],native_backend_sha256=d['native_default_backend_sha256'],
        program_sha256=d['program_sha256'],light_module_sha256=d['light_module_sha256'],
        integration_module_sha256=u['integration_module_sha256'],allowed_backends=u['allowed_backends'])


def check_native_program_context(declared,context):
    reference={k:v for k,v in declared.items() if k!='owner_render_program'}
    require_loaded_renderer_match(reference,context.contract)
    program=declared.get('owner_render_program')
    if program:
        context.processor.tokenizer.encode('')
        backend=context.processor.tokenizer.backend_tokenizer
        if canonical_sha(json.loads(backend.to_str()))!=program['native_backend_sha256'] or backend.encode_special_tokens is not False:
            raise ValueError('actual native tokenizer differs from prepared program')
