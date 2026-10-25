import importlib.util
from pathlib import Path
import pytest
from revtrace.standard_safe_async import expired,covered_indices
spec=importlib.util.spec_from_file_location('standard_fixture',Path(__file__).with_name('test_properties_abc.py'));f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
@pytest.mark.parametrize('rho',[1,3])
@pytest.mark.parametrize('proposal,authority',[(.001,.05),(.025,.001),(.004,.01)])
def test_standard_control_equivalent_on_full_fake_history(rho,proposal,authority):
 histories=[]
 for implementation in ['revtrace','standard']:
  s=f.build(rho=rho,proposal=proposal,authority=authority);s.contract['async_implementation']=implementation;s.run()
  histories.append([(e['kind'],e.get('session_id'),e.get('version'),e.get('audio_end_sample'),e.get('text')) for e in s.events if e['kind'] in ['display','canonical-display','commit']]);s.close()
 assert histories[0]==histories[1]
def test_covered_selection_and_old_parent_not_invalidation():
 assert list(covered_indices(2,[2,4,6,7],6))==[2,3]
 assert list(covered_indices(4,[2,4,6,7],7))==[4]
 assert not expired(8,3,6,3) and expired(6,3,6,3) and expired(8,2,6,3)
