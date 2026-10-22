from test_live_qwen import build
import pytest
@pytest.mark.parametrize('rho',[1,2,3])
def test_all_allowed_fixed_intervals_are_real_complete_coverage(rho):
 s=build(rho=rho,barrier='decoupled');r=s.run()
 for sid in s.sessions:
  commits=[e for e in s.events if e['kind']=='commit' and e['session_id']==sid]
  prior=0
  for e in commits:
   assert e['audio_start_sample']==prior and 0<e['audio_end_sample']-prior<=rho*160
   prior=e['audio_end_sample']
  assert prior==960
 assert r['fine_window_accounting_complete']
