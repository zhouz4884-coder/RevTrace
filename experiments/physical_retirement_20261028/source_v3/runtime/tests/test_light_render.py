"""CPU fixtures for program checks; not real tokenizer equivalence evidence."""
import hashlib,json
import pytest
from revtrace.light_render import FrozenTokenizer,parser_slice


class Backend:
    def no_padding(self):self.padding=None
    def no_truncation(self):self.truncation=None
    def encode_batch(self,text,add_special_tokens,is_pretokenized):
        assert text==['x'] and is_pretokenized is False
        class Result:ids=[1,2]
        return [Result()]
    def decode(self,ids,skip_special_tokens):return 'fixture'


def test_fixed_wrapper_and_options_fail_closed():
    b=Backend();tok=FrozenTokenizer(b,encode_special_tokens=False)
    assert tok.encode('x')==[1,2] and tok.decode([1,2],skip_special_tokens=True)=='fixture'
    assert b.padding is None and b.truncation is None and b.encode_special_tokens is False
    with pytest.raises(ValueError):tok.decode([1],clean_up_tokenization_spaces=True)
    with pytest.raises(ValueError):tok.decode([True])
    with pytest.raises(ValueError):tok.encode(['x'])
    with pytest.raises(ValueError):FrozenTokenizer(Backend(),encode_special_tokens='false')
    with pytest.raises(ValueError):FrozenTokenizer(Backend(),encode_special_tokens=True)


def test_exact_parser_slice_excludes_top_level_heavy_imports(tmp_path):
    p=tmp_path/'utils.py';p.write_text('import certainly_not_a_real_heavy_module\n_ASR_TEXT_TAG="tag"\n_LANG_PREFIX="lang "\ndef normalize_language_name(x):\n    return str(x)\ndef detect_and_fix_repetitions(x):\n    return x\ndef parse_asr_output(raw,user_language=None):\n    return user_language,detect_and_fix_repetitions(raw)\n')
    sha=hashlib.sha256(p.read_bytes()).hexdigest();parse,identity=parser_slice(p,sha)
    assert parse('x',user_language='English')==('English','x')
    assert parser_slice(p,sha,identity)[0]('y')==(None,'y')
    with pytest.raises(ValueError):parser_slice(p,sha,'0'*64)
    p.write_text(p.read_text()+'\n# modification\n')
    with pytest.raises(ValueError):parser_slice(p,sha)
