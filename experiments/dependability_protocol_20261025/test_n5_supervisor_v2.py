"""CPU-only resource ownership barrier regressions."""
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('supervisor',Path(__file__).with_name('run_n5_validation_v2.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_delayed_owned_release_waits_without_killing(monkeypatch):
 answers=iter(['42\n','42\n','']);monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**k:next(answers))
 monkeypatch.setattr(m.time,'sleep',lambda n:None)
 def forbidden(*a):raise AssertionError('no process deletion permitted by barrier')
 monkeypatch.setattr(m.os,'killpg',forbidden,raising=False)
 result=m.wait_own_driver_release([dict(pid=42)]);assert len(result)==2
def test_other_task_causes_immediate_stop(monkeypatch):
 monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**k:'43\n')
 with pytest.raises(AssertionError,match='another task'):m.wait_own_driver_release([dict(pid=42)])
def test_empty_is_immediate(monkeypatch):
 monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**k:'')
 assert m.wait_own_driver_release([dict(pid=42)])==[]
