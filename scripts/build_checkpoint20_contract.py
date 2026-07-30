#!/usr/bin/env python3
"""Build the single immutable checkpoint-20 mechanism manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-name", default="Qwen3-ASR-0.6B")
    parser.add_argument("--margin-threshold", type=float, default=0.031251)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from revtrace.contract_manifest import mechanism_manifest

    identity = json.loads(args.identity.read_text(encoding="utf-8"))
    payload = mechanism_manifest(
        model_name=args.model_name,
        model_fingerprint=identity["model_fingerprint"],
        data_manifest_sha256=identity["data_manifest_sha256"],
        authority_runtime_sha256=identity["authority_runtime_sha256"],
        duration_seconds=120,
        checkpoint_seconds=20,
        margin_threshold=args.margin_threshold,
    )
    payload["identity_environment"] = identity.get("environment", {})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
