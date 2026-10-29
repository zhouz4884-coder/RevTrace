"""Meaningful CPU controls executing the pinned original C/update AST.

Only neural generate/processor inputs are synthetic.  Original infer code is
compiled for identity checks but never run, and no CUDA or remote call occurs.
These development controls do not stand in for final frozen-source CPU/GPU
equivalence gates.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import logging
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import numpy as np
import torch

from native_tail import (AUTHOR_CLASS, AUTHOR_GIT_BLOB, AUTHOR_SHA256,
                         PACKET_LIVE_INS, RUNTIME_LIVE_INS, TAIL_LIVE_INS,
                         compile_original_tail, run_identity_tail, run_tail)
from native_bridge import export_cut, identity_prediction


def author_path():
    explicit = os.environ.get('REVTRACE_NATIVE_AUTHOR_FILE')
    if explicit:
        return Path(explicit)
    local = Path(__file__).resolve().parents[1] / 'author_reference/simul_whisper/simul_whisper.py'
    if local.exists():
        return local
    # Formal Linux CPU execution uses the already fixed author checkout.
    return Path('/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/projects/'
                'revtrace_dsn_streamcorrect_20261028/author_StreamCorrect_bbb9f7f/'
                'simul_whisper/simul_whisper.py')


class WhisperTokenizer:
    words = {10: 'alpha', 11: 'beta', 20: 'gamma', 21: 'delta',
             30: 'epsilon', 31: 'zeta', 40: 'eta', 41: 'theta',
             91: 'chosen', 92: 'response', 99: ''}

    def decode(self, ids, **unused):
        values = ids.tolist() if hasattr(ids, 'tolist') else list(ids)
        return ' '.join(self.words.get(int(v), '') for v in values).strip()

    def encode(self, text):
        if not text:
            return []
        inverse = {word: token for token, word in self.words.items() if word}
        return [inverse[word] for word in text.split()]

    def split_to_word_tokens(self, ids):
        return [self.words.get(int(v), '') for v in ids], [[int(v)] for v in ids]


class CorrectorTokenizer:
    bos_token = '<bos>'
    pad_token_id = 0
    eos_token_id = 2

    def __init__(self, response='chosen response'):
        self.response = response

    def decode(self, ids, **unused):
        return self.response


class Processor:
    def __init__(self, response='chosen response'):
        self.tokenizer = CorrectorTokenizer(response)
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return dict(input_ids=torch.tensor([[4, 5, 6]], dtype=torch.long),
                    attention_mask=torch.ones((1, 3), dtype=torch.long))


class CorrectorModel:
    def __init__(self):
        self.config = types.SimpleNamespace(model_type='ultravox')
        self.calls = []

    def parameters(self):
        return iter([torch.tensor(0., dtype=torch.float32)])

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return torch.cat((kwargs['input_ids'], torch.tensor([[501]], dtype=torch.long)), dim=1)


class Decoder:
    def __init__(self):
        self.finished_sequences = {'old': [1, 2]}
        self.resets = 0

    def reset(self):
        self.resets += 1
        self.finished_sequences = {}


class UnreadDiagnostic:
    def __iter__(self):
        raise AssertionError('diagnostic payload was read')

    def __repr__(self):
        raise AssertionError('diagnostic payload was rendered')


class NativeTailCPUControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = author_path().resolve()
        cls.artifact = compile_original_tail(cls.path)
        raw = cls.path.read_bytes()
        tree = ast.parse(raw.decode('utf8'), filename=str(cls.path))
        original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == AUTHOR_CLASS)
        names = {'infer', '_run_SpeechLM_error_corrector', '_run_LM_error_corrector', '_clean_cache'}
        selected = [deepcopy(n) for n in original.body if isinstance(n, ast.FunctionDef) and n.name in names]
        class_node = ast.ClassDef(name=AUTHOR_CLASS, bases=[], keywords=[], body=selected, decorator_list=[])
        class_node.type_params = []
        cls.namespace = dict(torch=torch, np=np, time=time, logger=logging.getLogger('native-tail-cpu'))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[class_node], type_ignores=[])),
                     str(cls.path), 'exec', dont_inherit=True, optimize=0), cls.namespace)
        cls.engine_class = cls.namespace[AUTHOR_CLASS]

    def setUp(self):
        self.format_calls = []
        package = types.ModuleType('SpeechLMCorrector')
        module = types.ModuleType('SpeechLMCorrector.training_qwen2audio')

        def format_instruction_for_correction(**kwargs):
            self.format_calls.append(kwargs)
            return 'ordered:' + '|'.join(kwargs['k_best_candidates'])

        module.format_instruction_for_correction = format_instruction_for_correction
        self.modules = patch.dict(sys.modules, {'SpeechLMCorrector': package,
                                                'SpeechLMCorrector.training_qwen2audio': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def engine_and_locals(self, *, response='chosen response'):
        engine = self.engine_class()
        engine.is_warmup = False
        engine.first_token_generated = False
        engine.first_token_latency = None
        engine.tokenizer = WhisperTokenizer()
        engine.cfg = types.SimpleNamespace(beam_size=4)
        engine.model = types.SimpleNamespace(device=torch.device('cpu'))
        engine.tokens = [torch.tensor([[1, 2, 3, 4]] * 4, dtype=torch.long)]
        engine.kv_cache = {'old': torch.tensor([1.])}
        engine.dec_attns = [torch.tensor([2.])]
        engine.inference = types.SimpleNamespace(kv_cache=engine.kv_cache)
        engine.decoder_type = 'beam'
        engine.token_decoder = Decoder()
        current = torch.tensor([[1, 2, 3, 4, 10, 11], [1, 2, 3, 4, 20, 21],
                                [1, 2, 3, 4, 30, 31], [1, 2, 3, 4, 40, 41]], dtype=torch.long)
        now = time.time()
        values = dict(current_tokens=current, token_len_before_decoding=4,
                      input_segments=torch.tensor([.1, -.2, .3], dtype=torch.float32),
                      fire_detected=False, is_last=True,
                      generation={'starting_tokens': object(), 'ASR_only_flag': 7},
                      corrector_type='speechlm', corrector_model=CorrectorModel(),
                      corrector_processor=Processor(response), infer_start_time=now,
                      start_time=now, t_before_decoding=now)
        return engine, values

    def invoke(self, engine, values):
        return run_tail(engine, values, compiled=self.artifact)

    def identity_engine_and_locals(self):
        engine, values = self.engine_and_locals()
        engine._run_SpeechLM_error_corrector = types.MethodType(identity_prediction, engine)
        values.update(corrector_model=object(), corrector_processor=None)
        return engine, values

    def invoke_identity(self, engine, values):
        return run_identity_tail(engine, values, compiled=self.artifact)

    def test_exact_original_blob_and_live_in_schema(self):
        self.assertEqual(self.artifact.author_sha256, AUTHOR_SHA256)
        self.assertEqual(self.artifact.author_git_blob, AUTHOR_GIT_BLOB)
        self.assertEqual((self.artifact.start_line, self.artifact.end_line), (1053, 1138))
        self.assertEqual(self.artifact.required_locals, TAIL_LIVE_INS)
        self.assertEqual(set(PACKET_LIVE_INS) | set(RUNTIME_LIVE_INS), set(TAIL_LIVE_INS))
        self.assertEqual(self.artifact.generation_payload_reads, ('error_corrector',))

    def test_tail_AST_is_exact_original_suffix(self):
        tree = ast.parse(self.path.read_text(encoding='utf8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == AUTHOR_CLASS)
        infer = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'infer')
        index = next(i for i, n in enumerate(infer.body) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'use_error_corrector' for t in n.targets))
        raw_ast = ast.dump(ast.Module(body=infer.body[index:], type_ignores=[]), include_attributes=False)
        self.assertEqual(hashlib.sha256(raw_ast.encode()).hexdigest(), self.artifact.tail_ast_sha256)

    def test_changed_author_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'author.py'
            path.write_bytes(self.path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'bytes/blob mismatch'):
                compile_original_tail(path)

    def test_caller_cannot_repin_another_author(self):
        with self.assertRaisesRegex(ValueError, 'only the pinned'):
            compile_original_tail(self.path, expected_sha256='0' * 64)

    def test_original_C_receives_all_beams_and_selects_original_response(self):
        engine, values = self.engine_and_locals()
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [91, 92])
        self.assertEqual(self.format_calls[0]['k_best_candidates'],
                         ['alpha beta', 'gamma delta', 'epsilon zeta', 'eta theta'])
        self.assertEqual(generation['error_corrector']['corrected_appended_text'], 'chosen response')
        self.assertEqual(generation['error_corrector']['corrected_appended_token_ids'], [91, 92])
        call = values['corrector_model'].calls[0]
        self.assertEqual(call['max_new_tokens'], 8)
        self.assertIs(call['do_sample'], False)
        np.testing.assert_array_equal(values['corrector_processor'].calls[0]['audio'],
                                      values['input_segments'].numpy())

    def test_generation_identity_and_unread_diagnostics_survive(self):
        engine, values = self.engine_and_locals()
        diagnostic = UnreadDiagnostic()
        values['generation']['diagnostic'] = diagnostic
        starting = values['generation']['starting_tokens']
        _, generation = self.invoke(engine, values)
        self.assertIs(generation, values['generation'])
        self.assertIs(generation['diagnostic'], diagnostic)
        self.assertIs(generation['starting_tokens'], starting)
        self.assertEqual(generation['ASR_only_flag'], 7)

    def test_original_C_result_object_is_not_copied_or_substituted(self):
        engine, values = self.engine_and_locals()
        returned = []
        old = sys.getprofile()

        def profile(frame, event, value):
            if event == 'return' and frame.f_code.co_name == '_run_SpeechLM_error_corrector':
                returned.append(value)

        sys.setprofile(profile)
        try:
            _, generation = self.invoke(engine, values)
        finally:
            sys.setprofile(old)
        self.assertEqual(len(returned), 1)
        self.assertIs(generation['error_corrector'], returned[0])

    def test_original_append_cleanup_and_decoder_reset_execute(self):
        engine, values = self.engine_and_locals()
        self.invoke(engine, values)
        self.assertTrue(torch.equal(engine.tokens[-1], torch.tensor([[91, 92]] * 4)))
        self.assertEqual(engine.dec_attns, [])
        self.assertEqual(engine.kv_cache, {})
        self.assertIs(engine.inference.kv_cache, engine.kv_cache)
        self.assertEqual(engine.token_decoder.resets, 1)
        self.assertEqual(engine.token_decoder.finished_sequences, {})

    def test_final_no_corrector_uses_whole_top_beam(self):
        engine, values = self.engine_and_locals()
        values['corrector_model'] = None
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [10, 11])
        self.assertNotIn('error_corrector', generation)

    def test_nonfinal_no_corrector_uses_original_word_truncation(self):
        engine, values = self.engine_and_locals()
        values.update(corrector_model=None, is_last=False, fire_detected=False)
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [10])
        self.assertEqual(generation['result']['split_tokens'], [[10]])
        self.assertEqual(generation['result_truncated']['split_tokens'], [[11]])

    def test_single_word_nonfinal_returns_empty_original_hypothesis(self):
        engine, values = self.engine_and_locals()
        values.update(corrector_model=None, is_last=False, current_tokens=values['current_tokens'][:, :5])
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [])
        self.assertEqual(tuple(engine.tokens[-1].shape), (4, 0))
        self.assertIn('result_truncated', generation)

    def test_fire_detected_fallback_keeps_complete_top_beam(self):
        engine, values = self.engine_and_locals()
        values.update(corrector_model=None, is_last=False, fire_detected=True)
        ids, _ = self.invoke(engine, values)
        self.assertEqual(ids, [10, 11])

    def test_original_C_None_result_uses_original_terminal_fallback(self):
        engine, values = self.engine_and_locals()
        values['current_tokens'][:, 4:] = 99
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [99, 99])
        self.assertNotIn('error_corrector', generation)
        self.assertEqual(values['corrector_model'].calls, [])
        self.assertEqual(engine.token_decoder.resets, 1)

    def test_nonNone_empty_corrector_selection_does_not_fallback(self):
        engine, values = self.engine_and_locals(response='')
        ids, generation = self.invoke(engine, values)
        self.assertEqual(ids, [])
        self.assertIn('error_corrector', generation)
        self.assertEqual(generation['error_corrector']['corrected_appended_token_ids'], [])

    def test_warmup_skips_original_corrector(self):
        engine, values = self.engine_and_locals()
        engine.is_warmup = True
        ids, _ = self.invoke(engine, values)
        self.assertEqual(ids, [10, 11])
        self.assertEqual(values['corrector_model'].calls, [])

    def test_missing_or_injected_global_live_in_rejected_before_mutation(self):
        engine, values = self.engine_and_locals()
        del values['input_segments']
        with self.assertRaisesRegex(ValueError, 'live-ins missing or unexpected'):
            self.invoke(engine, values)
        self.assertEqual(len(engine.tokens), 1)
        engine, values = self.engine_and_locals()
        values['torch'] = object()
        with self.assertRaisesRegex(ValueError, 'live-ins missing or unexpected'):
            self.invoke(engine, values)

    def test_preselected_C_result_injection_rejected(self):
        engine, values = self.engine_and_locals()
        values['generation']['error_corrector'] = {'corrected_appended_token_ids': [777]}
        with self.assertRaisesRegex(ValueError, 'cannot inject'):
            self.invoke(engine, values)

    def test_identity_predictor_cannot_replace_Authority_C(self):
        engine, values = self.engine_and_locals()
        engine._run_SpeechLM_error_corrector = types.MethodType(lambda self, **kw: {'chosen': 'fake'}, engine)
        with self.assertRaisesRegex(ValueError, 'pinned author file|was replaced'):
            self.invoke(engine, values)
        self.assertEqual(len(engine.tokens), 1)

    def test_replaced_cleanup_is_rejected(self):
        engine, values = self.engine_and_locals()
        engine._clean_cache = types.MethodType(lambda self: None, engine)
        with self.assertRaisesRegex(ValueError, 'pinned author file|was replaced'):
            self.invoke(engine, values)

    def test_cached_foreign_corrector_objects_are_rejected(self):
        engine, values = self.engine_and_locals()
        engine._speechlm_model = object()
        engine._speechlm_processor = values['corrector_processor']
        with self.assertRaisesRegex(ValueError, 'cached SpeechLM objects'):
            self.invoke(engine, values)

    def test_default_compilation_uses_same_pinned_author_source(self):
        engine, values = self.engine_and_locals()
        ids, generation = run_tail(engine, values)
        self.assertEqual(ids, [91, 92])
        self.assertIs(generation, values['generation'])

    def test_identity_projection_retokenizes_and_appends_original_top_beam(self):
        engine, values = self.identity_engine_and_locals()
        diagnostic = UnreadDiagnostic()
        values['generation']['diagnostic'] = diagnostic
        generation_before = values['generation']
        starting = generation_before['starting_tokens']
        ids, generation = self.invoke_identity(engine, values)
        self.assertEqual(ids, [10, 11])
        self.assertTrue(generation['error_corrector']['private_identity_prediction'])
        self.assertEqual(generation['error_corrector']['candidates'], ['alpha beta'])
        self.assertEqual(generation['error_corrector']['corrected_appended_text'], 'alpha beta')
        self.assertEqual(generation['error_corrector']['corrected_appended_token_ids'], [10, 11])
        self.assertIs(generation, generation_before)
        self.assertIs(generation['starting_tokens'], starting)
        self.assertIs(generation['diagnostic'], diagnostic)
        self.assertTrue(torch.equal(engine.tokens[-1], torch.tensor([[10, 11]] * 4)))
        self.assertEqual(engine.token_decoder.resets, 1)

    def test_identity_projection_preserves_confirmed_prefix_before_append(self):
        engine, values = self.identity_engine_and_locals()
        values['token_len_before_decoding'] = 5
        ids, generation = self.invoke_identity(engine, values)
        self.assertEqual(ids, [11])
        self.assertEqual(generation['error_corrector']['previous_transcription'], 'alpha')
        self.assertEqual(generation['error_corrector']['corrected_appended_text'], 'beta')

    def test_identity_projection_warmup_uses_original_nonfinal_fallback(self):
        engine, values = self.identity_engine_and_locals()
        engine.is_warmup = True
        values.update(is_last=False, fire_detected=False)
        ids, generation = self.invoke_identity(engine, values)
        self.assertEqual(ids, [10])
        self.assertNotIn('error_corrector', generation)
        self.assertEqual(generation['result']['split_tokens'], [[10]])
        self.assertEqual(generation['result_truncated']['split_tokens'], [[11]])
        self.assertEqual(engine.token_decoder.resets, 1)

    def test_identity_projection_runs_original_cleanup_before_closed_cut_export(self):
        engine, values = self.identity_engine_and_locals()
        engine.cfg.language = 'zh'
        engine.detected_language = 'zh'
        engine.segments = [values['input_segments'].clone()]
        engine.context = types.SimpleNamespace(text='', prefix_token_ids=[], as_token_ids=lambda: [])
        engine.last_attend_frame = 0
        engine.initial_tokens = engine.tokens[0].clone()
        engine.initial_token_length = 4
        engine.sot_index = 0
        with self.assertRaisesRegex(ValueError, 'cache not cleaned'):
            export_cut(engine, frontier=3, transcript='', contract={'synthetic_cpu': True})
        ids, _ = self.invoke_identity(engine, values)
        cut = export_cut(engine, frontier=3, transcript=engine.tokenizer.decode(ids),
                         contract={'synthetic_cpu': True})
        self.assertEqual(cut.frontier, 3)
        self.assertEqual(cut.transcript, 'alpha beta')
        self.assertEqual(cut.state['tokens'][-1], [[10, 11]] * 4)
        self.assertEqual(engine.dec_attns, [])
        self.assertEqual(engine.kv_cache, {})
        self.assertIs(engine.inference.kv_cache, engine.kv_cache)
        self.assertEqual(engine.token_decoder.finished_sequences, {})

    def test_Authority_entry_still_rejects_exact_native_identity_selector(self):
        engine, values = self.identity_engine_and_locals()
        with self.assertRaisesRegex(ValueError, 'was replaced|pinned author file'):
            self.invoke(engine, values)
        self.assertEqual(len(engine.tokens), 1)
        self.assertEqual(engine.token_decoder.resets, 0)

    def test_identity_entry_rejects_original_learned_C_or_replacement(self):
        engine, values = self.engine_and_locals()
        values.update(corrector_model=object(), corrector_processor=None)
        with self.assertRaisesRegex(ValueError, 'exact native private identity'):
            self.invoke_identity(engine, values)
        engine._run_SpeechLM_error_corrector = types.MethodType(lambda self, **kw: None, engine)
        with self.assertRaisesRegex(ValueError, 'exact native private identity'):
            self.invoke_identity(engine, values)
        self.assertEqual(len(engine.tokens), 1)

    def test_identity_entry_rejects_foreign_runtime_bindings(self):
        for key, value in [('corrector_model', CorrectorModel()),
                           ('corrector_model', None), ('corrector_processor', Processor()),
                           ('corrector_type', 'lm')]:
            with self.subTest(key=key, value_type=type(value).__name__):
                engine, values = self.identity_engine_and_locals()
                values[key] = value
                with self.assertRaisesRegex(ValueError, 'inert model sentinel|speechlm interface'):
                    self.invoke_identity(engine, values)
                self.assertEqual(len(engine.tokens), 1)

    def test_identity_entry_rejects_preselected_result_and_replaced_cleanup(self):
        engine, values = self.identity_engine_and_locals()
        values['generation']['error_corrector'] = {'corrected_appended_text': 'fake'}
        with self.assertRaisesRegex(ValueError, 'cannot inject'):
            self.invoke_identity(engine, values)
        engine, values = self.identity_engine_and_locals()
        engine._clean_cache = types.MethodType(lambda self: None, engine)
        with self.assertRaisesRegex(ValueError, 'was replaced|pinned author file'):
            self.invoke_identity(engine, values)
        self.assertEqual(engine.token_decoder.resets, 0)

    def test_identity_default_compilation_uses_original_source(self):
        engine, values = self.identity_engine_and_locals()
        ids, generation = run_identity_tail(engine, values)
        self.assertEqual(ids, [10, 11])
        self.assertTrue(generation['error_corrector']['private_identity_prediction'])


if __name__ == '__main__':
    unittest.main()
