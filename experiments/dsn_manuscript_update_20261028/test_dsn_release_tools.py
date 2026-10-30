#!/usr/bin/env python3
"""Meaningful parser/guard controls; temporary fixtures, never a real release."""
from __future__ import annotations

import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path

from prepare_dsn_release import Closure, ReleaseError, bib_entries, without_comments, write_release
from qa_dsn_release import font_check, logs_check, manifest_check, metadata_check, reference_pages
from release_delivery_checks import new_output_path, sha, validate_final_record
from record_final_visual_review import build_record


class PackagingControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="revtrace-release-controls-")
        self.parent = Path(self.temp.name)
        self.source = self.parent / "fixture_source"
        self.source.mkdir()
        (self.source / "sections").mkdir()
        (self.source / "figures").mkdir()
        (self.source / "core_draft.tex").write_bytes(b"\\documentclass{IEEEtran}\r\n% \\input{missing}\r\n\\input{sections/live}\r\n\\bibliography{refs}\r\n")
        (self.source / "sections/live.tex").write_text(r"\cite[see][p.~3]{a,child}\includegraphics{figures/live.pdf}\includegraphics{figures/live.pdf}", encoding="utf-8")
        (self.source / "sections/unused.tex").write_text(r"\input{missing}\cite{missing}", encoding="utf-8")
        (self.source / "figures/live.pdf").write_bytes(b"fixture-binary-not-a-real-pdf\x00\xff")
        (self.source / "refs.bib").write_bytes((
            '@string{journal = "Journ" # {al}}\r\n'
            '@article{a, title={A {nested} títle}, journal=journal, year=2026,\r\n'
            ' abstract={Metadata with {nested braces} and, comma}, keywords="one, two",}\r\n'
            '@inproceedings{child, title={Child}, crossref={parent}}\r\n'
            '@proceedings{parent, title={Required parent}, year={2026}}\r\n'
            '@misc{unused, title={Not reachable}}\r\n').encode("utf-8"))

    def tearDown(self):
        self.temp.cleanup()

    def closure(self, strip=False):
        closure = Closure(self.source, "core_draft.tex", strip)
        return closure, closure.plan()

    def test_only_reachable_and_binary_bytes_unchanged(self):
        closure, plan = self.closure()
        self.assertEqual(set(closure.outputs), {"main.tex", "sections/live.tex", "figures/live.pdf", "refs.bib"})
        self.assertEqual(closure.outputs["main.tex"], (self.source / "core_draft.tex").read_bytes())
        self.assertEqual(closure.outputs["figures/live.pdf"], (self.source / "figures/live.pdf").read_bytes())
        self.assertEqual(len(plan["files"]), 4)  # duplicate graphic use is one file
        self.assertEqual(plan["cited_keys"], ["a", "child"])

    def test_bib_closure_preserves_entry_bytes_and_parent_macro(self):
        closure, plan = self.closure()
        keys = {entry.key for entry in bib_entries(closure.outputs["refs.bib"].decode("utf-8"))}
        self.assertEqual(keys, {"journal", "a", "child", "parent"})
        for row in plan["bibliography_entries"]:
            original = base64.b64decode(row["original_entry_bytes_base64"])
            self.assertIn(original, closure.outputs["refs.bib"])
            self.assertEqual(original, (self.source / "refs.bib").read_bytes()[row["source_byte_start"]:row["source_byte_end"]])

    def test_metadata_removal_safe_and_original_recoverable(self):
        closure, plan = self.closure(True)
        entries = {e.key: e for e in bib_entries(closure.outputs["refs.bib"].decode("utf-8"))}
        self.assertNotIn("abstract", entries["a"].fields)
        self.assertNotIn("keywords", entries["a"].fields)
        row = next(r for r in plan["bibliography_entries"] if r["key"] == "a")
        original = base64.b64decode(row["original_entry_bytes_base64"])
        self.assertIn(b"abstract=", original)
        self.assertEqual(row["removed_fields"], ["abstract", "keywords"])

    def test_missing_cited_key_blocks(self):
        (self.source / "sections/live.tex").write_text(r"\cite{unknown}", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "Unresolved cited"):
            self.closure()

    def test_unresolved_crossref_blocks_instead_of_guess(self):
        (self.source / "refs.bib").write_text('@article{a,title={A}}\n@inproceedings{child,crossref={missing}}', encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "Unresolved BibTeX crossref"):
            self.closure()

    def test_crossref_cycle_blocks(self):
        (self.source / "refs.bib").write_text('@article{a,crossref={child}}\n@inproceedings{child,crossref={a}}', encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "Cyclic BibTeX crossref"):
            self.closure()

    def test_macro_cycle_blocks(self):
        (self.source / "refs.bib").write_text('@string{x=y}\n@string{y=x}\n@article{a,journal=x}\n@misc{child,title={C}}', encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "Cyclic bibliography string"):
            self.closure()

    def test_dynamic_path_escaping_root_and_hidden_macros_block(self):
        for dependency in (r"\input{\chosen}", r"\input{../outside}", r"\newcommand{\hidden}{\input{unused}}"):
            (self.source / "sections/live.tex").write_text(dependency, encoding="utf-8")
            with self.assertRaises(ReleaseError):
                self.closure()

    def test_unknown_citation_and_nocite_star_block(self):
        for citation in (r"\mycite{a}", r"\nocite{*}"):
            (self.source / "sections/live.tex").write_text(citation, encoding="utf-8")
            with self.assertRaises(ReleaseError):
                self.closure()

    def test_write_only_new_separate_destination_and_verify_manifest(self):
        closure, plan = self.closure(True)
        original = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        for path in (self.source, self.source / "release", self.parent):
            with self.assertRaises(ReleaseError):
                write_release(closure, plan, path)
        destination = self.parent / "fixture_release"
        write_release(closure, plan, destination)
        self.assertEqual(manifest_check(destination)["status"], "PASS")
        for path, data in original.items():
            self.assertEqual(path.read_bytes(), data)
        with self.assertRaisesRegex(ReleaseError, "overwrite"):
            write_release(closure, plan, destination)
        (destination / "main.tex").write_text("changed", encoding="utf-8")
        self.assertEqual(manifest_check(destination)["status"], "FAIL")

    def test_source_change_after_plan_is_detected(self):
        closure, plan = self.closure()
        (self.source / "sections/live.tex").write_text("changed during copying", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "Source changed during copy"):
            write_release(closure, plan, self.parent / "changed_fixture_release")
        self.assertTrue((self.parent / "changed_fixture_release/PACKAGING_FAILED.txt").is_file())

    def test_percent_escapes(self):
        text = "visible \\% retained % \\cite{hidden}\n"
        cleaned = without_comments(text)
        self.assertIn(r"\% retained", cleaned)
        self.assertNotIn("hidden", cleaned)


class QAControls(unittest.TestCase):
    def test_font_embedding_and_type3(self):
        header = "name type encoding emb sub uni object ID\n---------------------------------------\n"
        good = header + "ABC+Times  Type 1  WinAnsi  yes yes yes 4 0\n"
        self.assertEqual(font_check(good)["status"], "PASS")
        self.assertEqual(font_check(good.replace("Type 1", "Type 3"))["status"], "FAIL")
        self.assertEqual(font_check(good.replace("yes yes yes", "no yes yes"))["status"], "FAIL")

    def test_pages_clean_refs_and_limit(self):
        pdftext = "Main text\fConclusion\fREFERENCES\n[1] A paper.\f[2] Another paper.\f"
        result = reference_pages(pdftext, 4, 11)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["technical_pages"], 2)
        self.assertEqual(reference_pages(pdftext.replace("REFERENCES", "R EFERENCES"), 4, 11)["status"], "PASS")
        self.assertEqual(reference_pages(pdftext.replace("REFERENCES", "R EFERENCES").replace("\n", "\r\n"), 4, 11)["status"], "PASS")
        self.assertEqual(reference_pages(pdftext, 4, 1)["status"], "FAIL")
        mixed = pdftext.replace("REFERENCES", "Conclusion continues\nREFERENCES")
        self.assertEqual(reference_pages(mixed, 4, 11)["status"], "FAIL")
        appendix = pdftext.replace("[2] Another paper.", "[2] Another paper.\nAPPENDIX")
        self.assertEqual(reference_pages(appendix, 4, 11)["status"], "FAIL")

    def test_undefined_refs_and_failed_build(self):
        bbl = r"\begin{thebibliography}{1}\bibitem{a}A\end{thebibliography}"
        self.assertEqual(logs_check("Output written on main.pdf", "", bbl)["status"], "PASS")
        self.assertEqual(logs_check("Output written on main.pdf\nLaTeX Warning: Citation `a' undefined", "", bbl)["status"], "FAIL")
        self.assertEqual(logs_check("Compilation interrupted", "", bbl)["status"], "FAIL")

    def test_author_metadata_and_xmp_identity(self):
        self.assertEqual(metadata_check("Author: Anonymous submission\nPages: 10", "", ["PersonalName"])["status"], "PASS")
        self.assertEqual(metadata_check("Author: PersonalName", "", [])["status"], "FAIL")
        xmp = "<dc:creator><rdf:Seq><rdf:li>PersonalName</rdf:li></rdf:Seq></dc:creator>"
        self.assertEqual(metadata_check("Author:", xmp, [])["status"], "FAIL")
        alias = '<x:creator xmlns:x="http://purl.org/dc/elements/1.1/">PersonalName</x:creator>'
        self.assertEqual(metadata_check("Author:", alias, [])["status"], "FAIL")
        self.assertEqual(metadata_check("Title: Work\nSubject: hidden account", "", ["account"])["status"], "FAIL")


class VersionedDeliveryControls(unittest.TestCase):
    """Synthetic records and PNG headers only; never approve an actual PDF."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="revtrace-versioned-delivery-controls-")
        self.root = Path(self.temp.name)
        self.release = self.root / "Paper_DSN/revisions/fixture_new"
        self.release.mkdir(parents=True)
        self.archive = self.root / "Paper_DSN/fixture.zip"
        self.archive.write_bytes(b"synthetic archive bytes; not a real package")
        (self.release / "main.pdf").write_bytes(b"synthetic pdf identity; not a real paper")
        self.record_path = self.root / "fixture_record.json"
        self.record = {
            "gate": "PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA",
            "release": self.release.relative_to(self.root).as_posix(),
            "archive": self.archive.relative_to(self.root).as_posix(),
            "pdf_sha256": sha((self.release / "main.pdf").read_bytes()),
            "archive_sha256": sha(self.archive.read_bytes()), "archive_bytes": self.archive.stat().st_size,
        }
        self.record_path.write_text(json.dumps(self.record), encoding="utf-8")
        self.qa = self.release / "QA.json"
        self.qa.write_text(json.dumps({"gate": "PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA",
                                      "pdf_sha256": self.record["pdf_sha256"], "total_pages": 2,
                                      "checks": {"pagination": {"technical_pages": 1, "references_start_page": 2}}}), encoding="utf-8")
        self.rendered = self.release / "rendered"
        self.rendered.mkdir()
        # Parser fixture only: complete PNG decoding is not claimed by the tool.
        header = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 1391, 1800) + b"\x08\x02\0\0\0" + b"\0" * 4
        for page in (1, 2):
            (self.rendered / f"page-{page:02d}.png").write_bytes(header)

    def tearDown(self):
        self.temp.cleanup()

    def review(self, pages=None, attestation=True):
        return build_record(self.release, self.qa, self.rendered, [1, 2] if pages is None else pages,
                            attestation, "Synthetic fixture only", self.root)

    def test_new_record_refuses_old_version_and_escape_before_outputs(self):
        before = self.record_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            new_output_path(self.record_path, self.root, ".json")
        self.assertEqual(self.record_path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "inside"):
            new_output_path(self.root.parent / "escaped-record.json", self.root, ".json")
        self.assertEqual(new_output_path(self.root / "next.json", self.root, ".json"), self.root / "next.json")

    def test_matching_final_record_is_accepted(self):
        self.assertEqual(validate_final_record(self.record_path, self.release, self.archive, self.root), self.record)

    def test_stale_record_cannot_authorize_other_release_even_same_pdf(self):
        other = self.root / "Paper_DSN/revisions/other"
        other.mkdir()
        (other / "main.pdf").write_bytes((self.release / "main.pdf").read_bytes())
        with self.assertRaisesRegex(ValueError, "release"):
            validate_final_record(self.record_path, other, self.archive, self.root)

    def test_changed_or_renamed_archive_is_rejected(self):
        alternate = self.archive.with_name("other.zip")
        alternate.write_bytes(self.archive.read_bytes())
        with self.assertRaisesRegex(ValueError, "archive"):
            validate_final_record(self.record_path, self.release, alternate, self.root)
        self.archive.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "archive_sha256"):
            validate_final_record(self.record_path, self.release, self.archive, self.root)

    def test_changed_pdf_is_rejected_by_both_records(self):
        (self.release / "main.pdf").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "pdf_sha256"):
            validate_final_record(self.record_path, self.release, self.archive, self.root)
        with self.assertRaisesRegex(ValueError, "changed after"):
            self.review()

    def test_actual_attestation_and_explicit_complete_page_list_required(self):
        with self.assertRaisesRegex(ValueError, "attestation"):
            self.review(attestation=False)
        for pages in ([1], [1, 1], [2, 1], [1, 2, 3]):
            with self.assertRaisesRegex(ValueError, "every final page"):
                self.review(pages=pages)

    def test_review_binds_all_pngs_and_automatic_record(self):
        record = self.review()
        self.assertEqual(record["reviewed_pages"], [1, 2])
        self.assertEqual(record["automated_QA_sha256"], sha(self.qa.read_bytes()))
        self.assertEqual(record["rendered_max_side_pixels"], 1800)
        self.assertEqual(record["rendered_pages"][0]["sha256"], sha((self.rendered / "page-01.png").read_bytes()))

    def test_missing_duplicate_or_malformed_png_rejected(self):
        second = self.rendered / "page-02.png"
        original = second.read_bytes()
        second.unlink()
        with self.assertRaisesRegex(ValueError, "exactly match"):
            self.review()
        second.write_bytes(original)
        duplicate = self.rendered / "page-2.png"
        duplicate.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.review()
        duplicate.unlink()
        second.write_bytes(b"not a PNG")
        with self.assertRaisesRegex(ValueError, "not a PNG"):
            self.review()

    def test_new_pagination_allows_eleven_technical_and_reference_page(self):
        text = "\f".join([f"Technical content {i}" for i in range(1, 12)] + ["REFERENCES\n[1] A paper."]) + "\f"
        result = reference_pages(text, 12, 11)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["technical_pages"], 11)


if __name__ == "__main__":
    unittest.main()
