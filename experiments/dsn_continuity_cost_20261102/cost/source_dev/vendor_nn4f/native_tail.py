"""Execute only the pinned author's original corrector/update AST suffix.

This module neither defines a CandidatePacket nor restores open state.  The
caller supplies an already restored *open* engine plus explicit live-ins.
No closed FeedbackCut is manufactured here.  Native C selection, retokenize,
append, cache cleanup, and decoder reset remain the original author code.
"""
from __future__ import annotations

import ast
import builtins
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import inspect
from pathlib import Path
from types import CodeType
from typing import Mapping

AUTHOR_SHA256 = '9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7'
AUTHOR_GIT_BLOB = '02a2202ae6f559c70014eca789796cbc948dd340'
AUTHOR_CLASS = 'PaddedAlignAttWhisper'
PACKET_LIVE_INS = (
    'current_tokens', 'token_len_before_decoding', 'input_segments',
    'fire_detected', 'is_last', 'generation', 'corrector_type',
)
RUNTIME_LIVE_INS = (
    'corrector_model', 'corrector_processor',
    'infer_start_time', 'start_time', 't_before_decoding',
)
TAIL_LIVE_INS = PACKET_LIVE_INS + RUNTIME_LIVE_INS
_GLOBAL_NAMES = ('logger', 'time', 'torch')
_METHOD_NAMES = ('infer', '_run_SpeechLM_error_corrector',
                 '_run_LM_error_corrector', '_clean_cache')
_FUNCTION_NAME = '_revtrace_original_CU_tail'


def _need(value, message):
    if not value:
        raise ValueError(message)


def _find_code(parent: CodeType, name: str) -> CodeType:
    candidates = [v for v in parent.co_consts if isinstance(v, CodeType) and v.co_name == name]
    _need(len(candidates) == 1, 'ambiguous or missing original code object: ' + name)
    return candidates[0]


def _same_constant(a, b):
    if isinstance(a, CodeType) or isinstance(b, CodeType):
        return isinstance(a, CodeType) and isinstance(b, CodeType) and _same_code(a, b)
    if isinstance(a, tuple) or isinstance(b, tuple):
        return (isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b)
                and all(_same_constant(x, y) for x, y in zip(a, b)))
    return type(a) is type(b) and a == b


def _same_code(actual: CodeType, expected: CodeType) -> bool:
    """Compare behavior-bearing code fields, excluding source path/line metadata."""
    fields = ('co_code', 'co_names', 'co_varnames', 'co_freevars', 'co_cellvars',
              'co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_flags')
    return (all(getattr(actual, key) == getattr(expected, key) for key in fields)
            and len(actual.co_consts) == len(expected.co_consts)
            and all(_same_constant(a, b) for a, b in zip(actual.co_consts, expected.co_consts)))


@dataclass(frozen=True)
class CompiledOriginalTail:
    author_path: str
    author_sha256: str
    author_git_blob: str
    start_line: int
    end_line: int
    required_locals: tuple[str, ...]
    packet_locals: tuple[str, ...]
    runtime_locals: tuple[str, ...]
    tail_ast_sha256: str
    generation_payload_reads: tuple[str, ...]
    _module_code: CodeType = field(repr=False, compare=False)
    _method_codes: tuple[tuple[str, CodeType], ...] = field(repr=False, compare=False)


def compile_original_tail(author_file, expected_sha256=AUTHOR_SHA256) -> CompiledOriginalTail:
    """Compile the exact top-level suffix from ``use_error_corrector=False``.

    Only the fixed public author blob is accepted.  No source string surgery,
    inlined selector, replacement update, or execution of the author module is
    used.  The original suffix AST nodes are copied verbatim into a function
    with explicit live-in arguments.
    """
    _need(expected_sha256 == AUTHOR_SHA256, 'only the pinned original author SHA is allowed')
    path = Path(author_file).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    _need(digest == AUTHOR_SHA256 and blob == AUTHOR_GIT_BLOB, 'original author bytes/blob mismatch')
    tree = ast.parse(raw.decode('utf8'), filename=str(path))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == AUTHOR_CLASS]
    _need(len(classes) == 1, 'original author class not unique')
    cls = classes[0]
    methods = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in _METHOD_NAMES}
    _need(set(methods) == set(_METHOD_NAMES), 'required original methods missing')
    infer = methods['infer']
    boundaries = [i for i, node in enumerate(infer.body)
                  if isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'use_error_corrector'
                  and isinstance(node.value, ast.Constant) and node.value.value is False]
    _need(len(boundaries) == 1, 'original C/update split not unique')
    suffix = infer.body[boundaries[0]:]
    _need(isinstance(suffix[-1], ast.Return), 'original suffix does not end in return')
    original_suffix = ast.Module(body=suffix, type_ignores=[])
    loads = {n.id for n in ast.walk(original_suffix) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    stores = {n.id for n in ast.walk(original_suffix) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Param))}
    live = loads - stores - {'self', 'len', *_GLOBAL_NAMES}
    _need(live == set(TAIL_LIVE_INS), 'pinned suffix live-in schema differs')
    generation_reads = set()
    for node in ast.walk(original_suffix):
        if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
                and isinstance(node.value, ast.Name) and node.value.id == 'generation'):
            _need(isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str), 'dynamic generation read')
            generation_reads.add(node.slice.value)
    _need(generation_reads == {'error_corrector'}, 'unmodeled diagnostic generation payload read')
    arguments = ast.arguments(posonlyargs=[], args=[ast.arg(arg=name) for name in ('self', *TAIL_LIVE_INS)],
                              vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    function = ast.FunctionDef(name=_FUNCTION_NAME, args=arguments, body=deepcopy(suffix),
                               decorator_list=deepcopy(infer.decorator_list), returns=None, type_comment=None)
    # Python 3.12+ exposes this field; assigning it is harmless on older ASTs.
    function.type_params = []
    ast.copy_location(function, suffix[0])
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    module_code = compile(module, str(path), 'exec', dont_inherit=True, optimize=0)
    # Compile the complete pinned module, without executing it. CPython's
    # bytecode encoding can depend on the full compilation unit; compiling a
    # subset class is not an independent oracle for the imported original.
    # Preserve exact code/flags checks rather than normalizing their mismatch.
    reference = compile(raw, str(path), 'exec', dont_inherit=True, optimize=0)
    class_code = _find_code(reference, AUTHOR_CLASS)
    expected_codes = tuple((name, _find_code(class_code, name)) for name in _METHOD_NAMES)
    return CompiledOriginalTail(
        str(path), digest, blob, suffix[0].lineno, suffix[-1].end_lineno,
        TAIL_LIVE_INS, PACKET_LIVE_INS, RUNTIME_LIVE_INS,
        hashlib.sha256(ast.dump(original_suffix, include_attributes=False).encode()).hexdigest(),
        tuple(sorted(generation_reads)), module_code, expected_codes,
    )


@lru_cache(maxsize=8)
def _compiled_from_path(path: str):
    return compile_original_tail(path)


def _bound_original_method(engine, name, artifact):
    bound = getattr(engine, name, None)
    wrapped = getattr(bound, '__func__', None)
    _need(wrapped is not None and getattr(bound, '__self__', None) is engine,
          'original author method is not bound to this engine: ' + name)
    # infer is decorated with the author's torch.no_grad.  Check the original
    # wrapped descriptor by identity, then check the actual author's inner code.
    # A packet/instance cannot smuggle an identity selector in via __wrapped__.
    function = inspect.unwrap(wrapped)
    original_class = function.__globals__.get(AUTHOR_CLASS)
    _need(isinstance(original_class, type) and isinstance(engine, original_class)
          and inspect.getattr_static(original_class, name) is wrapped,
          'original author class method was replaced: ' + name)
    _need(Path(function.__code__.co_filename).resolve() == Path(artifact.author_path),
          'method is not from the pinned author file: ' + name)
    expected = dict(artifact._method_codes)[name]
    _need(_same_code(function.__code__, expected), 'original author method was replaced: ' + name)
    return function


def run_tail(engine, locals_dict: Mapping, *, compiled: CompiledOriginalTail | None = None):
    """Return the original ``(ids, generation)`` after original C and update.

    Supply exactly the seven decoded packet locals plus five Authority runtime
    bindings.  Generation is mutated/returned by the author's code itself;
    this helper does not precompute a C result or rewrite selected token IDs.
    """
    _need(isinstance(locals_dict, Mapping), 'tail locals must be a mapping')
    keys = set(locals_dict)
    _need(keys == set(TAIL_LIVE_INS),
          'tail live-ins missing or unexpected: missing=' + repr(sorted(set(TAIL_LIVE_INS) - keys))
          + ', extra=' + repr(sorted(keys - set(TAIL_LIVE_INS))))
    _need(type(locals_dict['generation']) is dict, 'generation must retain its original mapping')
    _need('error_corrector' not in locals_dict['generation'],
          'packet cannot inject an already selected corrector result')
    if compiled is None:
        original = getattr(getattr(engine, 'infer', None), '__func__', None)
        _need(original is not None, 'engine has no original infer method')
        compiled = _compiled_from_path(str(Path(inspect.getfile(inspect.unwrap(original))).resolve()))
    _need(isinstance(compiled, CompiledOriginalTail), 'invalid compiled author tail')
    infer = _bound_original_method(engine, 'infer', compiled)
    _bound_original_method(engine, '_clean_cache', compiled)
    calls_corrector = (locals_dict['token_len_before_decoding'] > 0
                       and not engine.is_warmup and locals_dict['corrector_model'] is not None)
    if calls_corrector:
        method = '_run_LM_error_corrector' if locals_dict['corrector_type'] == 'lm' else '_run_SpeechLM_error_corrector'
        _bound_original_method(engine, method, compiled)
        if method == '_run_SpeechLM_error_corrector' and hasattr(engine, '_speechlm_model'):
            _need(engine._speechlm_model is locals_dict['corrector_model']
                  and engine._speechlm_processor is locals_dict['corrector_processor'],
                  'cached SpeechLM objects differ from Authority runtime bindings')
    namespace = {'__builtins__': builtins.__dict__}
    for name in _GLOBAL_NAMES:
        _need(name in infer.__globals__, 'original author global missing: ' + name)
        namespace[name] = infer.__globals__[name]
    exec(compiled._module_code, namespace)
    function = namespace[_FUNCTION_NAME]
    return function(engine, **{name: locals_dict[name] for name in TAIL_LIVE_INS})


def run_identity_tail(engine, locals_dict: Mapping, *, compiled: CompiledOriginalTail | None = None):
    """Run the same original update suffix for a private identity projection.

    This separate entry accepts only NativeBridge's exact identity selector,
    bound to this projection engine, and its inert model sentinel.  It never
    selects learned Authority output or certifies a packet as a FeedbackCut.
    The caller must isolate the engine's mutable state before calling it.
    ``run_tail`` retains its original-method guards for actual Authority C.
    """
    from native_bridge import identity_prediction

    _need(isinstance(locals_dict, Mapping), 'identity tail locals must be a mapping')
    keys = set(locals_dict)
    _need(keys == set(TAIL_LIVE_INS),
          'identity tail live-ins missing or unexpected: missing=' + repr(sorted(set(TAIL_LIVE_INS) - keys))
          + ', extra=' + repr(sorted(keys - set(TAIL_LIVE_INS))))
    _need(type(locals_dict['generation']) is dict, 'generation must retain its original mapping')
    _need('error_corrector' not in locals_dict['generation'],
          'packet cannot inject an already selected corrector result')
    _need(locals_dict['corrector_type'] == 'speechlm', 'identity projection requires speechlm interface')
    _need(type(locals_dict['corrector_model']) is object
          and locals_dict['corrector_processor'] is None,
          'identity projection requires an inert model sentinel and no processor')
    if compiled is None:
        original = getattr(getattr(engine, 'infer', None), '__func__', None)
        _need(original is not None, 'engine has no original infer method')
        compiled = _compiled_from_path(str(Path(inspect.getfile(inspect.unwrap(original))).resolve()))
    _need(isinstance(compiled, CompiledOriginalTail), 'invalid compiled author tail')
    infer = _bound_original_method(engine, 'infer', compiled)
    _bound_original_method(engine, '_clean_cache', compiled)
    identity = getattr(engine, '_run_SpeechLM_error_corrector', None)
    _need(getattr(identity, '__self__', None) is engine
          and getattr(identity, '__func__', None) is identity_prediction,
          'identity projection requires the exact native private identity selector')
    namespace = {'__builtins__': builtins.__dict__}
    for name in _GLOBAL_NAMES:
        _need(name in infer.__globals__, 'original author global missing: ' + name)
        namespace[name] = infer.__globals__[name]
    exec(compiled._module_code, namespace)
    function = namespace[_FUNCTION_NAME]
    return function(engine, **{name: locals_dict[name] for name in TAIL_LIVE_INS})
