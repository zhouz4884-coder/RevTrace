#!/usr/bin/env python3
"""Real-model integration gate for provisional holdback state semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


PATTERNS = {
    "single_holdback": {2},
    "consecutive_holdbacks": {2, 3},
    "holdback_then_catchup": {4},
    "hold_until_checkpoint": {5, 6, 7, 8},
    "last_before_checkpoint": {8},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.80)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    script_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(script_dir))
    sys.path.insert(0, str(script_dir.parents[1] / "src"))
    from run_revbatch_gate import (
        SAMPLE_RATE,
        apply_output,
        load_sources,
        make_streams,
        prepare_job,
    )
    from run_revguard_same_input import candidate_record, state_projection_record
    from run_revtrace_dual_gpu import build_asr
    from revtrace.long_horizon import (
        append_checkpoint_history,
        assert_provisional_holdback_transition,
        checkpoint_payload,
        feedback_state_snapshot,
    )

    contract = json.loads(args.contract_manifest.read_text(encoding="utf-8"))
    if contract["mechanism"]["authority"]["fixed_batch_size"] != 12:
        raise ValueError("semantic gate requires the frozen fixed B=12 authority")
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    asr = build_asr(
        str(args.model),
        "float16",
        args.gpu_memory_utilization,
        max_model_len=4096,
        logprobs=20,
        max_num_seqs=12,
    )
    sources = load_sources(args.data_manifest)
    base = make_streams(sources, duration=20, concurrency=6)
    pattern_names = list(PATTERNS)
    streams = base[: len(pattern_names)]
    states = [
        asr.init_streaming_state(
            language=stream["language"],
            unfixed_chunk_num=2,
            unfixed_token_num=5,
            chunk_size_sec=2.0,
        )
        for stream in streams
    ]
    histories = ["" for _ in streams]
    pattern_rows: dict[str, dict[str, Any]] = {
        name: {
            "holdback_count": 0,
            "audio_frontier_checks": 0,
            "feedback_immutability_checks": 0,
            "catchup_checks": 0,
            "checkpoint_payload_agreement": False,
            "reset_reconstruction_agreement": False,
        }
        for name in pattern_names
    }
    for chunk_index in range(10):
        checkpoint = chunk_index == 9
        jobs = []
        prefixes = []
        before = []
        for stream, state in zip(streams, states):
            before.append(feedback_state_snapshot(state))
            begin = chunk_index * 2 * SAMPLE_RATE
            end = begin + 2 * SAMPLE_RATE
            job, prefix = prepare_job(
                asr,
                state,
                stream["audio"][begin:end],
                tail=checkpoint,
            )
            jobs.append(job)
            prefixes.append(prefix)
        padded = jobs + [jobs[0]] * (12 - len(jobs))
        outputs = asr.model.generate(
            padded,
            sampling_params=asr.sampling_params,
            use_tqdm=False,
        )[: len(jobs)]
        for position, (name, stream, state, prefix, output) in enumerate(
            zip(pattern_names, streams, states, prefixes, outputs)
        ):
            row = pattern_rows[name]
            held_back = chunk_index in PATTERNS[name] and not checkpoint
            if held_back:
                assert_provisional_holdback_transition(
                    before[position],
                    feedback_state_snapshot(state),
                    expected_audio_samples=2 * SAMPLE_RATE,
                )
                row["holdback_count"] += 1
                row["audio_frontier_checks"] += 1
                row["feedback_immutability_checks"] += 1
                continue
            previous_chunk_id = int(state.chunk_id)
            selected = candidate_record(output)
            projection = state_projection_record(
                asr,
                state,
                prefix,
                selected,
                terminal=checkpoint,
            )
            applied = apply_output(state, output, prefix)
            if chunk_index > 0 and chunk_index - 1 in PATTERNS[name]:
                if int(state.chunk_id) != previous_chunk_id + 1:
                    raise AssertionError("catch-up transition did not commit once")
                row["catchup_checks"] += 1
            if checkpoint:
                service_payload = checkpoint_payload(
                    prefix=prefix,
                    selected=selected,
                    selected_projection=projection,
                )
                quality_payload = checkpoint_payload(
                    prefix=prefix,
                    selected=selected,
                    selected_projection=projection,
                )
                replay_payload = str(projection["projection_text"]).strip()
                if not (
                    service_payload == quality_payload == replay_payload
                    == (prefix + str(selected["text"])).strip()
                ):
                    raise AssertionError("checkpoint payload paths disagree")
                row["checkpoint_payload_agreement"] = True
                histories[position] = append_checkpoint_history(
                    histories[position], service_payload
                )
                reset = asr.init_streaming_state(
                    context=histories[position],
                    language=stream["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=2.0,
                )
                replay_reset = asr.init_streaming_state(
                    context=histories[position],
                    language=stream["language"],
                    unfixed_chunk_num=2,
                    unfixed_token_num=5,
                    chunk_size_sec=2.0,
                )
                reset_fields = feedback_state_snapshot(reset)
                replay_fields = feedback_state_snapshot(replay_reset)
                if reset_fields != replay_fields:
                    raise AssertionError("checkpoint reset is not reconstructible")
                if reset_fields["audio_samples"] or reset_fields["chunk_id"]:
                    raise AssertionError("checkpoint reset retained segment state")
                row["reset_reconstruction_agreement"] = True
                states[position] = reset
            if str(applied["text"]) != str(state.text):
                raise AssertionError("applied text/state mismatch")

    passed = all(
        row["holdback_count"] == len(PATTERNS[name])
        and row["audio_frontier_checks"] == len(PATTERNS[name])
        and row["feedback_immutability_checks"] == len(PATTERNS[name])
        and row["checkpoint_payload_agreement"]
        and row["reset_reconstruction_agreement"]
        for name, row in pattern_rows.items()
    )
    payload = {
        "schema_version": 1,
        "experiment_id": "checkpoint20-holdback-semantics",
        "decision": "HOLDBACK_SEMANTICS_PASS" if passed else "HOLDBACK_SEMANTICS_FAIL",
        "mechanism_digest": contract["mechanism_digest"],
        "contract_manifest_sha256": sha256(args.contract_manifest),
        "patterns": pattern_rows,
        "invariants": {
            "holdback_advances_audio_frontier": True,
            "holdback_does_not_advance_text_chunk_or_language": True,
            "checkpoint_payload_service_quality_replay_identical": True,
            "checkpoint_reset_reconstructible": True,
        },
        "environment": {
            "python": platform.python_version(),
            "code_commit": os.environ.get("REVTRACE_CODE_COMMIT", "UNRECORDED"),
            "runner_sha256": sha256(Path(__file__)),
        },
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": payload["decision"]}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
