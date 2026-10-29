#!/usr/bin/env python3
"""Read-only PDF/log checks using installed Poppler tools; no compilation.

Writes QA evidence only when --output is given. A passing automatic gate still
requires root's visual review of every final page and submission metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


class QAError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_tool(binary: str, args: list[str]) -> str:
    executable = shutil.which(binary) if not Path(binary).is_file() else binary
    if not executable:
        raise QAError(f"Required installed PDF tool unavailable: {binary}; no installation attempted")
    result = subprocess.run([str(executable), *args], capture_output=True, timeout=60)
    if result.returncode:
        raise QAError(f"{Path(binary).name} exited {result.returncode}: {result.stderr.decode('utf-8', errors='replace')[:1000]}")
    if len(result.stdout) > 16 * 1024 * 1024:
        raise QAError("PDF inspection output exceeds bounded 16 MiB limit")
    return result.stdout.decode("utf-8", errors="replace")


def font_check(text: str) -> dict:
    rows, unparsed = [], []
    for line in text.splitlines()[2:]:
        if not line.strip():
            continue
        m = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+(\d+)\s+(\d+)\s*$", line)
        if not m:
            unparsed.append(line)
            continue
        rows.append({"description": line[:m.start()].strip(), "embedded": m.group(1) == "yes",
                     "subset": m.group(2) == "yes", "unicode": m.group(3) == "yes",
                     "type3": bool(re.search(r"\bType\s*3\b", line, re.I))})
    return {"status": "PASS" if rows and not unparsed and all(r["embedded"] and not r["type3"] for r in rows) else "FAIL",
            "font_count": len(rows), "fonts": rows, "unparsed_rows": unparsed}


def reference_pages(text: str, expected_pages: int, max_technical: int) -> dict:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != expected_pages:
        return {"status": "INDETERMINATE", "reason": f"Extracted {len(pages)} pages vs pdfinfo {expected_pages}"}
    headings = []
    for index, page in enumerate(pages):
        # IEEE small caps commonly extract as "R EFERENCES".
        hits = [line for line in re.finditer(r"(?m)^[^\r\n]*$", page)
                if re.sub(r"\s+", "", line.group()).upper() == "REFERENCES"]
        headings.extend((index, hit) for hit in hits)
    if len(headings) != 1:
        return {"status": "INDETERMINATE", "reason": f"Expected one standalone References heading, found {len(headings)}"}
    index, heading = headings[0]
    # Standalone page numbers are the only pre-heading text ignored. A title,
    # conclusion, or AI disclosure above REFERENCES makes this a mixed page.
    prefix = pages[index][:heading.start()]
    before = [line.strip() for line in prefix.splitlines() if line.strip() and not re.fullmatch(r"\d+", line.strip())]
    refs_only = not before
    technical_pages = index + (not refs_only)
    suspicious = []
    ref_numbers = []
    for number, page in enumerate(pages[index:], index + 1):
        content = page[heading.end():] if number == index + 1 else page
        # IEEE bibliography text itself may contain headings in titles, so only
        # section-like isolated lines at the left margin trigger manual review.
        for line in content.splitlines():
            clean = line.strip()
            compact = re.sub(r"\s+", "", clean).upper()
            if re.fullmatch(r"(?:APPENDIX[A-Z]?|SUPPLEMENT(?:ARYMATERIAL)?|ACKNOWLEDG(?:E)?MENTS|AITOOLUSAGE)", compact):
                suspicious.append({"page": number, "text": clean})
            ref_numbers.extend(int(x) for x in re.findall(r"(?:^|\s)\[(\d+)\]\s", line))
    status = "PASS" if refs_only and technical_pages <= max_technical and ref_numbers and not suspicious else "FAIL"
    return {"status": status, "technical_pages": int(technical_pages), "max_technical_pages": max_technical,
            "references_start_page": index + 1, "reference_page_count": len(pages) - index,
            "references_start_on_clean_page": refs_only, "text_before_heading": before,
            "reference_numbers_seen": sorted(set(ref_numbers)), "suspicious_post_reference_headings": suspicious,
            "scope": "structural text check; root must visually confirm every references page contains references only"}


def metadata_check(info: str, xmp: str, forbidden_tokens: list[str]) -> dict:
    fields = {}
    for line in info.splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z ]*):\s*(.*)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    problems = []
    allowed_author = re.compile(r"^(?:anonymous(?: submission| authors?)?|anon\.?|)$", re.I)
    for field in ("Author", "Authors"):
        if field in fields and not allowed_author.fullmatch(fields[field]):
            problems.append(f"Non-anonymous {field}: {fields[field]}")
    # XMP may carry an author even when pdfinfo's Author is empty.
    if xmp.strip():
        try:
            tree = ET.fromstring(xmp)
            for element in tree.iter():
                if element.tag.rsplit("}", 1)[-1].lower() in {"creator", "author"}:
                    names = " ".join(" ".join(element.itertext()).split())
                    if not allowed_author.fullmatch(names):
                        problems.append(f"Non-anonymous XMP author: {names}")
        except ET.ParseError as exc:
            problems.append(f"Unparsed XMP metadata; anonymity cannot be decided: {exc}")
    combined = info + "\n" + xmp
    for token in forbidden_tokens:
        if token and token.casefold() in combined.casefold():
            problems.append(f"Forbidden identity token in PDF metadata: {token}")
    if re.search(r"[A-Za-z]:[\\/](?:Users|home)[\\/]|/home/[^/\s]+/|/Users/[^/\s]+/", combined, re.I):
        problems.append("Machine user path in PDF metadata")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", combined):
        problems.append("Email address in PDF metadata")
    return {"status": "PASS" if not problems else "FAIL", "problems": problems,
            "pdfinfo_fields": fields, "xmp_present": bool(xmp.strip()),
            "scope": "metadata only; author self-identification in prose/repository links requires root's visual and source review"}


def logs_check(log: str, blg: str, bbl: str) -> dict:
    patterns = [r"(?:Citation|Reference)[^\n]*(?:undefined|not defined)",
                r"There were undefined (?:references|citations)",
                r"I didn't find a database entry", r"Repeated entry", r"LaTeX Error:", r"Fatal error"]
    messages = []
    for content, name in ((log, "log"), (blg, "blg")):
        for line in content.splitlines():
            if any(re.search(pattern, line, re.I) for pattern in patterns):
                messages.append({"file": name, "line": line})
    if not re.search(r"Output written on\s+", log):
        messages.append({"file": "log", "line": "No successful Output written on marker"})
    if r"\begin{thebibliography}" not in bbl or r"\bibitem" not in bbl:
        messages.append({"file": "bbl", "line": "Missing nonempty compiled bibliography"})
    return {"status": "PASS" if not messages else "FAIL", "messages": messages}


def manifest_check(root: Path) -> dict:
    path = root / "PACKAGING_PROVENANCE.json"
    if not path.is_file():
        return {"status": "FAIL", "reason": "Missing PACKAGING_PROVENANCE.json"}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    issues = []
    for row in manifest["files"]:
        target = (root / row["target"]).resolve()
        if not target.is_relative_to(root) or not target.is_file() or sha(target.read_bytes()) != row["target_sha256"]:
            issues.append(row["target"])
    return {"status": "PASS" if not issues else "FAIL", "issues": issues,
            "manifest_sha256": sha(path.read_bytes()), "registered_files": len(manifest["files"]),
            "cited_keys": manifest["cited_keys"]}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("--pdf", default="main.pdf", help="Relative to release directory")
    parser.add_argument("--max-technical-pages", type=int, default=11)
    parser.add_argument("--pdfinfo", default="pdfinfo")
    parser.add_argument("--pdftotext", default="pdftotext")
    parser.add_argument("--pdffonts", default="pdffonts")
    parser.add_argument("--forbid-token", action="append", default=[], help="Identity token checked in metadata only; repeatable")
    parser.add_argument("--output", type=Path, help="Optional NEW QA directory; without this no file is written")
    args = parser.parse_args()
    try:
        root = args.release.resolve()
        pdf = (root / args.pdf).resolve()
        if not pdf.is_relative_to(root) or not pdf.is_file():
            raise QAError("PDF must exist inside the release directory")
        info = run_tool(args.pdfinfo, [str(pdf)])
        xmp = run_tool(args.pdfinfo, ["-meta", str(pdf)])
        fonts = run_tool(args.pdffonts, [str(pdf)])
        text = run_tool(args.pdftotext, ["-layout", "-enc", "UTF-8", str(pdf), "-"])
        pm = re.search(r"(?m)^Pages:\s*(\d+)", info)
        if not pm:
            raise QAError("pdfinfo returned no page count")
        count = int(pm.group(1))
        for suffix in (".log", ".blg", ".bbl"):
            if not pdf.with_suffix(suffix).is_file():
                raise QAError(f"Missing final build evidence {pdf.with_suffix(suffix).name}")
        log, blg, bbl = (pdf.with_suffix(s).read_text(encoding="utf-8", errors="replace") for s in (".log", ".blg", ".bbl"))
        checks = {"source_snapshot": manifest_check(root),
                  "pagination": reference_pages(text, count, args.max_technical_pages),
                  "fonts": font_check(fonts), "references": logs_check(log, blg, bbl),
                  "anonymity_metadata": metadata_check(info, xmp, args.forbid_token)}
        # Check that cited keys reached the compiled bibliography, including any
        # explicit BST control key (which intentionally has no rendered bibitem).
        manifest_path = root / "PACKAGING_PROVENANCE.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            controls = {e["key"] for e in manifest["bibliography_entries"] if e["type"] == "ieeetranbstctl"}
            rendered = set(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", bbl))
            missing = sorted(set(manifest["cited_keys"]) - controls - rendered)
            checks["cited_keys_rendered"] = {"status": "PASS" if not missing else "FAIL", "missing": missing}
        passed = all(c["status"] == "PASS" for c in checks.values())
        report = {"schema": "revtrace-dsn-release-qa-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
                  "pdf": pdf.relative_to(root).as_posix(), "pdf_sha256": sha(pdf.read_bytes()), "total_pages": count,
                  "checks": checks, "gate": "PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA" if passed else "FAIL_OR_INDETERMINATE",
                  "visual_review": "REQUIRED_ROOT_ALL_PAGES; automatic checks cannot approve visual layout or semantic anonymity"}
        if args.output:
            if args.output.exists():
                raise QAError("QA output directory already exists; use a new version")
            args.output.mkdir(parents=False)
            (args.output / "QA.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            for name, data in (("pdfinfo.txt", info), ("xmp.xml", xmp), ("pdffonts.txt", fonts), ("pages.txt", text)):
                (args.output / name).write_text(data, encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if passed else 2
    except (QAError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"gate": "FAIL_OR_INDETERMINATE", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
