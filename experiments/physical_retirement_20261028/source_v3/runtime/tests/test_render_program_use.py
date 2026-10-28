import json
from types import SimpleNamespace
import pytest
from revtrace.light_render import canonical_sha
from revtrace.render_program_use import eos_from_assets,check_native_program_context


def test_explicit_eos_asset_rejects_ambiguous_values(tmp_path):
    p=tmp_path/'generation_config.json'
    for value,want in [(3,[3]),([3,4],[3,4])]:
        p.write_text(json.dumps(dict(eos_token_id=value)))
        assert eos_from_assets(tmp_path)==want
    for value in [True,[],[False],[-1]]:
        p.write_text(json.dumps(dict(eos_token_id=value)))
        with pytest.raises(ValueError):eos_from_assets(tmp_path)


def test_native_check_does_not_relabel_changed_reference():
    class Tok:
        backend_tokenizer=SimpleNamespace(to_str=lambda:'{"padding":null}',encode_special_tokens=False)
        def encode(self,text):assert text=='';return []
    c=SimpleNamespace(contract=dict(adapter='fixture'),processor=SimpleNamespace(tokenizer=Tok()))
    spec=dict(native_backend_sha256=canonical_sha(dict(padding=None)),allowed_backends=['native','light'])
    declared=dict(adapter='fixture',owner_render_program=spec)
    check_native_program_context(declared,c)
    # The allowed set, not a chosen implementation, belongs in the shared
    # semantic contract. The native reference must still match exactly.
    assert declared['owner_render_program']['allowed_backends']==['native','light']
    with pytest.raises(ValueError):check_native_program_context({**declared,'adapter':'changed'},c)
    with pytest.raises(ValueError):check_native_program_context({**declared,'owner_render_program':{**spec,'native_backend_sha256':'0'*64}},c)
