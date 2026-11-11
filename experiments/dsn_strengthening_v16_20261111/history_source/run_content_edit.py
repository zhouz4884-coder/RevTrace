"""Formal read-only CPU entry; requires clean frozen source and prelaunch record."""
from __future__ import annotations
import argparse
from collections import defaultdict
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import traceback
import unittest
from content_edit import analyze_rows, checked_json, checked_rows, sha256
from historical_pairs import audit_metadata
from speaker_sensitivity import recount_new8


def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def digest(p): return sha256(Path(p).read_bytes())
def put(p, value):
    with Path(p).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")


def source_gate(manifest):
    root = Path(__file__).resolve().parent
    def git(*args): return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("source must be its own frozen checkout")
    if git("rev-parse", "HEAD") != manifest["code_commit"]:
        raise ValueError("full execution commit mismatch")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("dirty frozen source")
    files = {x["path"] for x in manifest["files"]}
    if set(git("ls-files").splitlines()) != files:
        raise ValueError("complete source-manifest set mismatch")
    for record in manifest["files"]:
        p = root / record["path"]
        if p.stat().st_size != record["bytes"] or digest(p) != record["sha256"]:
            raise ValueError("source-manifest byte mismatch")


def main():
    p = argparse.ArgumentParser()
    for key in ("config", "source-manifest", "environment", "prelaunch", "out"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    config, manifest, prelaunch = load(a.config), load(a.source_manifest), load(a.prelaunch)
    source_gate(manifest)
    before = {str(f.resolve()): digest(f) for f in (a.config, a.source_manifest, a.environment, a.prelaunch)}
    for key, path in (("frozen_config_sha256", a.config), ("source_manifest_sha256", a.source_manifest),
                      ("environment_sha256", a.environment)):
        if prelaunch[key] != digest(path): raise ValueError("prelaunch hash mismatch: " + key)
    if prelaunch["code_commit"] != manifest["code_commit"]:
        raise ValueError("prelaunch actual source commit mismatch")
    root_gate = Path(prelaunch["root_preflight_path"])
    if digest(root_gate) != prelaunch["root_preflight_sha256"]:
        raise ValueError("root preflight receipt changed")
    root_receipt = load(root_gate)
    if not (root_receipt.get("status", "").startswith("PASS") or
            root_receipt.get("gate", "").startswith("PASS") or
            root_receipt.get("gate") == "SOURCE_IDENTITY_PASS"):
        raise ValueError("root preflight is not PASS")
    if prelaunch["experiment_id"] != config["experiment_id"]:
        raise ValueError("prelaunch experiment ID mismatch")
    if str(a.out.resolve()) != prelaunch["raw_result_location"]:
        raise ValueError("actual raw result path mismatch")
    if config["designated_experiment_disk_prefix"] not in str(a.out.resolve()):
        raise ValueError("output is not on designated experiment disk")
    if len({x["cell_id"] for x in config["cells"]}) != len(config["cells"]):
        raise ValueError("duplicate cell ID")
    a.out.mkdir(parents=True, exist_ok=False)
    put(a.out / "CONFIG.json", config)
    put(a.out / "ENVIRONMENT_FROZEN.json", load(a.environment))
    put(a.out / "ENVIRONMENT_ACTUAL.json", dict(python=sys.version, executable=sys.executable,
        platform=platform.platform(), new_model_calls=0))
    put(a.out / "RUN_RECORD.json", dict(experiment_id=config["experiment_id"],
        code_commit=manifest["code_commit"], source_manifest_sha256=digest(a.source_manifest),
        frozen_config_sha256=digest(a.config), environment_sha256=digest(a.environment),
        raw_result_location=str(a.out.resolve()), aggregate_summary_location=str(a.out / "SUMMARY.json"),
        gate_decision_location=str(a.out / "GATE.json"), inference_tier="offline actual-Consumer text analysis"))
    records, groups, input_hashes = [], defaultdict(list), {}
    try:
        stream = io.StringIO()
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent), pattern="test_*.py")
        registered = suite.countTestCases()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        (a.out / "CPU_CONTROLS.log").write_text(stream.getvalue(), encoding="utf-8")
        put(a.out / "CPU_CONTROLS.json", dict(registered=registered, run=result.testsRun,
            failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped)))
        if not result.wasSuccessful() or result.skipped or result.testsRun != config["expected_controls"]:
            raise ValueError("frozen complete CPU controls did not pass")
        for cell in config["cells"]:
            # Native NN4f, old14 and all110 core use the same observed/text/source_id
            # fields. Adapt paths only; do not add instrumentation to the runtime.
            rows = checked_rows(cell["consumer_path"], cell["consumer_sha256"])
            input_hashes[cell["consumer_path"]] = cell["consumer_sha256"]
            if cell["schema"] == "core":
                rows = [dict(source_id=cell["session_source_map"][str(r["session_id"])],
                    text=r["visible_text"], observed=r["observed_perf"], kind=r["source_kind"])
                    for r in rows]
            elif cell["schema"] != "native": raise ValueError("unknown frozen Consumer schema")
            ll = analyze_rows(rows, config.get("age_threshold_seconds", 2.0))
            source_summaries, events, spans = [], [], []
            for (sid, mode, convention), ledger in sorted(ll.items()):
                meta = dict(cell_id=cell["cell_id"], source_id=sid, mode=mode,
                            convention=convention, bank=cell["bank"], stage=cell["stage"], arm=cell["arm"],
                            cohort=cell.get("cohort"), repeat=cell.get("repeat"))
                summary = dict(meta, **ledger.summary()); source_summaries.append(summary)
                events.extend(dict(meta, **e) for e in ledger.events)
                spans.extend(dict(meta, **s) for s in ledger.spans())
                groups[cell["bank"], cell["stage"], cell["arm"], mode, convention].append(summary)
            records.extend(source_summaries)
            # Every cell gets its own folder to avoid name collisions and RAM growth.
            target = a.out / "cells" / cell["cell_id"]; target.mkdir(parents=True)
            put(target / "SOURCE_SUMMARIES.json", source_summaries)
            put(target / "ACTUAL_EDIT_EVENTS.json", events)
            put(target / "EDIT_AND_LCP_OCCURRENCE_LIFETIMES.json", spans)
        aggregate = []
        for (bank, stage, arm, mode, convention), items in sorted(groups.items()):
            numeric = ("I", "D", "S", "M", "distance", "lcp_suffix_closed", "lcp_suffix_introduced",
                       "retracted_edit_occurrences", "edit_retractions_age_ge_threshold",
                       "final_visible_code_points", "right_censored_survivors", "ambiguous_events",
                       "lcp_retractions_age_ge_threshold")
            aggregate.append(dict(bank=bank, stage=stage, arm=arm, mode=mode, convention=convention,
                cell_count=len({x["cell_id"] for x in items}), source_observations=len(items),
                unique_sources=len({x["source_id"] for x in items}),
                **{k: sum(x.get(k, 0) for x in items) for k in numeric},
                metric_family=items[0]["metric_family"],
                longest_edit_retraction_lifetime_seconds=max(x.get("longest_edit_retraction_lifetime_seconds", 0) for x in items),
                longest_lcp_retraction_lifetime_seconds=max(x.get("longest_lcp_retraction_lifetime_seconds", 0) for x in items)))
        loaded = {}
        for name, spec in config["metadata_inputs"].items():
            loaded[name] = checked_json(spec["path"], spec["sha256"])
            input_hashes[spec["path"]] = spec["sha256"]
        old_expected = loaded["old14_lcp_runs"]
        for cell in config["cells"]:
            actual = [r for r in records if r["cell_id"] == cell["cell_id"] and r["mode"] == "raw"
                      and r["convention"] == "LCP_suffix_identity"]
            if cell["bank"] == "native_old14":
                expected = next(x["raw"] for x in old_expected if x["cell_id"] == cell["cell_id"])
                checks = {"lcp_suffix_closed": "LCP_erased_code_point_occurrences",
                          "lcp_suffix_introduced": "introduced_code_point_occurrences",
                          "final_visible_code_points": "final_observed_text_code_points"}
            else:
                expected = next(x for x in loaded["h3_runs"] if x["cell_id"] == cell["cell_id"])
                checks = {"lcp_suffix_closed": "erased_visible_characters"}
            for new, old in checks.items():
                if sum(x[new] for x in actual) != expected[old]:
                    raise ValueError("original actual-Consumer LCP scope mismatch: " + cell["cell_id"])
        pairs = audit_metadata(loaded["h3_runs"], loaded["h3_opportunities"], loaded["h3_sources"])
        put(a.out / "H3_ALL110_PAIRED_RECOUNT.json", pairs)
        sensitivity = recount_new8(loaded["new8_report"])
        put(a.out / "NEW8_EXACT_PAIRED_AND_LEAVE_OUT.json", sensitivity)
        for path, expected in input_hashes.items():
            if digest(path) != expected: raise ValueError("input changed after read")
        for path, expected in before.items():
            if digest(path) != expected: raise ValueError("config/environment/source record changed")
        if digest(root_gate) != prelaunch["root_preflight_sha256"]:
            raise ValueError("root preflight receipt changed after read")
        source_gate(manifest)
        put(a.out / "INPUT_HASHES.json", input_hashes)
        put(a.out / "SOURCE_SUMMARIES.json", records)
        put(a.out / "AGGREGATE_BY_STAGE_ARM_MODE_CONVENTION.json", aggregate)
        put(a.out / "SUMMARY.json", dict(status="COMPLETE_ALL_FROZEN_CONSUMERS", cells=len(config["cells"]),
            new_model_calls=0, CPU_controls=result.testsRun, aggregates=aggregate,
            metadata_recount=dict(cells=pairs["cells"], blocks=pairs["five_arm_blocks"], acoustic_speakers=24),
            new8_sensitivity=sensitivity,
            uncertainty="Per-event all-optimal bounds condition on that convention's previous identity history; two complete tie-break histories are sensitivity analyses, not global confidence bounds.",
            scope="Minimum Unicode code-point edits, literal actual Consumer observations; no claim of semantic wrong words, token/audio mapping, online support, or deployed counterfactual speed."))
        put(a.out / "GATE.json", dict(status="PASS_ALL_INPUT_BYTES_AND_EDIT_CONSERVATION", cells=len(config["cells"]),
                                    config_environment_and_source_after_checks=True))
    except Exception:
        put(a.out / "GATE.json", dict(status="FAIL_PRESERVED_PARTIAL_OUTPUTS", traceback=traceback.format_exc()))
        raise


if __name__ == "__main__": main()
