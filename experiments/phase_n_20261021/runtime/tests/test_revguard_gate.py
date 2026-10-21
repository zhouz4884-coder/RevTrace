from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from revtrace.core import (
    margin_certifies_argmax,
    pipeline_speedup_lower_bound,
    single_gpu_selective_speedup,
)


ROOT = Path(__file__).resolve().parents[1]


class RevGuardGateTest(unittest.TestCase):
    def test_margin_certificate_is_strict(self) -> None:
        self.assertTrue(margin_certifies_argmax(0.21, 0.10))
        self.assertFalse(margin_certifies_argmax(0.20, 0.10))
        self.assertFalse(margin_certifies_argmax(0.19, 0.10))
        with self.assertRaises(ValueError):
            margin_certifies_argmax(-0.1, 0.0)

    def test_pipeline_and_single_gpu_cost_models(self) -> None:
        self.assertAlmostEqual(
            single_gpu_selective_speedup(75.0, 10.0, 15.0), 3.0
        )
        self.assertAlmostEqual(
            pipeline_speedup_lower_bound(75.0, 10.0, 15.0), 5.0
        )

    def test_contract_separates_empirical_and_deterministic_claims(self) -> None:
        config = json.loads(
            (ROOT / "configs" / "revguard_mechanism_gate.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(config["frozen_margin_threshold"], 1.0)
        self.assertEqual(config["m2_empirical"]["held_out_false_safe_events"], 0)
        self.assertIn(
            "not a deterministic certificate",
            config["m2_empirical"]["claim_boundary"],
        )
        self.assertTrue(config["sequential_stop"])

    def test_remote_runners_are_syntactically_valid(self) -> None:
        for name in [
            "run_revguard_same_input.py",
            "run_revguard_selective.py",
        ]:
            source = (
                ROOT / "scripts" / "remote" / name
            ).read_text(encoding="utf-8")
            ast.parse(source)
        same_input = (
            ROOT / "scripts" / "remote" / "run_revguard_same_input.py"
        ).read_text(encoding="utf-8")
        for marker in [
            "singleton_a",
            "singleton_b",
            "batch_a",
            "batch_b",
            "identical_job_replica_probe",
            "input_sha256",
            "state_projection_record",
            "state_projection_token_exact",
        ]:
            self.assertIn(marker, same_input)

    def test_frozen_summary_preserves_gate_boundaries(self) -> None:
        path = (
            ROOT
            / "results"
            / "phase0"
            / "revguard"
            / "revguard_v1"
            / "summary.json"
        )
        if not path.exists():
            self.skipTest("RevGuard summary is not present")
        summary = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(summary["gates"]["m1_same_input_mechanism"], "PASS")
        self.assertEqual(summary["gates"]["m1_fp32_shape_stability"], "PASS")
        self.assertEqual(
            summary["gates"]["m2_deterministic_margin_certificate"],
            "NOT_ESTABLISHED",
        )
        self.assertEqual(summary["gates"]["m3_live_selective_oracle"], "PASS")
        self.assertEqual(summary["gates"]["m4_verifier_fully_hidden"], "FAIL")


if __name__ == "__main__":
    unittest.main()
