#!/usr/bin/env python3
"""Record root's ACTUAL all-page review after viewing the final rendered PNGs.

This tool cannot inspect layout or approve the paper. The explicit root
attestation records completed human/agent visual inspection, never a planned
review. It binds the inspected PNG bytes, final PDF and passing automatic QA.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import struct
from pathlib import Path

from release_delivery_checks import new_output_path, sha

T = Path(__file__).resolve().parent
R = T.parents[1]


def build_record(release: Path, qa_path: Path, rendered: Path, reviewed_pages: list[int],
                 root_attestation: bool, notes: str, project_root: Path = R) -> dict:
    release, qa_path, rendered, project_root = (p.resolve() for p in (release, qa_path, rendered, project_root))
    if not release.is_relative_to(project_root / "Paper_DSN/revisions") or not release.is_dir():
        raise ValueError("Release must exist inside Paper_DSN/revisions")
    if not qa_path.is_relative_to(release) or not rendered.is_relative_to(release) or not rendered.is_dir():
        raise ValueError("Automatic QA and rendered pages must be inside the selected release")
    if root_attestation is not True or not notes.strip():
        raise ValueError("Actual root review attestation and nonempty review notes are required")
    qa_bytes = qa_path.read_bytes()
    qa = json.loads(qa_bytes)
    if qa.get("gate") != "PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA":
        raise ValueError("Passing automatic QA is required before recording visual review")
    count = qa["total_pages"]
    if type(count) is not int or count < 1 or reviewed_pages != list(range(1, count + 1)):
        raise ValueError("Explicit reviewed page list must cover every final page exactly once in order")
    pdf = release / "main.pdf"
    if sha(pdf.read_bytes()) != qa["pdf_sha256"]:
        raise ValueError("Final PDF changed after automatic QA")
    pages = {}
    for path in rendered.glob("page-*.png"):
        match = re.fullmatch(r"page-(\d+)\.png", path.name)
        if not match or path.is_symlink():
            raise ValueError("Unexpected or symlinked rendered page")
        index = int(match.group(1))
        if index in pages:
            raise ValueError("Duplicate rendered page number")
        data = path.read_bytes()
        if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise ValueError("Rendered page is not a PNG with IHDR")
        width, height = struct.unpack(">II", data[16:24])
        if min(width, height) < 1:
            raise ValueError("Invalid rendered page dimensions")
        pages[index] = {"page": index, "path": path.relative_to(project_root).as_posix(),
                        "bytes": len(data), "sha256": sha(data), "width": width, "height": height}
    if sorted(pages) != reviewed_pages:
        raise ValueError("Rendered PNG set must exactly match all reviewed final pages")
    return {
        "gate": "PASS_ROOT_ALL_PAGE_VISUAL_QA",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pdf": pdf.relative_to(project_root).as_posix(), "pdf_sha256": qa["pdf_sha256"],
        "automated_QA": qa_path.relative_to(project_root).as_posix(),
        "automated_QA_sha256": sha(qa_bytes), "actual_root_visual_review": True,
        "reviewed_pages": reviewed_pages, "technical_pages": qa["checks"]["pagination"]["technical_pages"],
        "references_only_pages": list(range(qa["checks"]["pagination"]["references_start_page"], count + 1)),
        "rendered_max_side_pixels": max(max(p["width"], p["height"]) for p in pages.values()),
        "root_attested_checks": {
            "all_final_pages_actually_viewed": True,
            "readability_layout_and_clipping_reviewed": True,
            "figures_tables_and_reference_pages_reviewed": True,
            "prose_anonymity_reviewed": True,
        },
        "notes": notes.strip(), "rendered_pages": [pages[i] for i in reviewed_pages],
        "scope": "Root attestation after actual image inspection; this script checks artifact identity and completeness, not visual correctness.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--automated-qa", type=Path, required=True)
    parser.add_argument("--rendered-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="NEW record; no overwrites")
    parser.add_argument("--reviewed-pages", required=True, help="Explicit list, e.g. 1,2,3; must cover every final page")
    parser.add_argument("--root-reviewed-all-pages", action="store_true", help="Attest actual completed review of every image for readability, layout, figures/tables, references and prose anonymity")
    parser.add_argument("--notes", required=True, help="Actual findings from root's completed inspection")
    args = parser.parse_args()
    target = new_output_path(args.output, T, ".json")
    pages = [int(value) for value in args.reviewed_pages.split(",")]
    record = build_record(args.release, args.automated_qa, args.rendered_directory, pages,
                          args.root_reviewed_all_pages, args.notes)
    with target.open("x", encoding="utf-8") as output:
        output.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "rendered_pages"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
