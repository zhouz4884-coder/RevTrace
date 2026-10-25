"""Offline scorer units are independent of reference-text deviation."""
from pathlib import Path
import importlib.util

spec=importlib.util.spec_from_file_location("tc_gt",Path(__file__).resolve().parents[1]/"scripts/score_tc_live_ground_truth.py")
# The scorer intentionally reuses the frozen edit-distance implementation.
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_english_normalization_preserves_contractions():
    assert module.tokens("It's A TEST!", "English")==["it's","a","test"]

def test_chinese_scoring_uses_characters_not_english_word_chunks():
    assert module.tokens("中文，GPU１２。", "Chinese")==list("中文gpu12")

def test_edit_error_denominator_is_the_ground_truth():
    reference=module.tokens("one two three four", "English")
    hypothesis=module.tokens("one two four", "English")
    assert module.edits(reference,hypothesis)/len(reference)==0.25
