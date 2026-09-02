"""Build the whitelisted IEEE TC RevTrace submission staging package."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "Paper_TC"
SUBMISSION = PAPER / "submission"
SOURCE_ZIP = SUBMISSION / "RevTrace_TC_source.zip"
PACKAGE_ZIP = SUBMISSION / "TC_RevTrace_STAGING.zip"

SECTIONS = tuple(f"sections/{i:02d}_{name}.tex" for i, name in (
    (1, "introduction"),
    (2, "model"),
    (3, "dgft"),
    (4, "system"),
    (5, "implementation"),
    (6, "evaluation"),
    (7, "discussion"),
    (8, "related"),
    (9, "conclusion"),
))

SOURCE_FILES = (
    "main.tex",
    "refs.bib",
    *SECTIONS,
    "tables/t5_guarantees.tex",
    "tables/t8_normal_slo_adaptations.tex",
    "figures/f1_motivation_senior.jpg",
    "figures/f2_architecture_senior.jpg",
    "figures/f3_certification_senior.jpg",
    "figures/f3_authority_frontier_column.pdf",
    "figures/f4_production.pdf",
    "figures/f5_quality_column.pdf",
    "figures/f7_v100_dual_plane.pdf",
    "supplement/main.tex",
    "supplement/dgft_details.tex",
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def zip_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 3, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def require(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_source() -> None:
    with zipfile.ZipFile(SOURCE_ZIP, "w") as archive:
        for relative in SOURCE_FILES:
            path = require(PAPER / relative)
            zip_member(archive, relative, path.read_bytes())


def main() -> int:
    manuscript = require(PAPER / "main.pdf")
    supplement = require(PAPER / "supplement" / "main.pdf")
    review_artifact = require(SUBMISSION / "RevTrace_TC_review_artifact.zip")
    audit = require(PAPER / "reports" / "tc_submission_audit.json")
    audit_payload = json.loads(audit.read_text(encoding="utf-8"))
    if audit_payload.get("decision") != "PASS":
        raise RuntimeError("TC manuscript audit has not passed")
    if len(PdfReader(manuscript).pages) > 12:
        raise RuntimeError("TC manuscript exceeds 12 pages")

    SUBMISSION.mkdir(parents=True, exist_ok=True)
    build_source()

    files = {
        "01_manuscript/RevTrace_TC_manuscript.pdf": manuscript,
        "02_supplement/RevTrace_TC_supplement.pdf": supplement,
        "03_cover_letter/TC_COVER_LETTER.docx": require(
            SUBMISSION / "TC_COVER_LETTER.docx"
        ),
        "03_cover_letter/TC_COVER_LETTER_source.md": require(
            SUBMISSION / "TC_COVER_LETTER.md"
        ),
        "04_metadata/TC_SUBMISSION_METADATA.md": require(
            SUBMISSION / "TC_SUBMISSION_METADATA.md"
        ),
        "04_metadata/TC_AUTHOR_ACTION_CHECKLIST.md": require(
            SUBMISSION / "TC_AUTHOR_ACTION_CHECKLIST.md"
        ),
        "04_metadata/TC_SUBMISSION_CHECKLIST.md": require(
            SUBMISSION / "TC_SUBMISSION_CHECKLIST.md"
        ),
        "05_source/RevTrace_TC_source.zip": SOURCE_ZIP,
        "06_review_artifact/RevTrace_TC_review_artifact.zip": review_artifact,
        "07_audits/tc_submission_audit.json": audit,
        "07_audits/TRANSACTION_OVERHEAD.md": require(
            PAPER / "reports" / "TRANSACTION_OVERHEAD.md"
        ),
        "07_audits/transaction_overhead_result.json": require(
            ROOT / "results" / "tc_transaction_overhead" / "result.json"
        ),
    }

    records = []
    payloads = []
    for name, path in sorted(files.items()):
        data = path.read_bytes()
        payloads.append((name, data))
        records.append({"path": name, "bytes": len(data), "sha256": digest(data)})

    status = {
        "schema_version": 1,
        "decision": "STAGING_PENDING_AUTHOR_METADATA_AND_APPROVAL",
        "journal": "IEEE Transactions on Computers",
        "manuscript_pages": len(PdfReader(manuscript).pages),
        "supplement_pages": len(PdfReader(supplement).pages),
        "pending": [
            "Verified ORCID for Jiyuan Miao",
            "Verified ORCID for Xi Cao",
            "Current postal addresses in each IEEE Author Portal account",
            "All-author approval of the final manuscript and declarations",
        ],
    }
    readme = """# RevTrace IEEE TC submission staging package

The manuscript is formatted as a 12-page IEEE Transactions regular paper. The
two-page supplement contains detailed safety proofs and the host-side protocol
overhead table. The review artifact is supplied because the public repository
is not anonymously accessible at package-build time.

Upload only the whitelisted files in this archive. Do not upload the dormant
FGCS tables, figures, or historical PDFs from the repository.

Before submission, complete the ORCID/address items listed in STATUS.json and
obtain approval from all authors.
""".encode("utf-8")
    manifest = (json.dumps({"schema_version": 1, "files": records}, indent=2) + "\n").encode("utf-8")
    status_data = (json.dumps(status, indent=2) + "\n").encode("utf-8")

    with zipfile.ZipFile(PACKAGE_ZIP, "w") as archive:
        zip_member(archive, "README.md", readme)
        zip_member(archive, "STATUS.json", status_data)
        zip_member(archive, "MANIFEST.json", manifest)
        for name, data in payloads:
            zip_member(archive, name, data)

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        for record in records:
            if digest(archive.read(record["path"])) != record["sha256"]:
                raise RuntimeError(f"package hash mismatch: {record['path']}")

    print(json.dumps({
        "output": str(PACKAGE_ZIP),
        "bytes": PACKAGE_ZIP.stat().st_size,
        "sha256": digest(PACKAGE_ZIP.read_bytes()),
        "files": len(records),
        "status": status["decision"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
