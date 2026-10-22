import pytest
from r3_core import quality,trajectory_summary,validate_runtime_manifest

def window(i,P,Z,Y):return {'window':i,'P_equal':P,'Z_equal':Z,'Y_equal':Y}
def test_new_Z_equality_is_not_state_equality():
    x=trajectory_summary([window(2,False,True,False)],1)
    assert x['Z']['first_equal_K']==1 and x['P']['first_equal_right_censored']
def test_redivergence_after_first_equal():
    x=trajectory_summary([window(2,True,True,True),window(3,False,True,False)],1)
    assert x['P']['first_equal_K']==1 and x['P']['redivergence_windows']==[2]
def test_source_end_not_infinite_divergence():
    x=trajectory_summary([window(2,False,False,False)],1)
    assert x['P']['first_equal_K'] is None and x['censor_reason']=='source_end'
def test_no_future_data_is_censored():
    x=trajectory_summary([],1,censor_reason='input_limit')
    assert x['observed_future_windows']==0 and x['P']['equal_at_observed_endpoint'] is None
def test_same_error_count_does_not_define_equal_text():
    assert quality('a b','a c')['word_errors']==quality('a b','a d')['word_errors']
    x=trajectory_summary([window(2,False,False,False)],1)
    assert x['Y']['first_equal_K'] is None
def test_Y_can_equal_without_Z():
    x=trajectory_summary([window(2,False,False,True)],1)
    assert x['Y']['first_equal_K']==1 and x['Z']['first_equal_K'] is None
def test_first_equal_then_stays_equal_is_only_observed():
    x=trajectory_summary([window(2,True,True,True),window(3,True,True,True)],1)
    assert x['P']['equal_at_observed_endpoint'] and x['P']['permanent_convergence_not_claimed']
def test_punctuation_normalizer_and_denominator():
    q=quality("Hello, don't!","hello don't")
    assert q['word_errors']==0 and q['reference_words']==2
def test_manifest_schema_catches_missing_language_before_model_load():
    r={'path':'native.flac','source_id':'a','audio_sha256':'sha','duration':32.,'reference':'words'}
    with pytest.raises(ValueError,match='missing worker'):validate_runtime_manifest({'sessions':[r]})
def test_manifest_metadata_repair_does_not_select_different_audio():
    r={'path':'native.flac','source_id':'a','audio_sha256':'sha','duration':32.,'reference':'words'}
    repaired=dict(r,language='English');assert validate_runtime_manifest({'sessions':[repaired]})
    assert all(repaired[k]==v for k,v in r.items())
