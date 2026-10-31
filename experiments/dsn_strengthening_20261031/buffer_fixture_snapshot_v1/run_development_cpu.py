"""Explicit development wiring gate; this is not frozen NN/GPU evidence."""
import argparse
import json
import os
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-source", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    scratch = ((args.out.parent if args.out else Path.cwd()) / "buffer_fixture_development_scratch").resolve()
    scratch.mkdir(exist_ok=True)
    os.environ["REVTRACE_FIXTURE_TEST_ROOT"] = str(scratch)
    sys.path.insert(0, str(args.base_source.resolve()))
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent), pattern="test_buffer_fixture.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    gate = dict(status="PASS_DEVELOPMENT_CPU_BUFFER_FIXTURE" if result.wasSuccessful() else "FAIL_DEVELOPMENT_CPU_BUFFER_FIXTURE",
                tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), source_frozen=False, neural_calls=0,
                real_CPU_process_terminations=sys.modules["test_buffer_fixture"].DEVELOPMENT_CPU_CHILD_TERMINATIONS,
                real_NN_worker_signals=0,
                scope="Synthetic CPU transport/control conformance only, not actual neural completed-buffer survival.")
    if args.out:
        with args.out.open("x", encoding="utf8") as stream: json.dump(gate, stream, indent=2)
    print(json.dumps(gate))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
