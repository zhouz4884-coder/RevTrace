import hashlib,json
import pytest
import cpu_controller as c


def test_complete_byte_identity_not_only_fake_git_status(tmp_path,monkeypatch):
    p=tmp_path/'x.py';p.write_bytes(b'one');commit='a'*40
    m=tmp_path/'manifest.json';m.write_text(json.dumps(dict(code_commit=commit,files=[dict(path='x.py',bytes=3,sha256=hashlib.sha256(b'one').hexdigest())])))
    answers={('rev-parse','HEAD'):commit,('status','--porcelain'):'',('ls-files',):'x.py'}
    monkeypatch.setattr(c,'git',lambda root,*args:answers[args])
    assert c.validate(tmp_path,m)['code_commit']==commit
    p.write_bytes(b'two')
    with pytest.raises(AssertionError):c.validate(tmp_path,m)


def test_environment_record_has_no_function_local_importlib_binding(monkeypatch):
    monkeypatch.setattr(c.importlib.metadata,'version',lambda n:'fixture-'+n)
    for _ in range(2):
        record=c.environment_record()
        assert record['packages']['tokenizers']=='fixture-tokenizers'
        assert json.loads(json.dumps(record))==record
    assert 'importlib' not in c.main.__code__.co_varnames
