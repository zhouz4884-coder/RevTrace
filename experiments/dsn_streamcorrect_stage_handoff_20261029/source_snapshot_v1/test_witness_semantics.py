import unittest
from native_audit import meaningful_selection
class NonemptyWitness(unittest.TestCase):
    def test_empty_repeat_cannot_be_a_positive_unchanged_witness(self):
        x=meaningful_selection(dict(previous_transcription='你好',candidates=['你好'],corrected_appended_text=''))
        self.assertFalse(x['nonempty_content']);self.assertFalse(x['changed'])
    def test_real_unchanged_continuation_is_not_filtered(self):
        x=meaningful_selection(dict(previous_transcription='你好',candidates=['你好世界'],corrected_appended_text='世界'))
        self.assertTrue(x['nonempty_content']);self.assertFalse(x['changed'])
    def test_real_deletion_correction_still_counts_as_changed(self):
        x=meaningful_selection(dict(previous_transcription='你好',candidates=['你好错误'],corrected_appended_text=''))
        self.assertTrue(x['nonempty_content']);self.assertTrue(x['changed'])
if __name__=='__main__':unittest.main()
