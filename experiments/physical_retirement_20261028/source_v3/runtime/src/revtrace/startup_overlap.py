"""Identity-checked startup overlap. Selection/render/admission stay unchanged."""
from __future__ import annotations
import ast
from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
from pathlib import Path


SUFFIXES=('.json','.txt','.py','.tiktoken','.model')
REQUIRED_PACKAGE_FILES={'__init__.py','inference/qwen3_asr.py','inference/utils.py',
                        'core/transformers_backend/processing_qwen3_asr.py'}
PACKAGES=('torch','transformers','qwen-asr','tokenizers')


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def asset_inventory(model):
    return {p.name:file_hash(p) for p in sorted(Path(model).iterdir())
            if p.is_file() and p.suffix in SUFFIXES}


def python_inventory(package_root):
    root=Path(package_root).resolve()
    return {p.relative_to(root).as_posix():file_hash(p) for p in sorted(root.rglob('*.py')) if p.is_file()}


def package_root():
    spec=importlib.util.find_spec('qwen_asr')
    if spec is None or spec.origin is None:
        raise ValueError('installed qwen_asr location unavailable')
    return Path(spec.origin).resolve().parent


def function_source_hash(path,function):
    text=Path(path).read_text(encoding='utf8')
    nodes=[n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==function]
    if len(nodes)!=1:raise ValueError('missing or ambiguous native parser function')
    node=nodes[0];start=min([node.lineno]+[d.lineno for d in node.decorator_list])-1
    source=''.join(text.splitlines(keepends=True)[start:node.end_lineno])
    return hashlib.sha256(source.encode('utf8')).hexdigest()


@dataclass
class NativeRenderContext:
    processor: object
    parse: object
    contract: dict


def load_native_qwen_context(model,profile=None):
    with profile.span('trusted-render-library-imports') if profile else nullcontext():
        from transformers import AutoProcessor
        from qwen_asr import parse_asr_output
    with profile.span('first-render-processor-load') if profile else nullcontext():
        processor=AutoProcessor.from_pretrained(model,local_files_only=True)
    with profile.span('render-assets-and-implementation-identity') if profile else nullcontext():
        contract={'adapter':'qwen-text-rollback5-unfixed2-v1','assets':asset_inventory(model),
            'parse_source_sha256':hashlib.sha256(inspect.getsource(parse_asr_output).encode()).hexdigest(),
            'processor_source_sha256':file_hash(inspect.getfile(type(processor))),
            'tokenizers_version':importlib.metadata.version('tokenizers'),
            'published_text_encoding':'UTF-8 byte exact'}
    return NativeRenderContext(processor,parse_asr_output,contract)


def prepare_descriptor(model):
    """Trusted CPU preparation using real native imports and processor object."""
    context=load_native_qwen_context(model)
    root=package_root();files=python_inventory(root)
    if not REQUIRED_PACKAGE_FILES.issubset(files):
        raise ValueError('native package does not match inspected adapter layout')
    if function_source_hash(root/'inference/utils.py','parse_asr_output')!=context.contract['parse_source_sha256']:
        raise ValueError('AST/native source identities disagree')
    return dict(schema='qwen-trusted-render-startup-v1',inventory_scope='qwen-asr-all-python-v1',
        render_contract=context.contract,package_files=files,
        packages={name:importlib.metadata.version(name) for name in PACKAGES},
        preparation={'kind':'native-AutoProcessor-and-native-parser',
                     'processor_class':type(context.processor).__module__+'.'+type(context.processor).__qualname__,
                     'tokenizer_class':type(context.processor.tokenizer).__module__+'.'+type(context.processor.tokenizer).__qualname__})


def verify_prefrozen_renderer(model,descriptor_path,*,expected_descriptor_sha256,
                              root=None,version_lookup=importlib.metadata.version):
    """Stdlib metadata/file checks only, before either worker is started."""
    if len(expected_descriptor_sha256)!=64 or any(c not in '0123456789abcdef' for c in expected_descriptor_sha256):
        raise ValueError('frozen SHA256 required')
    if file_hash(descriptor_path)!=expected_descriptor_sha256:
        raise ValueError('renderer descriptor identity mismatch')
    d=json.loads(Path(descriptor_path).read_text(encoding='utf8'))
    if d.get('schema')!='qwen-trusted-render-startup-v1' or d.get('inventory_scope')!='qwen-asr-all-python-v1':
        raise ValueError('renderer descriptor schema/inventory scope mismatch')
    if set(d['packages'])!=set(PACKAGES):raise ValueError('incomplete dependency version inventory')
    for name,wanted in d['packages'].items():
        if version_lookup(name)!=wanted:raise ValueError('dependency version mismatch: '+name)
    contract=d['render_contract']
    if contract['adapter']!='qwen-text-rollback5-unfixed2-v1':raise ValueError('unsupported renderer adapter')
    if contract['tokenizers_version']!=d['packages']['tokenizers']:raise ValueError('inconsistent tokenizer version')
    if asset_inventory(model)!=contract['assets']:raise ValueError('render asset inventory/bytes mismatch')
    root=Path(root).resolve() if root is not None else package_root()
    if not REQUIRED_PACKAGE_FILES.issubset(d['package_files']):raise ValueError('incomplete package inventory')
    if python_inventory(root)!=d['package_files']:raise ValueError('package Python inventory/bytes mismatch')
    if function_source_hash(root/'inference/utils.py','parse_asr_output')!=contract['parse_source_sha256']:
        raise ValueError('parser function source identity mismatch')
    if file_hash(root/'core/transformers_backend/processing_qwen3_asr.py')!=contract['processor_source_sha256']:
        raise ValueError('processor source identity mismatch')
    return contract


def require_loaded_renderer_match(declared,loaded):
    if declared!=loaded:raise ValueError('loaded renderer differs from prevalidated contract')


def bootstrap_renderer_and_workers(order,*,load_renderer,spawn_workers,abort_workers):
    """Same two owned workers and full renderer; only initialization order varies.

    The caller owns normal finally cleanup. abort_workers must remove successfully
    closed partial-start handles from its registry, so finally cannot close twice.
    """
    if order not in {'full_first','descriptor_workers_first'}:raise ValueError('unknown startup order')
    try:
        if order=='full_first':
            renderer=load_renderer()
            spawn_workers()
        else:
            spawn_workers()
            renderer=load_renderer()
        return renderer
    except BaseException:
        abort_workers()
        raise
