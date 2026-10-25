import ast,gzip,hashlib,importlib.util,sys,json
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
def module(name):
 s=importlib.util.spec_from_file_location(name,HERE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_collector_parts_reassemble_exact_bytes_not_lines(tmp_path,monkeypatch):
 m=module('collect_v6');monkeypatch.setattr(m,'PART',17)
 source=tmp_path/'raw';original=b'first\r\nsecond\n'+bytes(range(100));source.write_bytes(original)
 record=m.compress_file(source,tmp_path/'dest','results/cell/events.jsonl')
 data=b''.join(gzip.decompress((tmp_path/'dest'/p['path']).read_bytes()) for p in record['parts'])
 assert data==original and record['raw_sha256']==hashlib.sha256(original).hexdigest()
 assert record['raw_bytes']==len(original)

def test_empty_and_escaping_payload(tmp_path):
 m=module('collect_v6');source=tmp_path/'empty';source.write_bytes(b'')
 r=m.compress_file(source,tmp_path/'dest','results/empty.log')
 assert len(r['parts'])==1 and gzip.decompress((tmp_path/'dest'/r['parts'][0]['path']).read_bytes())==b''
 with pytest.raises(AssertionError):m.compress_file(source,tmp_path/'dest','../outside')

def test_raw_mutation_during_collection_is_rejected(tmp_path,monkeypatch):
 m=module('collect_v6');source=tmp_path/'raw';source.write_bytes(b'fixed');original=m.gzip.compress
 def corrupt(data,**kw):
  source.write_bytes(b'changed-longer');return original(data,**kw)
 monkeypatch.setattr(m.gzip,'compress',corrupt)
 with pytest.raises(AssertionError,match='changing raw'):m.compress_file(source,tmp_path/'dest','results/raw')

def test_paired_ratios_do_not_turn_frontiers_into_independent_runs():
 m=module('summarize_v6');x={i:{'metric':10.,'WER':.1} for i in range(3)};y={i:{'metric':11.,'WER':.12} for i in range(3)}
 r=m.paired(x,y,'metric');assert r['n']==3 and r['not_independent_sources']
 assert abs(r['mean']-.1)<1e-12 and all(abs(v-.1)<1e-12 for v in r['small_n_t95'])
 assert abs(m.paired(x,y,'WER')['mean']-.02)<1e-12

def test_zero_reference_is_not_an_infinite_speedup():
 m=module('summarize_v6');assert m.paired({0:{'metric':0}},{0:{'metric':1}},'metric')['status']=='ZERO_BASE_REPORTED_WITHOUT_RATIO'

def test_local_review_counts_actual_cells_not_quality_component_index():
    m=module('local_event_review_v6_v2');assert m.verified_count(24,[{} for _ in range(24)])==24
    with pytest.raises(AssertionError):m.verified_count(24,[{} for _ in range(3)])

@pytest.mark.parametrize('name',['analyze_C_v2','audit_anchor_policy_v2','audit_C_actionability','analyze_D_opportunities'])
def test_actual_cell_iterator_uses_frozen_manifest_not_journal_directory(tmp_path,name):
    from types import SimpleNamespace
    (tmp_path/'C').mkdir();(tmp_path/'C/journals').mkdir();(tmp_path/'C/planned-a').mkdir()
    (tmp_path/'C_SUMMARY.json').write_text(json.dumps({'completed':['planned-a','missing-b']}))
    tree=ast.parse((HERE/(name+'.py')).read_text())
    loop=next(n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='C')
    expression=ast.Expression(loop.iter);ast.fix_missing_locations(expression)
    env={'O':tmp_path,'a':SimpleNamespace(stage='C'),'stage':'C','json':json,'read':lambda p:json.loads(p.read_text())}
    paths=eval(compile(expression,'actual-iterator','eval'),env)
    assert [p.name for p in paths]==['missing-b','planned-a']
    # Missing planned evidence remains a failure, not silently filtered.
    assert not paths[0].exists() and all(p.name!='journals' for p in paths)
