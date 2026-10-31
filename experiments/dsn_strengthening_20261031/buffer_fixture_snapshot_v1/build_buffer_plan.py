"""Pure four-trial plan construction. No GPU, signals, activation or launch."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
from fixture_paths import frozen_path

TARGET_SOURCE = "BAC009S0908W0369"
SEED = 20261031
POSITIVE = "264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169"
NEGATIVE_PRED = "d25f4c1b78a3dbf8603e3184a5073ac5ef464f17e536d47ce8445ba33ad53e17"
NEGATIVE_ACTUAL = "951d27d89c334b8d15689a4ecb0f033a589feaee6a7a2352054cd6ef8b778827"


def load(path):
    return json.loads(Path(path).read_bytes())


def create(path, value):
    with Path(path).open("xb") as stream:
        stream.write((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf8"))


def specification(cell_id, match):
    return dict(schema="revtrace-buffer-fixture-v1", experiment_id=cell_id,
                nonce=hashlib.sha256(f"{SEED}:{cell_id}:controlled-v1".encode()).hexdigest(),
                source_id=TARGET_SOURCE, expect_match=match,
                parent_start=16000 if match else 24000,
                parent_end=24000 if match else 32000, child_end=32000 if match else 40000,
                barrier_timeout_seconds=90, startup_timeout_seconds=360,
                base_nn_commit="4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47",
                base_manifest_sha256="60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457",
                historical_parent_prediction_sha=POSITIVE if match else NEGATIVE_PRED,
                historical_parent_actual_sha=POSITIVE if match else NEGATIVE_ACTUAL)


def build(template, dependencies, raw_root, followup=None):
    if set(dependencies) != {"base", "harness", "fixture"}:
        raise ValueError("all three actual execution source identities must be supplied")
    raw_root = frozen_path(raw_root).as_posix()
    sources = template["settings"]["sources"]
    if len(sources) != 1 or sources[0]["source_id"] != TARGET_SOURCE:
        raise ValueError("four-trial timing target requires the predeclared historical source")
    if followup and followup["source_id"] == TARGET_SOURCE:
        raise ValueError("follow-up needs its own original source identity/reference")
    rng = random.Random(SEED)
    order = [True, False]
    rng.shuffle(order)
    cells = []
    for repeat in range(2):
        for match in (order if repeat == 0 else list(reversed(order))):
            cid = f"SC_BUFFER_DEAD_PRODUCER_{'MATCH' if match else 'MISMATCH'}_20261031_v1_r{repeat}"
            cfg = copy.deepcopy(template)
            cfg.update(cell_id=cid, experiment_id=cid, arm="fullcall", repeat=repeat,
                       position=len(cells), stage="controlled_dead_producer_buffer_witness",
                       fault=dict(kind="none"), maximum_service_seconds=template["maximum_service_seconds"],
                       request_contract="closed_loop_single_outstanding_independent_EOS_v1",
                       maximum_owner_restarts=0, expected_owner_error_types=[],
                       base_nn_source=copy.deepcopy(dependencies["base"]),
                       harness_source=copy.deepcopy(dependencies["harness"]),
                       execution_dependencies=[copy.deepcopy(dependencies[key]) for key in ("base", "harness", "fixture")],
                       timing_fixture=specification(cid, match),
                       scope="Predeclared controlled complete-result receipt / actual producer SIGKILL / original fence / exact-input install or rejection. No natural prevalence or performance-success claim.")
            cfg["settings"]["primary_gpu"] = repeat % 2
            cfg["settings"]["record_resources"] = False
            if followup and match:
                cfg["settings"]["sources"].append(copy.deepcopy(followup))
                bysid = {s["source_id"]: s for s in cfg["settings"]["model_sources"]}
                bysid[followup["source_id"]] = copy.deepcopy(followup)
                cfg["settings"]["model_sources"] = list(bysid.values())
            cfg["request_order"] = [s["source_id"] for s in cfg["settings"]["sources"]]
            destination = str(raw_root).rstrip("/") + "/cells/" + cid
            cfg.update(frozen_raw_root=raw_root, raw_result_location=destination,
                       maximum_process_seconds=900, watchdog_cleanup_seconds=40,
                       watchdog_cli_timeout_seconds=5,
                       watchdog_result_location=raw_root + "/watchdog/" + cid,
                       aggregate_summary_location=destination + "/SUMMARY.json",
                       gate_decision_location=destination + "/BUFFER_WITNESS_GATE.json")
            cells.append(dict(cell_id=cid, repeat=repeat, expect_match=match, primary_gpu=repeat % 2,
                              raw_result_location=destination, aggregate_summary_location=destination + "/SUMMARY.json",
                              gate_decision_location=destination + "/BUFFER_WITNESS_GATE.json", config=cfg))
    return dict(experiment_id="SC_CONTROLLED_BUFFER_FOUR_TRIALS_20261031_v1", seed=SEED,
                expected_trials=4, positive_trials=2, negative_trials=2, cells=cells,
                raw_result_location=str(raw_root), aggregate_summary_location=str(raw_root).rstrip("/") + "/SUMMARY.json",
                gate_decision_location=str(raw_root).rstrip("/") + "/GATE.json",
                followup_requested=bool(followup), GPU_launched=False,
                scope="Complete all four frozen fresh trials, preserving every failed trigger and negative. Fullcall only; match/mismatch order seeded and reversed; primary GPU rotates by repeat.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dependencies", type=Path, required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--followup-source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan = build(load(args.template), load(args.dependencies), args.raw_root,
                 load(args.followup_source) if args.followup_source else None)
    create(args.out, plan)
    print(json.dumps(dict(experiment_id=plan["experiment_id"], trials=len(plan["cells"]), GPU_launched=False)))


if __name__ == "__main__":
    main()
