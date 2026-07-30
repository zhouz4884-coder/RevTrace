#!/usr/bin/env python3
"""Capture immutable model, data, runtime, and runner identities."""

from __future__ import annotations

import argparse
import importlib.metadata
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


def package_version(*names: str) -> str | None:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def module_source_fingerprint(
    module_name: str,
    *,
    fingerprint_files: object,
) -> dict[str, object]:
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return {"available": False}
    if spec.submodule_search_locations:
        root = Path(next(iter(spec.submodule_search_locations))).resolve()
        relative = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if path.is_file()
        ]
    elif spec.origin is not None:
        origin = Path(spec.origin).resolve()
        root = origin.parent
        relative = [origin.name]
    else:
        return {"available": False}
    fingerprint = fingerprint_files(root, relative)
    return {
        "available": True,
        "module": module_name,
        "source_root_label": root.name,
        **fingerprint,
    }


def main() -> int:
    args = parse_args()
    source_dir = Path(__file__).resolve().parents[2] / "src"
    sys.path.insert(0, str(source_dir))
    from revtrace.contract_manifest import (
        digest_value,
        fingerprint_files,
        sha256_file,
    )

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
        gpus = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid,pci.bus_id,driver_version,name",
                "--format=csv,noheader",
            ],
            text=True,
        ).strip().splitlines()
    except Exception:
        gpus = []
    runtime = args.runtime
    if runtime is None:
        spec = importlib.util.find_spec(
            "vllm.model_executor.layers.batch_invariant"
        )
        if spec is None or spec.origin is None:
            raise RuntimeError("cannot locate deployed batch-invariant runtime")
        runtime = Path(spec.origin)
    manifest = json.loads(args.data_manifest.read_text(encoding="utf-8"))
    data_records: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for raw in manifest["records"]:
        sample_id = str(raw["sample_id"])
        if sample_id in seen_ids:
            raise ValueError(f"duplicate sample_id in manifest: {sample_id}")
        seen_ids.add(sample_id)
        audio = Path(raw["path"])
        if not audio.is_absolute():
            audio = (args.data_manifest.parent / audio).resolve()
        if not audio.is_file():
            raise FileNotFoundError(audio)
        data_records.append(
            {
                "sample_id": sample_id,
                "language": str(raw["language"]),
                "reference": str(raw.get("reference", "")),
                "audio_file_label": audio.name,
                "audio_bytes": audio.stat().st_size,
                "audio_sha256": sha256_file(audio),
            }
        )
    data_records.sort(key=lambda row: str(row["sample_id"]))
    try:
        import torch

        torch_environment: dict[str, object] = {
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
        }
    except Exception as exc:
        torch_environment = {"unavailable": type(exc).__name__}
    try:
        repo_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[2],
            text=True,
        ).strip()
    except Exception:
        repo_commit = "UNRECORDED"
    software = {
        "packages": {
            name: package_version(name)
            for name in (
                "accelerate",
                "numpy",
                "qwen-asr",
                "tokenizers",
                "torch",
                "transformers",
                "triton",
                "vllm",
            )
        },
        "torch_runtime": torch_environment,
        "qwen_asr_source": module_source_fingerprint(
            "qwen_asr",
            fingerprint_files=fingerprint_files,
        ),
        "revtrace_code_commit": repo_commit,
    }
    payload = {
        "schema_version": 2,
        "model_root_label": args.model.name,
        "model_fingerprint": model,
        "data_manifest_sha256": sha256_file(args.data_manifest),
        "data_content": {
            "records": data_records,
            "audio_file_count": len(data_records),
            "content_digest": digest_value(data_records),
            "digest_semantics": (
                "SHA-256 over canonical JSON records containing sample ID, "
                "language, reference, audio byte count, and audio SHA-256"
            ),
        },
        "authority_runtime_path": str(runtime.resolve()),
        "authority_runtime_sha256": sha256_file(runtime),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "gpu_identity": gpus,
            "software": software,
            "code_commit": repo_commit,
            "runner_sha256": sha256_file(Path(__file__).resolve()),
        },
    }
    payload["identity_extension_digest"] = digest_value(
        {
            "model_fingerprint": payload["model_fingerprint"],
            "data_manifest_sha256": payload["data_manifest_sha256"],
            "data_content": payload["data_content"],
            "authority_runtime_sha256": payload[
                "authority_runtime_sha256"
            ],
            "environment": payload["environment"],
        }
    )
    payload["claim_boundary"] = (
        "This post-run content attestation strengthens artifact identity. "
        "Only identities already embedded in the frozen mechanism digest are "
        "claimed as at-run contract fields."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
