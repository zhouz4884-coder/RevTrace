"""The observed staggered empty-mode-root case earns zero early audio credit."""
import copy

import pytest

import retirement_audit as audit


def fixture():
    specs={0:dict(duration=2.,offset=3.)}
    consumer=[dict(kind='consumer-view',source_kind='display',session_id=0,
      observed_perf=104.2,server_time=4.1,valid_visible_frontier=16000,certified_frontier=0),
      dict(kind='consumer-view',source_kind='canonical-display',session_id=0,
      observed_perf=105.3,server_time=5.2,valid_visible_frontier=32000,certified_frontier=32000)]
    return dict(specs=specs,consumer=consumer,snapshots=[dict(sessions={'0':dict(accepted=32000)})],
      events=[dict(kind='commit',session_id=0,audio_end_sample=32000)],
      origin=100.,owner_start=100.,fine_seconds=1.,sample_rate=16000,end_perf=106.)


def empty_root(observed=100.2):
    return dict(kind='consumer-view',source_kind='view-mode',session_id=0,
      observed_perf=observed,server_time=observed-100.-.01,canonical_version=0,
      certified_frontier=0,valid_visible_frontier=0,certified_text='',visible_text='',
      certified_transaction=None,certified_Z_sha256=None,certified_P_sha256=None,
      certified_text_sha256=None,no_certified_snapshot_yet=True,joined_suffix=False,
      compatible_provisional_retained=False,envelope_mode='RECOVERY')


def test_actual_empty_genesis_controls_before_arrival_change_no_audio_credit_or_deadline():
    data=fixture();expected=audit.recount_progress(**data)
    data['consumer']=[empty_root(),dict(empty_root(100.3),envelope_mode='NORMAL')]+data['consumer']
    actual=audit.recount_progress(**data)
    assert actual==expected
    frontiers,sessions,progress,certified=actual
    assert [r['original_ready_perf'] for r in frontiers]==[104.,105.]
    assert [r['first_actual_visible_perf'] for r in frontiers]==[104.2,105.3]
    assert progress[0][0]==(104.2,16000)
    assert certified[0][0]==(105.3,32000)


@pytest.mark.parametrize('change',[
    {'valid_visible_frontier':1},{'certified_frontier':1,'valid_visible_frontier':1},
    {'visible_text':'premature text'},{'certified_text':'premature text'},
    {'canonical_version':1},{'certified_transaction':'non-genesis'},
    {'certified_Z_sha256':'selected-Z'},{'certified_P_sha256':'selected-P'},
    {'certified_text_sha256':'selected-text'}, {'no_certified_snapshot_yet':False},
    {'source_kind':'display'}, {'joined_suffix':True}, {'compatible_provisional_retained':True},
])
def test_genesis_exception_cannot_hide_premature_audio_text_or_selected_state(change):
    data=fixture();data['consumer'].insert(0,dict(empty_root(),**change))
    with pytest.raises(AssertionError,match='Consumer precedes source arrival'):
        audit.recount_progress(**data)


def test_empty_root_still_requires_actual_observation_after_server_publication():
    data=fixture();data['consumer'].insert(0,dict(empty_root(),server_time=1.))
    with pytest.raises(AssertionError,match='credit taken before actual Consumer observation'):
        audit.recount_progress(**data)


def test_positive_audio_after_source_birth_but_before_original_audio_release_still_fails():
    data=fixture();early=copy.deepcopy(data['consumer'][0])
    early.update(observed_perf=103.1,server_time=3.)
    data['consumer'].insert(0,early)
    with pytest.raises(AssertionError,match='frontier credited before original input release'):
        audit.recount_progress(**data)
