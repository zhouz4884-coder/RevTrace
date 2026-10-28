"""Identity-pinned tokenizer program and exact native parser slice.

This module imports no model framework. It does not contain selected output or
cached transcript data. The adapter is a narrow implementation of the operations
used by TrustedQwenRender, not a replacement for the full Processor API.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import unicodedata
from typing import Optional,Tuple


FUNCTIONS=('normalize_language_name','detect_and_fix_repetitions','parse_asr_output')
CONSTANTS=('_ASR_TEXT_TAG','_LANG_PREFIX')
FORBIDDEN_IMPORTS=('torch','transformers','qwen_asr','librosa')
FIXED_OPERATIONS=dict(encode='single string, add_special_tokens caller boolean (default True), no padding/truncation, split_special_tokens=False',decode='integer list, caller skip_special_tokens boolean, clean_up_tokenization_spaces=False')


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4194304),b''):h.update(b)
    return h.hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def parser_slice(path,expected_file_sha,expected_ast_sha=None):
    if file_sha(path)!=expected_file_sha:raise ValueError('native parser file changed')
    tree=ast.parse(Path(path).read_text(encoding='utf8'))
    funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in FUNCTIONS}
    if set(funcs)!=set(FUNCTIONS):raise ValueError('missing native parser/helper')
    constants={}
    for n in tree.body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in CONSTANTS:
            constants[n.targets[0].id]=ast.literal_eval(n.value)
    if set(constants)!=set(CONSTANTS) or not all(isinstance(v,str) for v in constants.values()):
        raise ValueError('native parser constants changed')
    nodes=[funcs[name] for name in FUNCTIONS]
    identity=dict(functions={name:ast.dump(funcs[name],include_attributes=False) for name in FUNCTIONS},constants=constants)
    digest=canonical_sha(identity)
    if expected_ast_sha is not None and digest!=expected_ast_sha:raise ValueError('native parser AST identity changed')
    # The file is byte-pinned before compilation, and only these exact definitions
    # execute. Audio/network helpers and package top-level imports are excluded.
    namespace=dict(Optional=Optional,Tuple=Tuple,**constants)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace['parse_asr_output'],digest


class FrozenTokenizer:
    """Fixed unpadded/untruncated single-string wrapper operations only."""
    def __init__(self,backend,*,encode_special_tokens=False):
        if type(encode_special_tokens) is not bool or encode_special_tokens is not False:
            raise ValueError('unsupported special-token splitting mode')
        backend.no_padding();backend.no_truncation()
        backend.encode_special_tokens=bool(encode_special_tokens)
        self._backend=backend

    def encode(self,text,add_special_tokens=True):
        if not isinstance(text,str) or type(add_special_tokens) is not bool:
            raise ValueError('unsupported tokenizer encode input/options')
        # Match the native fast-wrapper operation, including the single-row
        # batch entry point, rather than assuming encode()==encode_batch().
        return self._backend.encode_batch([text],add_special_tokens=add_special_tokens,is_pretokenized=False)[0].ids

    def decode(self,ids,skip_special_tokens=False,clean_up_tokenization_spaces=None):
        if clean_up_tokenization_spaces not in (None,False):
            raise ValueError('unsupported cleanup transformation')
        if type(skip_special_tokens) is not bool or not isinstance(ids,(list,tuple)):
            raise ValueError('unsupported tokenizer decode input/options')
        if any(type(t) is not int or t<0 for t in ids):raise ValueError('token IDs must be nonnegative integers')
        return self._backend.decode(list(ids),skip_special_tokens=skip_special_tokens)


@dataclass
class LightContext:
    tokenizer: object
    parse: object
    reference_contract: dict
    implementation_identity: dict


def load_light_context(bundle,*,expected_descriptor_sha256,model,package_root):
    """Fail closed before exposing the parser/tokenizer to replay.

    This initial CPU component gate verifies all pinned files/versions. Serving
    integration still requires an explicit shared allowed-implementation contract.
    """
    bundle=Path(bundle).resolve();descriptor=bundle/'descriptor.json'
    if file_sha(descriptor)!=expected_descriptor_sha256:raise ValueError('light descriptor changed')
    d=json.loads(descriptor.read_text(encoding='utf8'))
    if d['schema']!='qwen-equivalent-render-program-v1':raise ValueError('unsupported renderer program')
    if d['fixed_operations']!=FIXED_OPERATIONS or d['encode_special_tokens'] is not False:
        raise ValueError('unsupported fixed tokenizer operations')
    if tuple(d['parser_functions'])!=FUNCTIONS:raise ValueError('unsupported parser dependency slice')
    if d['native_reference_contract']['adapter']!='qwen-text-rollback5-unfixed2-v1':raise ValueError('wrong reference adapter')
    if platform.python_version()!=d['python_version'] or unicodedata.unidata_version!=d['unicode_version']:
        raise ValueError('parser interpreter/unicode version changed')
    for name,want in d['packages'].items():
        if importlib.metadata.version(name)!=want:raise ValueError('renderer dependency version changed:'+name)
    from .startup_overlap import asset_inventory,REQUIRED_PACKAGE_FILES
    if d['model_assets']!=d['native_reference_contract']['assets'] or asset_inventory(model)!=d['model_assets']:
        raise ValueError('renderer model asset inventory/bytes changed')
    root=Path(package_root).resolve()
    actual={p.relative_to(root).as_posix():file_sha(p) for p in root.rglob('*.py') if p.is_file()}
    if not REQUIRED_PACKAGE_FILES.issubset(actual) or actual!=d['qwen_package_python']:
        raise ValueError('native package source inventory changed')
    for r in d['dependency_files']:
        if file_sha(r['path'])!=r['sha256']:raise ValueError('tokenizer/wrapper dependency bytes changed')
    program=bundle/d['program_file']
    if not program.resolve().is_relative_to(bundle) or file_sha(program)!=d['program_sha256']:
        raise ValueError('tokenizer program changed')
    if file_sha(__file__)!=d['light_module_sha256']:raise ValueError('light loader implementation changed')
    native_parse,ast_sha=parser_slice(root/'inference/utils.py',d['qwen_package_python']['inference/utils.py'],d['parser_ast_sha256'])
    from tokenizers import Tokenizer
    backend=Tokenizer.from_file(str(program))
    tok=FrozenTokenizer(backend,encode_special_tokens=d['encode_special_tokens'])
    if canonical_sha(json.loads(backend.to_str()))!=d['native_default_backend_sha256']:
        raise ValueError('loaded tokenizer backend differs from normalized native backend')
    return LightContext(tok,native_parse,d['native_reference_contract'],
        dict(schema=d['schema'],descriptor_sha256=expected_descriptor_sha256,
             program_sha256=d['program_sha256'],parser_ast_sha256=ast_sha,
             light_module_sha256=d['light_module_sha256']))
