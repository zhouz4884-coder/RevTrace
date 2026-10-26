"""Same-clock legal-oracle checks of v2 cached versus uncached accounting.

Not equivalence to v1's wall-clock/tick-dependent tie order or a GPU speedup.
"""
import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('event_env_fixture',Path(__file__).with_name('test_certified_envelope.py'))
f=importlib.util.module_from_spec(s);s.loader.exec_module(f)

def history(e):return [{k:r[k] for k in ['session_id','parent','version','audio_start_sample','audio_end_sample','segment_tokens','next_prompt_tokens']} for r in e if r['kind']=='commit']
def decisions(e):
    result=[]
    for r in e:
        if r['kind']=='input-ack':result.append((r['session_id'],r['from_sample'],r['to_sample'],r['prefix_sha256']))
        elif r['kind']=='input-session-rejected':result.append(('reject',r['session_id'],r['reason']))
    return result

@pytest.mark.parametrize('method',['fine_fair','cde_full','queue_expiry','dgft_original'])
def test_cache_preserves_all_fixed_clock_admission_and_input_obligations(tmp_path,method):
    a,_,ea=f.build(tmp_path/'a',method=method,count=5,adelay=.04)
    ra=a.run();a.close()
    b,_,eb=f.build(tmp_path/'b',method=method,count=5,adelay=.04)
    b._diagnostic_disable_ingress_cache=True
    rb=b.run();b.close()
    assert history(ea)==history(eb) and decisions(ea)==decisions(eb)
    assert ra['final_input_snapshot']==rb['final_input_snapshot']
    assert ra['ingress_noop_skips']>0 and rb['ingress_noop_skips']==0
    assert ra['ingress_transactions']<rb['ingress_transactions']

def test_accepted_backlog_reaches_ingress_fixed_point_without_a_future_tick(tmp_path):
    a,_,_=f.build(tmp_path,method='dgft_original',count=1)
    a._stream_applied=True;a.mode=__import__('revtrace.degradation_state',fromlist=['Mode']).Mode.NORMAL
    a.clock.sleep(.1);a._ingress()
    # Binary100+.1 subtraction can conservatively fall just below the tenth
    # release. The oracle is the actually offered prefix, never future audio.
    assert a.book.session(0).accepted==a.book.session(0).offered>=9*160
    a.close()
