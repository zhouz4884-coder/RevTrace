"""Auditable pre-submission checks for the IEEE TC RevTrace manuscript."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "Paper_TC"
REPORT = PAPER / "reports" / "tc_submission_audit.json"


def included_tex_sources() -> list[Path]:
    """Resolve the manuscript's actual input graph, excluding dormant tables."""
    found: list[Path] = []
    seen: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        found.append(path)
        text = path.read_text(encoding="utf-8")
        dependencies = re.findall(r"\\input\{([^}]+)\}", text)
        dependencies += [f"tables/{name}" for name in re.findall(r"\\tbl\{([^}]+)\}", text)]
        for dependency in dependencies:
            child = PAPER / dependency
            if child.suffix != ".tex":
                child = child.with_suffix(".tex")
            if child.exists():
                visit(child)

    visit(PAPER / "main.tex")
    return found


def strip_tex(text: str) -> str:
    text = re.sub(r"%.*", " ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", text)
    return re.sub(r"[{}$~]", " ", text)


def main() -> int:
    sources = included_tex_sources()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    package_sources = [PAPER / "main.tex"]
    package_sources.extend(sorted((PAPER / "sections").glob("*.tex")))
    package_sources.extend(sorted((PAPER / "tables").glob("*.tex")))
    package_text = "\n".join(
        path.read_text(encoding="utf-8") for path in package_sources
    )
    errors: list[str] = []
    warnings: list[str] = []

    abstract_match = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
        (PAPER / "main.tex").read_text(encoding="utf-8"),
        re.S,
    )
    abstract_words = 0
    if not abstract_match:
        errors.append("abstract environment missing")
    else:
        abstract_words = len(
            re.findall(
                r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*",
                strip_tex(abstract_match.group(1)),
            )
        )
        if not 100 <= abstract_words <= 200:
            errors.append(f"abstract has {abstract_words} words; required 100--200")

    pdf_path = PAPER / "main.pdf"
    pages = None
    if not pdf_path.exists():
        errors.append("compiled main.pdf missing")
    else:
        pages = len(PdfReader(pdf_path).pages)
        if pages > 12:
            errors.append(f"main.pdf has {pages} pages; TC target is at most 12")

    required_evidence = {
        "causal denominator": ("21", "8", "0"),
        "revision amplification": ("153",),
        "matched throughput": ("1.39", "1.28"),
        "headline speedup": ("6.88",),
        "accepted-history traces": ("800", "1{,}048"),
        "protocol fuzzer": ("250{,}000",),
        "V100 throughput": ("157.8", "111.7"),
        "V100 display latency": ("1.089", "1.394"),
        "V100 commit latency": ("3.080", "4.890"),
        "host protocol attribution": ("101.107", "81.960", "104.514"),
    }
    missing_evidence: dict[str, list[str]] = {}
    for name, tokens in required_evidence.items():
        missing = [token for token in tokens if token not in combined]
        if missing:
            missing_evidence[name] = missing
            errors.append(f"missing protected evidence for {name}: {', '.join(missing)}")

    for stale in ("147.1", "114.5", "1.115", "1.471"):
        if stale in package_text:
            errors.append(f"stale pre-repeat V100 value remains: {stale}")

    for phrase in (
        "datacenter-scale deployment",
        "establishes multi-node scalability",
        "demonstrates multi-node scalability",
        "proposes a new accelerator architecture",
        "bitwise equivalent across precisions",
    ):
        if phrase.lower() in combined.lower():
            errors.append(f"unsupported claim phrase remains: {phrase}")

    for placeholder in ("TODO", "FIXME", "XXX", "[REQUIRED", "[PLACEHOLDER"):
        if placeholder in package_text:
            errors.append(f"placeholder remains: {placeholder}")

    cite_keys: set[str] = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", combined):
        cite_keys.update(key.strip() for key in group.split(","))
    control_keys: set[str] = set()
    for group in re.findall(r"\\bstctlcite\{([^}]+)\}", combined):
        control_keys.update(key.strip() for key in group.split(","))
    used_bib_keys = cite_keys | control_keys
    bib_text = (PAPER / "refs.bib").read_text(encoding="utf-8")
    bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib_text))
    missing_bib = sorted(used_bib_keys - bib_keys)
    if missing_bib:
        errors.append("missing bibliography keys: " + ", ".join(missing_bib))
    unused_bib = sorted(bib_keys - used_bib_keys)
    if unused_bib:
        warnings.append(f"{len(unused_bib)} unused bibliography entries")

    result = {
        "decision": "PASS" if not errors else "FAIL",
        "pages": pages,
        "abstract_words": abstract_words,
        "source_files": len(sources),
        "citation_keys": len(cite_keys),
        "bibliography_control_keys": sorted(control_keys),
        "unused_bib_entries": unused_bib,
        "missing_evidence": missing_evidence,
        "errors": errors,
        "warnings": warnings,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
