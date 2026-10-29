#!/usr/bin/env python3
"""Static, fail-closed TeX/BibTeX closure packager; dry run unless --write.

No TeX expansion or bibliography inference. It supports the literal input,
include, includegraphics and citation syntax used by the current core draft.
Only the explicitly supplied latex-paper-en compile.py can compile a package.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class ReleaseError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def without_comments(text: str) -> str:
    """Blank comments without changing character positions; retain escaped %."""
    chars = list(text)
    for m in re.finditer(r"%", text):
        slashes, j = 0, m.start() - 1
        while j >= 0 and text[j] == "\\":
            slashes, j = slashes + 1, j - 1
        if slashes % 2 == 0:
            end = text.find("\n", m.start())
            end = len(text) if end < 0 else end
            chars[m.start():end] = " " * (end - m.start())
    return "".join(chars)


def group(text: str, pos: int, left="{", right="}") -> tuple[str, int]:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != left:
        raise ReleaseError(f"Expected literal {left!r} argument near {text[pos:pos+60]!r}")
    depth, start, pos = 1, pos + 1, pos + 1
    while pos < len(text):
        c = text[pos]
        if c == "\\":
            pos += 2
            continue
        if c == left:
            depth += 1
        elif c == right:
            depth -= 1
            if depth == 0:
                return text[start:pos], pos + 1
        pos += 1
    raise ReleaseError("Unclosed literal argument")


def command_arg(text: str, pos: int) -> str:
    while True:
        while pos < len(text) and (text[pos].isspace() or text[pos] == "*"):
            pos += 1
        if pos < len(text) and text[pos] == "[":
            _, pos = group(text, pos, "[", "]")
        else:
            return group(text, pos)[0].strip()


def literal(value: str) -> str:
    if not value or re.search(r"[\\{}#$~\x00-\x1f]", value):
        raise ReleaseError(f"Dynamic or unsafe literal dependency/key: {value!r}")
    return value


@dataclass
class Entry:
    kind: str
    key: str
    start: int
    end: int
    fields: dict[str, tuple[int, int, str]]


def bib_value_end(text: str, pos: int, end: int) -> int:
    depth, quote = 0, False
    while pos < end:
        c = text[pos]
        if c == "\\":
            pos += 2
            continue
        if c == '"' and depth == 0:
            quote = not quote
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                raise ReleaseError("Unbalanced bibliography value")
        elif c == "," and depth == 0 and not quote:
            return pos
        pos += 1
    if depth or quote:
        raise ReleaseError("Unclosed bibliography field value")
    return pos


def bib_entries(text: str) -> list[Entry]:
    """Keep original entry/field spans; no reserialization of retained fields."""
    result, pos = [], 0
    while True:
        m = re.search(r"@([A-Za-z]+)\s*([({])", text[pos:])
        if not m:
            break
        start = pos + m.start()
        kind = m.group(1).lower()
        opening = pos + m.end() - 1
        left = text[opening]
        right = "}" if left == "{" else ")"
        if left == "{":
            inner, entry_end = group(text, opening)
        else:
            # Parenthesis entries may contain arbitrary balanced brace values.
            cur, braces, quote = opening + 1, 0, False
            while cur < len(text):
                c = text[cur]
                if c == "\\":
                    cur += 2
                    continue
                if c == '"' and braces == 0:
                    quote = not quote
                elif c == "{":
                    braces += 1
                elif c == "}":
                    braces -= 1
                elif c == right and braces == 0 and not quote:
                    break
                cur += 1
            if cur >= len(text) or braces < 0:
                raise ReleaseError("Unclosed parenthesis bibliography entry")
            inner, entry_end = text[opening+1:cur], cur + 1
        pos = entry_end
        if kind == "comment":
            continue
        if kind == "preamble":
            raise ReleaseError("@preamble is active bibliography code: manual resolution required")
        inner_start, inner_end = opening + 1, entry_end - 1
        if kind == "string":
            key, fields_pos = "", inner_start
        else:
            comma = inner.find(",")
            if comma < 0:
                raise ReleaseError(f"No key separator in bibliography entry at {start}")
            key = literal(inner[:comma].strip())
            fields_pos = inner_start + comma + 1
        fields = {}
        while fields_pos < inner_end:
            while fields_pos < inner_end and (text[fields_pos].isspace() or text[fields_pos] == ","):
                fields_pos += 1
            if fields_pos >= inner_end:
                break
            if text[fields_pos] == "%":
                newline = text.find("\n", fields_pos)
                fields_pos = inner_end if newline < 0 else newline + 1
                continue
            fm = re.match(r"([A-Za-z][\w:-]*)\s*=\s*", text[fields_pos:inner_end])
            if not fm:
                raise ReleaseError(f"Unparsed BibTeX field near {text[fields_pos:fields_pos+65]!r}")
            name, field_start = fm.group(1).lower(), fields_pos
            value_start = fields_pos + fm.end()
            value_end = bib_value_end(text, value_start, inner_end)
            field_end = value_end + (value_end < inner_end and text[value_end] == ",")
            if name in fields:
                raise ReleaseError(f"Duplicate bibliography field {name!r} in {key!r}")
            fields[name] = (field_start, int(field_end), text[value_start:value_end].strip())
            fields_pos = int(field_end)
        if kind == "string":
            if len(fields) != 1:
                raise ReleaseError("@string must contain exactly one assignment")
            key = next(iter(fields))
        result.append(Entry(kind, key, start, entry_end, fields))
    return result


MONTHS = set("jan feb mar apr may jun jul aug sep oct nov dec".split())


def bare_macros(expr: str) -> set[str]:
    """Inspect only bare terms of a BibTeX # expression, not words in values."""
    macros, pos = set(), 0
    while pos < len(expr):
        if expr[pos].isspace() or expr[pos] == "#":
            pos += 1
        elif expr[pos] == "{":
            _, pos = group(expr, pos)
        elif expr[pos] == '"':
            pos += 1
            depth = 0
            while pos < len(expr):
                c = expr[pos]
                if c == "\\":
                    pos += 2
                    continue
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif c == '"' and depth == 0:
                    pos += 1
                    break
                pos += 1
            else:
                raise ReleaseError("Unclosed quoted BibTeX expression")
        else:
            m = re.match(r"[A-Za-z][\w:-]*|\d+", expr[pos:])
            if not m:
                raise ReleaseError(f"Unsupported BibTeX expression: {expr!r}")
            if not m.group().isdigit():
                macros.add(m.group().lower())
            pos += len(m.group())
    return macros - MONTHS


def simple_bib_literal(expr: str) -> str:
    if expr.startswith("{"):
        value, end = group(expr, 0)
        if expr[end:].strip():
            raise ReleaseError(f"Nonliteral crossref: {expr!r}")
        return literal(value.strip())
    if expr.startswith('"') and expr.endswith('"') and '"' not in expr[1:-1]:
        return literal(expr[1:-1].strip())
    raise ReleaseError(f"Unresolved/nonliteral crossref {expr!r}; no parent inferred")


class Closure:
    CITES = set("cite Cite citep Cited Citet Citetal citet citealp citealt citeauthor citeyear citeyearpar nocite bstctlcite textcite Textcite autocite parencite footcite smartcite supercite".split())
    UNSUPPORTED = set("import subimport subinputfrom inputfrom includeonly graphicspath DeclareGraphicsExtensions addbibresource includepdf lstinputlisting verbatiminput externaldocument IfFileExists InputIfFileExists write18 newcommand renewcommand providecommand newenvironment renewenvironment def edef gdef xdef let csname catcode verb".split())

    def __init__(self, source: Path, entry: str, strip_metadata: bool = False):
        self.root = source.resolve()
        self.entry = self.inside(entry)
        self.strip_metadata = strip_metadata
        self.outputs: dict[str, bytes] = {}
        self.inputs: dict[Path, bytes] = {}
        self.seen, self.active = set(), set()
        self.citations, self.bibs, self.system = set(), [], set()
        self.provenance = []
        self.bib_provenance = []

    def inside(self, name: str) -> Path:
        path = (self.root / literal(name)).resolve()
        if not path.is_relative_to(self.root):
            raise ReleaseError(f"Dependency escapes source root: {name!r}")
        return path

    def read(self, path: Path) -> bytes:
        if not path.is_file():
            raise ReleaseError(f"Missing source dependency: {path.relative_to(self.root)}")
        data = path.read_bytes()
        if path in self.inputs and self.inputs[path] != data:
            raise ReleaseError(f"Source changed while reading: {path.relative_to(self.root)}")
        self.inputs[path] = data
        return data

    def add(self, path: Path, data: bytes | None = None, transform="byte-identical"):
        raw = self.read(path)
        output = data if data is not None else raw
        rel = "main.tex" if path == self.entry else path.relative_to(self.root).as_posix()
        if rel in self.outputs:
            if self.outputs[rel] != output:
                raise ReleaseError(f"Release output collision: {rel}")
            return
        self.outputs[rel] = output
        self.provenance.append({"source": path.relative_to(self.root).as_posix(),
                                "target": rel, "source_sha256": sha(raw),
                                "target_sha256": sha(output), "bytes": len(output),
                                "transformation": transform})

    def resolve(self, name: str, suffix: str) -> Path:
        p = self.inside(name)
        return p if p.suffix else self.inside(name + suffix)

    def tex(self, path: Path):
        if path in self.active:
            raise ReleaseError(f"Cyclic TeX input: {path.relative_to(self.root)}")
        if path in self.seen:
            return
        self.active.add(path)
        self.add(path)
        text = without_comments(self.inputs[path].decode("utf-8-sig"))
        if re.search(r"\\begin\s*\{(?:verbatim|Verbatim|lstlisting|minted)\}", text):
            raise ReleaseError(f"Verbatim/code environment in {path.name}: explicit parsing support required")
        for m in re.finditer(r"\\([A-Za-z@]+)(?:\*)?", text):
            name = m.group(1)
            if name in self.UNSUPPORTED or name.startswith("if"):
                raise ReleaseError(f"Unsupported dependency/conditional command \\{name} in {path.name}")
            if name in {"input", "include"}:
                self.tex(self.resolve(command_arg(text, m.end()), ".tex"))
            elif name == "includegraphics":
                graphics = self.inside(command_arg(text, m.end()))
                if not graphics.suffix:
                    matches = [graphics.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".mps", ".jpeg") if graphics.with_suffix(ext).is_file()]
                    if not matches:
                        raise ReleaseError(f"Missing literal graphic: {graphics.name}")
                    graphics = matches[0]
                self.add(graphics)
            elif name == "bibliography":
                for db in command_arg(text, m.end()).split(","):
                    bp = self.resolve(db.strip(), ".bib")
                    if bp not in self.bibs:
                        self.bibs.append(bp)
            elif name in self.CITES:
                for key in command_arg(text, m.end()).split(","):
                    if key.strip() == "*":
                        raise ReleaseError("\\nocite{*} would include uncited entries; manual decision required")
                    self.citations.add(literal(key.strip()))
            elif "cite" in name.lower():
                raise ReleaseError(f"Unsupported citation command \\{name}; do not silently omit keys")
            elif name in {"documentclass", "usepackage", "bibliographystyle"}:
                suffix = {"documentclass": ".cls", "usepackage": ".sty", "bibliographystyle": ".bst"}[name]
                for dep in command_arg(text, m.end()).split(","):
                    dep = literal(dep.strip())
                    if self.resolve(dep, suffix).is_file():
                        raise ReleaseError(f"Local style {dep+suffix}: explicit support required before packaging")
                    self.system.add(dep + suffix)
        self.active.remove(path)
        self.seen.add(path)

    def bibliography(self):
        records, entries, macros = [], {}, {}
        for path in self.bibs:
            text = self.read(path).decode("utf-8-sig")
            # UTF-8 BOM is excluded from spans, then accounted for in byte offsets.
            for entry in bib_entries(text):
                item = (path, text, entry)
                table = macros if entry.kind == "string" else entries
                if entry.key in table:
                    raise ReleaseError(f"Duplicate bibliography key/string: {entry.key}")
                table[entry.key] = item
                records.append(item)
        missing = sorted(self.citations - entries.keys())
        if missing:
            raise ReleaseError(f"Unresolved cited BibTeX keys: {missing}")
        selected, reasons, pending = set(self.citations), {k: "cited" for k in self.citations}, list(self.citations)
        parents = {}
        while pending:
            key = pending.pop()
            entry = entries[key][2]
            if "xdata" in entry.fields:
                raise ReleaseError(f"BibLaTeX xdata on {key}: explicit resolution required")
            if "crossref" in entry.fields:
                parent = simple_bib_literal(entry.fields["crossref"][2])
                if parent not in entries:
                    raise ReleaseError(f"Unresolved BibTeX crossref {key} -> {parent}; no parent guessed")
                parents[key] = parent
                if parent not in selected:
                    selected.add(parent)
                    reasons[parent] = "crossref_dependency"
                    pending.append(parent)
        for key in selected:
            trail, node = set(), key
            while node in parents:
                if node in trail:
                    raise ReleaseError(f"Cyclic BibTeX crossref involving {node}")
                trail.add(node)
                node = parents[node]
        needed_macros, queue = set(), []
        for key in selected:
            for _, _, expr in entries[key][2].fields.values():
                queue.extend(bare_macros(expr))
        while queue:
            key = queue.pop()
            if key in needed_macros:
                continue
            if key not in macros:
                raise ReleaseError(f"Unresolved bibliography string {key!r}")
            needed_macros.add(key)
            for _, _, expr in macros[key][2].fields.values():
                queue.extend(bare_macros(expr))
        def visit_macro(key, active, visited):
            if key in active:
                raise ReleaseError(f"Cyclic bibliography string {key!r}")
            if key in visited:
                return
            active.add(key)
            for _, _, expr in macros[key][2].fields.values():
                for child in bare_macros(expr):
                    visit_macro(child, active, visited)
            active.remove(key)
            visited.add(key)
        visited_macros = set()
        for key in needed_macros:
            visit_macro(key, set(), visited_macros)
        for path in self.bibs:
            output = []
            for bp, text, entry in records:
                if bp != path or (entry.kind == "string" and entry.key not in needed_macros) or (entry.kind != "string" and entry.key not in selected):
                    continue
                original = text[entry.start:entry.end].encode("utf-8")
                rendered = text[entry.start:entry.end]
                remove = {k: span for k, span in entry.fields.items() if self.strip_metadata and k in {"abstract", "keywords"} and entry.kind != "string"}
                for _, (start, end, _) in sorted(remove.items(), key=lambda x: x[1][0], reverse=True):
                    rendered = rendered[:start-entry.start] + rendered[end-entry.start:]
                rendered_bytes = rendered.encode("utf-8")
                output.append(rendered_bytes)
                bom = 3 if self.inputs[path].startswith(b"\xef\xbb\xbf") else 0
                byte_start = bom + len(text[:entry.start].encode("utf-8"))
                self.bib_provenance.append({
                    "key": entry.key, "type": entry.kind, "source": path.relative_to(self.root).as_posix(),
                    "reason": "string_dependency" if entry.kind == "string" else reasons[entry.key],
                    "source_byte_start": byte_start, "source_byte_end": byte_start + len(original),
                    "source_entry_sha256": sha(original), "target_entry_sha256": sha(rendered_bytes),
                    "removed_fields": sorted(remove),
                    "original_entry_bytes_base64": base64.b64encode(original).decode("ascii"),
                })
            # Keep each selected entry byte-for-byte apart from explicitly removed fields.
            self.add(path, b"\n\n".join(output) + b"\n", "reachable-BibTeX-closure" + ("; strip-abstract-keywords" if self.strip_metadata else ""))

    def plan(self) -> dict:
        self.tex(self.entry)
        self.bibliography()
        # Close the read snapshot before a destination can be created.
        for path, data in self.inputs.items():
            if path.read_bytes() != data:
                raise ReleaseError(f"Source changed during planning: {path.relative_to(self.root)}")
        source_label = self.root.name
        for ancestor in self.root.parents:
            if (ancestor / ".git").exists():
                source_label = self.root.relative_to(ancestor).as_posix()
                break
        return {"schema": "revtrace-dsn-release-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
                "source_directory": source_label,
                "entry_source": self.entry.relative_to(self.root).as_posix(), "entry_target": "main.tex",
                "source_identity": "exact input bytes; legacy checkout HEAD is not execution provenance",
                "strip_bib_metadata": self.strip_metadata, "cited_keys": sorted(self.citations),
                "external_tex_dependencies": sorted(self.system), "files": self.provenance,
                "bibliography_entries": self.bib_provenance,
                "parser_scope": "literal static TeX; no macro expansion, conditionals, local styles or BibLaTeX inference",
                "gate": "READY_TO_PACKAGE_NOT_COMPILED_NOT_VISUALLY_REVIEWED"}


def write_release(closure: Closure, manifest: dict, destination: Path):
    dest = destination.resolve()
    if dest == closure.root or dest.is_relative_to(closure.root) or closure.root.is_relative_to(dest):
        raise ReleaseError("Release destination must be a separate, new directory, not a source ancestor/descendant")
    if dest.exists():
        raise ReleaseError(f"Refusing to overwrite existing destination: {dest}")
    if not dest.parent.is_dir():
        raise ReleaseError("Destination parent must already exist; no implicit hierarchy creation")
    # Exclusive creation is intentional: errors retain an inspectable partial pack, never overwrite.
    dest.mkdir()
    try:
        for rel, data in closure.outputs.items():
            path = dest / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest["packager_sha256"] = sha(Path(__file__).read_bytes())
        (dest / "PACKAGING_PROVENANCE.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for row in manifest["files"]:
            if sha((dest / row["target"]).read_bytes()) != row["target_sha256"]:
                raise ReleaseError(f"Post-copy mismatch: {row['target']}")
        # A source can change during copying; never silently publish an inconsistent snapshot.
        for path, data in closure.inputs.items():
            if path.read_bytes() != data:
                raise ReleaseError(f"Source changed during copy: {path.relative_to(closure.root)}")
    except Exception as exc:
        (dest / "PACKAGING_FAILED.txt").write_text(str(exc) + "\n", encoding="utf-8")
        raise


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--entry", default="core_draft.tex")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--strip-bib-metadata", action="store_true", help="Remove parsed abstract/keywords fields; retain original selected entry bytes in provenance")
    parser.add_argument("--write", action="store_true", help="Without this flag only print the bounded closure plan")
    parser.add_argument("--compile", action="store_true", help="After --write, invoke only the explicitly supplied skill compile.py")
    parser.add_argument("--skill-compile", type=Path, help="Absolute path to latex-paper-en/scripts/compile.py")
    args = parser.parse_args()
    try:
        closure = Closure(args.source, args.entry, args.strip_bib_metadata)
        manifest = closure.plan()
        print(json.dumps({"gate": manifest["gate"], "write_requested": args.write,
                          "files": [{k: v for k, v in r.items() if k != "source_sha256"} for r in manifest["files"]],
                          "cited_keys": manifest["cited_keys"],
                          "bibliography_dependencies": [e["key"] for e in manifest["bibliography_entries"] if e["reason"] != "cited"],
                          "external_tex_dependencies": manifest["external_tex_dependencies"]}, ensure_ascii=False, indent=2))
        if args.compile and (not args.write or not args.skill_compile):
            raise ReleaseError("--compile requires --write and explicit --skill-compile")
        if args.write:
            if not args.destination:
                raise ReleaseError("--write requires --destination")
            if args.compile:
                skill = args.skill_compile.resolve()
                if skill.name != "compile.py" or skill.parent.name != "scripts" or skill.parent.parent.name != "latex-paper-en" or not skill.is_file():
                    raise ReleaseError("Only latex-paper-en/scripts/compile.py is allowed for compilation")
            write_release(closure, manifest, args.destination)
            if args.compile:
                # The explicit recipe emits aux/PDF alongside main.tex; do not assume --outdir is honored.
                cmd = [sys.executable, "-B", str(skill), "main.tex", "--recipe", "pdflatex-bibtex"]
                result = subprocess.run(cmd, cwd=args.destination.resolve(), capture_output=True, timeout=600)
                record = {"skill_sha256": sha(skill.read_bytes()), "recipe": "pdflatex-bibtex", "shell_escape": False,
                          "returncode": result.returncode, "compiler_identity": "latex-paper-en skill; no direct TeX invocation"}
                (args.destination / "COMPILE_RECORD.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
                (args.destination / "COMPILE_STDOUT.txt").write_bytes(result.stdout + b"\n" + result.stderr)
                return result.returncode
        return 0
    except (ReleaseError, UnicodeError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"gate": "BLOCKED_NOT_A_RELEASE", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
