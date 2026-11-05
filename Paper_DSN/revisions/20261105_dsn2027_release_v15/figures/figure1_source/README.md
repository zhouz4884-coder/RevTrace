# Fig. 1 editable editorial source

This self-contained matplotlib renderer changes only the Fig. 1 action labels.
The input is byte-identical to the v13 bounded observation file. The two
independent recorded event schedules, ready clocks, stair values, time scale,
D2 line, first deliveries, and 2.175941837-s withdrawal gap are preserved.

The 7.125-in-wide canvas is 3.25 in high. Text is at least 8 pt at that width.
The new upper leader ends at the actual 1.543663284741342-s application
(selected 12 s; visible frontier falls from 14 to 12 s). The lower leader ends
at the actual 3.7943886145949364-s application on its retained 16-s whole view
(selected frontier advances to 14 s). It does not point at the earlier
16-s view arrival at 3.4643774135038257 s.

For an internal experiment launch, freeze this directory as a separate clean Git source, import its full commit
into the root repository, and create a complete source manifest outside this
directory before rendering. Record config and environment hashes, the actual
source commit, a designated 8-TB-disk archive path, and local editorial output,
summary, and gate paths. Run the root no-argument source preflight and an
explicit source+manifest+run-record preflight. Do not relabel the default
experimental source pointer or any previous run.

Internal invocation after the source gate:

```text
python render.py --manifest <complete-source-manifest.json> --out <new-local-output-directory>
```

The renderer checks the complete manifest and a clean source both before and
after export when `--manifest` is supplied. This is the required internal
launch route. The delivery package also supports standalone reproduction
without a private Git database:

```text
python render.py --out <new-output-directory>
```

Dependencies are Python 3.10+, matplotlib, and PyMuPDF (`fitz`). Both modes
verify the immutable input hashes, write PDF/SVG/300-dpi PNG and a gray
preview, verify the exported PDF text is at least 8 pt, and leave visual QA
pending for inspection. Standalone mode records no experimental source
commit and does not imply a new service measurement. Editable label text
and positions are in `config.json`; the complete underlying numeric input
is in `inputs/case.json`. No other paper figure is rendered.
