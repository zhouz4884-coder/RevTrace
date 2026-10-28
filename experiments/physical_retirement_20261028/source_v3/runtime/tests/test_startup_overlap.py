"""Mock order and exact identity guards; separate from real tokenizer equivalence."""
import hashlib,json
from pathlib import Path
import pytest
from revtrace.startup_overlap import (PACKAGES,asset_inventory,python_inventory,function_source_hash,
    verify_prefrozen_renderer,require_loaded_renderer_match,bootstrap_renderer_and_workers)


def fixture_descriptor(tmp_path):
    root=tmp_path/'package';model=tmp_path/'model';model.mkdir()
    (model/'vocab.json').write_text('{}\n')
    for name,text in {'__init__.py':'# fake package\n','inference/qwen3_asr.py':'# fake engine\n',
      'inference/utils.py':'def parse_asr_output(raw):\n    return raw\n',
      'core/transformers_backend/processing_qwen3_asr.py':'# fake processor\n'}.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    contract=dict(adapter='qwen-text-rollback5-unfixed2-v1',assets=asset_inventory(model),
        parse_source_sha256=function_source_hash(root/'inference/utils.py','parse_asr_output'),
        processor_source_sha256=hashlib.sha256((root/'core/transformers_backend/processing_qwen3_asr.py').read_bytes()).hexdigest(),
        tokenizers_version='fixture',published_text_encoding='UTF-8 byte exact')
    d=dict(schema='qwen-trusted-render-startup-v1',inventory_scope='qwen-asr-all-python-v1',
        render_contract=contract,package_files=python_inventory(root),packages={n:'fixture' for n in PACKAGES})
    p=tmp_path/'descriptor.json';p.write_text(json.dumps(d))
    return root,model,p,d,hashlib.sha256(p.read_bytes()).hexdigest()


def check(f):
    root,model,path,d,sha=f
    return verify_prefrozen_renderer(model,path,expected_descriptor_sha256=sha,root=root,version_lookup=lambda _:'fixture')


def test_exact_inventory_passes_without_importing_model(tmp_path):
    f=fixture_descriptor(tmp_path)
    assert check(f)==f[3]['render_contract']


@pytest.mark.parametrize('where',['asset','dependency','extra-source','descriptor'])
def test_changed_bytes_fail_before_worker_start(tmp_path,where):
    f=fixture_descriptor(tmp_path);root,model,path,d,sha=f
    if where=='asset':(model/'vocab.json').write_text('{"change":1}')
    elif where=='dependency':(root/'inference/utils.py').write_text('def parse_asr_output(raw):\n    return 1\n')
    elif where=='extra-source':(root/'extra.py').write_text('x=1\n')
    else:path.write_text(json.dumps(d)+' ')
    calls=[]
    with pytest.raises(ValueError):
        check(f)
        calls.append('spawn')
    assert not calls


def test_same_contract_two_orders_and_no_relabeling():
    histories=[]
    for order in ['full_first','descriptor_workers_first']:
        events=[];declared={'assets':{'vocab':'digest'},'parser':'frozen'}
        def render():
            events.append('full-native-renderer')
            require_loaded_renderer_match(declared,dict(declared))
            events.append('identity-confirmed')
            return declared
        result=bootstrap_renderer_and_workers(order,load_renderer=render,
            spawn_workers=lambda:events.extend(['worker0','worker1']),abort_workers=lambda:events.append('abort'))
        assert result==declared
        histories.append(events)
    assert histories[0]==['full-native-renderer','identity-confirmed','worker0','worker1']
    assert histories[1]==['worker0','worker1','full-native-renderer','identity-confirmed']


@pytest.mark.parametrize('failure',['load','identity','partial-spawn'])
def test_overlap_failure_cleans_owned_workers_and_never_starts_wal(failure):
    calls=[];owned=[]
    def spawn():
        owned.append(0);calls.append('worker0')
        if failure=='partial-spawn':raise RuntimeError('spawn failed')
        owned.append(1);calls.append('worker1')
    def render():
        calls.append('render')
        if failure=='load':raise RuntimeError('load failed')
        require_loaded_renderer_match({'identity':'declared'},{'identity':'changed'})
    def abort():
        while owned:calls.append('close'+str(owned.pop()))
    with pytest.raises((RuntimeError,ValueError)):
        bootstrap_renderer_and_workers('descriptor_workers_first',load_renderer=render,spawn_workers=spawn,abort_workers=abort)
        calls.append('WAL')
    assert not owned and 'WAL' not in calls
    assert calls.count('close0')==1
    assert calls.count('close1')==(failure!='partial-spawn')


def test_dependency_versions_and_incomplete_inventory_fail(tmp_path):
    f=fixture_descriptor(tmp_path);root,model,path,d,sha=f
    with pytest.raises(ValueError):
        verify_prefrozen_renderer(model,path,expected_descriptor_sha256=sha,root=root,version_lookup=lambda _:'changed')
    del d['package_files']['inference/utils.py'];path.write_text(json.dumps(d));sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        verify_prefrozen_renderer(model,path,expected_descriptor_sha256=sha,root=root,version_lookup=lambda _:'fixture')
