from __future__ import annotations

import ast
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_finalizer():
    path = ROOT / "scripts" / "finalize_revbatch_gate.py"
    spec = importlib.util.spec_from_file_location("revbatch_finalizer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RevBatchGateTest(unittest.TestCase):
    def test_gate_contract_is_sequential_and_dual_model(self) -> None:
        config = json.loads(
            (ROOT / "configs" / "revbatch_gate.json").read_text(encoding="utf-8")
        )
        self.assertTrue(config["sequential_stop"])
        self.assertEqual(len(config["models"]), 2)
        self.assertTrue(config["gate_a"]["required_for_both_models"])
        self.assertEqual(config["gate_b"]["minimum_chunk_events"], 1000)
        self.assertTrue(config["gate_c"]["run_only_if_gate_a_and_gate_b_pass"])

    def test_runner_is_syntactically_valid_and_preserves_contract_fields(self) -> None:
        path = ROOT / "scripts" / "remote" / "run_revbatch_gate.py"
        source = path.read_text(encoding="utf-8")
        ast.parse(source)
        for marker in [
            "audio_accum",
            "unfixed_chunk_num",
            "unfixed_token_num",
            "token_exact_match_rate",
            "final_exact_match_rate",
            'mode="singleton"',
            'mode="batched"',
        ]:
            self.assertIn(marker, source)

    def test_remote_setup_uses_only_the_data_disk_for_runtime_state(self) -> None:
        setup = (
            ROOT / "scripts" / "remote" / "setup_revbatch_gate.sh"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "DISK_ROOT=/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9",
            setup,
        )
        for name in [
            "HF_HOME",
            "HF_DATASETS_CACHE",
            "TRITON_CACHE_DIR",
            "PIP_CACHE_DIR",
            "MODELSCOPE_CACHE",
        ]:
            self.assertIn(name, setup)

    def test_gate_helpers_enforce_per_model_exactness_and_performance(self) -> None:
        finalizer = load_finalizer()
        payload = {
            "official_semantics_smoke": {"exact": True},
            "cells": [
                {
                    "audio_throughput_speedup": 1.6,
                    "slo_goodput_speedup": 1.2,
                    "p99_reduction_fraction": 0.1,
                }
            ],
            "aggregate": {
                "event_count": 1000,
                "token_exact_match_rate": 1.0,
                "transcript_exact_match_rate": 1.0,
                "final_exact_match_rate": 1.0,
            },
        }
        self.assertTrue(finalizer.gate_a_model(payload)["pass"])
        self.assertTrue(finalizer.gate_b_model(payload)["pass"])
        payload["aggregate"]["token_exact_match_rate"] = 0.999
        self.assertFalse(finalizer.gate_b_model(payload)["pass"])

    def test_frozen_result_stops_before_gate_c(self) -> None:
        summary_path = (
            ROOT
            / "results"
            / "phase0"
            / "revbatch"
            / "revbatch_v1"
            / "summary.json"
        )
        if not summary_path.exists():
            self.skipTest("formal RevBatch results are not present")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertTrue(summary["gate_a"]["pass"])
        self.assertFalse(summary["gate_b"]["pass"])
        self.assertEqual(
            summary["gate_c"]["status"], "NOT_RUN_SEQUENTIAL_STOP"
        )
        self.assertEqual(
            summary["decision"], "NO_GO_FOR_REVBATCH_EXACT_REVISION_GATE_B"
        )


if __name__ == "__main__":
    unittest.main()
