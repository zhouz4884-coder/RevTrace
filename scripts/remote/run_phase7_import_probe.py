#!/usr/bin/env python3
"""Fail-preserving import probe for source baselines."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", choices=("sglang-asr", "llm42-text"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source))
    payload: dict[str, object] = {
        "schema_version": 1,
        "target": args.target,
        "source": str(args.source),
    }
    try:
        import sglang

        payload["import_sglang"] = "pass"
        payload["sglang_version"] = getattr(sglang, "__version__", "unknown")
    except Exception as error:
        payload["import_sglang"] = "fail"
        payload["sglang_error"] = repr(error)
        payload["traceback"] = traceback.format_exc()
    if args.target == "sglang-asr" and payload["import_sglang"] == "pass":
        try:
            from sglang.srt.models.qwen3_asr import (  # noqa: F401
                Qwen3ASRForConditionalGeneration,
            )

            payload["qwen3_asr_model_import"] = "pass"
        except Exception as error:
            payload["qwen3_asr_model_import"] = "fail"
            payload["qwen3_asr_error"] = repr(error)
            payload["qwen3_asr_traceback"] = traceback.format_exc()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
