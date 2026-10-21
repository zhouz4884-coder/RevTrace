from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RevTraceDeployedGateTest(unittest.TestCase):
    def test_summary_contract_if_present(self) -> None:
        path = (
            ROOT
            / "results"
            / "phase1"
            / "deployed_v1"
            / "summary.json"
        )
        if not path.exists():
            self.skipTest("deployed RevTrace summary is not present")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["decision"],
            "DEPLOYED_SYSTEM_GATE_PASS_"
            "DETERMINISTIC_CERTIFICATE_UNRESOLVED",
        )
        self.assertEqual(payload["gates"]["deployed_service"], "PASS")
        self.assertEqual(payload["gates"]["flip_rich_stress"], "PASS")
        self.assertEqual(
            payload["gates"]["generic_wsir_novelty"], "REJECTED_BY_D0"
        )
        self.assertEqual(
            payload["gates"]["deterministic_margin_certificate"],
            "NOT_ESTABLISHED",
        )
        for row in payload["rows"]:
            self.assertGreaterEqual(row["wall_speedup"], 4.0)
            self.assertGreaterEqual(row["slo_goodput_speedup"], 4.0)
            self.assertEqual(row["output_violations"], 0)
            self.assertEqual(row["state_violations"], 0)
            self.assertEqual(row["stale_commits"], 0)
            self.assertGreaterEqual(row["stress_mismatches"], 50)
            self.assertEqual(row["stress_false_safe"], 0)


if __name__ == "__main__":
    unittest.main()
