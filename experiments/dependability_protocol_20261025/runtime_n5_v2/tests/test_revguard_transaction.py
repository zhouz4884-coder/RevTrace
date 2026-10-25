from __future__ import annotations

import unittest

from revtrace.core import RevisionCommitLedger


class RevisionCommitLedgerTest(unittest.TestCase):
    def test_version_bound_commit_and_replay_rejection(self) -> None:
        ledger = RevisionCommitLedger()
        ledger.register("session")
        first = ledger.issue("session", "session:0")
        competing = ledger.issue("session", "session:0:duplicate")

        self.assertTrue(ledger.can_commit(first))
        self.assertEqual(ledger.commit(first), 1)
        self.assertFalse(ledger.can_commit(first))
        self.assertFalse(ledger.can_commit(competing))
        with self.assertRaises(ValueError):
            ledger.commit(first)
        with self.assertRaises(ValueError):
            ledger.commit(competing)

        second = ledger.issue("session", "session:1")
        self.assertEqual(second.parent_version, 1)
        self.assertEqual(ledger.commit(second), 2)

    def test_registration_and_identity_fail_closed(self) -> None:
        ledger = RevisionCommitLedger()
        ledger.register("s", initial_version=3)
        self.assertEqual(ledger.version("s"), 3)
        with self.assertRaises(ValueError):
            ledger.register("s")
        with self.assertRaises(KeyError):
            ledger.issue("missing", "r")
        ledger.issue("s", "r")
        with self.assertRaises(ValueError):
            ledger.issue("s", "r")


if __name__ == "__main__":
    unittest.main()
