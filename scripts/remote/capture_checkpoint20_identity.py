#!/usr/bin/env python3
"""Capture immutable model, data, runtime, and runner identities."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import subprocess
import sys
from pathlib import Path


MODEL_FILES = (
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data-manifest", type=Path, required=True)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(__file__).resolve().parents[2] / "src"
    sys.path.insert(0, str(source_dir))
    from revtrace.contract_manifest import fingerprint_files, sha256_file

    weight_files = sorted(
        path.name
        for path in args.model.iterdir()
        if path.is_file()
        and path.suffix in {".safetensors", ".bin"}
    )
    selected = [
        name for name in MODEL_FILES if (args.model / name).is_file()
    ] + weight_files
    model = fingerprint_files(args.model, selected)
    try:
        driver = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=driver_version,name",
                "--format=csv,noheader",
            ],
            text=True,
        ).strip().splitlines()
    except Exception:
        driver = []
    runtime = args.runtime
    if runtime is None:
        spec = importlib.util.find_spec(
            "vllm.model_executor.layers.batch_invariant"
        )
        if spec is None or spec.origin is None:
            raise RuntimeError("cannot locate deployed batch-invariant runtime")
        runtime = Path(spec.origin)
    payload = {
        "schema_version": 1,
        "model_root_label": args.model.name,
        "model_fingerprint": model,
        "data_manifest_sha256": sha256_file(args.data_manifest),
        "authority_runtime_path": str(runtime.resolve()),
        "authority_runtime_sha256": sha256_file(runtime),
        "environment": {
            "python": platform.python_version(),
            "gpu_driver_and_name": driver,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
