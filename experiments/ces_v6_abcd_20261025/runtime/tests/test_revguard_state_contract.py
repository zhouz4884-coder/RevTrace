from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RevGuardStateContractTest(unittest.TestCase):
    def test_frozen_summary_if_present(self) -> None:
        path = (
            ROOT
            / "results"
            / "phase0"
            / "revguard"
            / "revguard_n1"
            / "summary.json"
        )
        if not path.exists():
            self.skipTest("state-contract summary is not present")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["decision"],
            "LIVE_MECHANISM_GATE_PASS_"
            "DETERMINISTIC_CERTIFICATE_UNRESOLVED",
        )
        self.assertEqual(
            payload["default_bf16_state_projection"][
                "state_projection_mismatch_events"
            ],
            16,
        )
        for run in payload["live_runs"]:
            self.assertEqual(run["policy_violation_events"], 0)
            self.assertEqual(
                run["policy_state_projection_violation_events"], 0
            )
            self.assertLessEqual(run["verification_fraction"], 0.1)
            self.assertLessEqual(
                run["verifier_to_proposer_service_ratio"], 0.8
            )

    def test_report_preserves_certificate_boundary(self) -> None:
        text = (
            ROOT / "docs" / "reports" / "revguard_state_contract_report.md"
        ).read_text(encoding="utf-8")
        self.assertIn("not yet a deterministic margin certificate", text)
        self.assertIn("Only 1/17 was absorbed by rollback", text)
        self.assertIn("FP32 remains a stable alternative", text)


if __name__ == "__main__":
    unittest.main()
