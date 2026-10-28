"""CPU control-flow/clock tests, not real tokenizer or GPU equivalence evidence."""
import json
import pytest
from revtrace.recovery_profile import RecoveryProfile, recovery_processor


def profile(tmp_path):
    return RecoveryProfile(tmp_path / "timing.jsonl", process_entry_perf=10.0,
                           processor_mode="reuse", clock=lambda: 20.0)


def observation(sid, frontier, at, owner=99.0):
    return dict(session_id=sid, certified_frontier=frontier, observed_perf=at,
                owner_incarnation=owner)


def test_same_first_processor_is_reused_and_legacy_reloads():
    first, second = object(), object()
    calls = []
    def load():
        calls.append(True)
        return second
    assert recovery_processor(first, mode="reuse", load_processor=load) is first
    assert calls == []
    assert recovery_processor(first, mode="legacy_double", load_processor=load) is second
    assert calls == [True]


def test_failed_or_unknown_loader_does_not_fall_back(tmp_path):
    p = profile(tmp_path)
    def fail():
        raise RuntimeError("loader failed")
    with pytest.raises(RuntimeError):
        recovery_processor(object(), mode="legacy_double", load_processor=fail, profile=p)
    assert p.summary()["open_spans"] == []
    assert p.records[-1]["error_type"] == "RuntimeError"
    with pytest.raises(ValueError):
        recovery_processor(None, mode="reuse", load_processor=fail)
    with pytest.raises(ValueError):
        recovery_processor(object(), mode="invalid", load_processor=fail)


def test_real_consumer_clocks_survive_late_target_registration(tmp_path):
    p = profile(tmp_path)
    p.observe_consumer(observation(0, 4, 11.0))
    p.observe_consumer(observation(1, 2, 12.0))
    p.configure_recovery(recovered_frontiers={0: 4, 1: 2}, accepted_frontiers={0: 8, 1: 6},
                         owner_incarnation=99.0, original_origin_perf=1.0)
    assert p.summary()["applied_crossings_perf"] == {"all-old-facts-consumed": 12.0}
    p.observe_consumer(observation(0, 6, 13.0))
    p.observe_consumer(observation(0, 8, 14.0))
    p.observe_consumer(observation(1, 6, 17.0))
    assert p.summary()["applied_crossings_perf"] == {
        "all-old-facts-consumed": 12.0, "first-new-fact-consumed": 13.0,
        "precrash-accepted-debt-consumed": 17.0}
    assert p.summary()["targets"]["origin"] == 1.0


def test_other_owner_and_provisional_only_progress_get_no_credit(tmp_path):
    p = profile(tmp_path)
    p.configure_recovery(recovered_frontiers={0: 4}, accepted_frontiers={0: 8},
                         owner_incarnation=99.0, original_origin_perf=1.0)
    p.observe_consumer(observation(0, 8, 11.0, owner=98.0))
    p.observe_consumer({**observation(0, 4, 12.0), "valid_visible_frontier": 10})
    assert p.summary()["applied_crossings_perf"] == {"all-old-facts-consumed": 12.0}


def test_no_debt_stays_not_applicable_and_unknown_is_not_zero(tmp_path):
    p = profile(tmp_path)
    p.configure_recovery(recovered_frontiers={0: 0}, accepted_frontiers={0: 0},
                         owner_incarnation=99.0, original_origin_perf=1.0)
    assert not p.summary()["has_old_facts"]
    assert not p.summary()["has_precrash_debt"]
    assert p.summary()["applied_crossings_perf"] == {}


def test_profile_is_readable_and_targets_cannot_be_relabelled(tmp_path):
    p = profile(tmp_path)
    with p.span("CPU-fixture"):
        pass
    p.configure_recovery(recovered_frontiers={0: 2}, accepted_frontiers={0: 4},
                         owner_incarnation=99.0, original_origin_perf=1.0)
    with pytest.raises(ValueError):
        p.configure_recovery(recovered_frontiers={0: 4}, accepted_frontiers={0: 4},
                             owner_incarnation=100.0, original_origin_perf=20.0)
    assert all(json.loads(line) for line in (tmp_path / "timing.jsonl").read_text().splitlines())
