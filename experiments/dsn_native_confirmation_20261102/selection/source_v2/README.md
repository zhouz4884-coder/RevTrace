# Strict AISHELL history census and metadata-first confirmation selection

No models, transcripts-as-selection-features, inference, performance mining or
new audio are read by these programs. Source preparation has not executed the
16 semantic controls or a formal census. Root freezes this full independent
source, manifest/bundle, actual environment and root no-argument preflight
before any formal CPU run.

`metadata_census.py` reads identity/path/hash fields from historical JSON/CSV
metadata. It distinguishes case configs, frozen plans, acquired/selected
receipts and artifact metadata. It conservatively excludes every implicated
speaker while preserving the evidence tier; it does not count every entry as
an independent neural execution. Global ZIP catalog previews, eligible pools,
technical fallback lists and the full `reference.json` corpus are not usage.
Reference corpora are not opened/hashed before selection.

Renamed/concatenated Chinese inputs inherit all recorded component speakers;
exact path/hash/qualified-ID links resolve transitive aliases. Generic source0
aliases are file-scoped. WAV/PCM hash keys and origin remain distinct in the
full observation ledger; an exact hash match is useful, but hash nonmatch alone
does not prove speaker separation or compatible encodings. Unresolved Chinese
lineage remains explicit and blocks a final unused-speaker claim.

The complete historical input metadata content hashes and file set are checked
again at the end. Read-only input roots are in external `CENSUS_CONFIG.json`.
The current experiment subtree is excluded so selection cannot contaminate its
own history. Large nonidentity neural payloads are not metadata and are listed
in `SKIPPED_NONMETADATA.json`; original configs/source manifests and lineages
remain the authoritative identity evidence. Compressed-only model results are
not interpreted as new evidence; local archive mirrors and original 8 TB case
metadata provide the source identities.

Formal controls (stdlib only; 16 named controls):

```
python -B -m unittest -v test_selection_controls
```

Formal census, local checkout phase and authoritative 8 TB phase, each with its
own prelaunch/run record and previously nonexistent result directory:

```
python -B metadata_census.py --manifest COMPLETE_SOURCE.json \
  --config CENSUS_CONFIG.json --phase local_history --stream-bundle \
  --out /media/user/DESIGNATED_8TB/results/NEW_LOCAL_CENSUS
python -B metadata_census.py --manifest COMPLETE_SOURCE.json \
  --config CENSUS_CONFIG.json --phase remote_history --out NEW_8TB_CENSUS
```

The configuration intentionally contains both Windows and Linux roots; only
the selected phase is traversed. Root controls transport of bounded census
ledgers. Keep full observations/input inventories on the designated experiment
disk and publish bounded audited exclusions. If roots or metadata are missing,
do not silently label the phase complete. Cross-phase exact lineage joins may
resolve an alias; metadata errors cannot be waived by the selector.

`--stream-bundle` is only for `local_history`: the actual Windows process reads
the original Windows metadata and records the true Windows/Python environment.
Every output is held in a Path-like RAM sink labelled with the predeclared
POSIX8TB `--out`; no local output/raw/temp file is created. Binary ZIP is the
only stdout payload, including preserved partial failure files on error.
Root captures stdout in RAM and uses the approved SFTP route for FIRST
persistence at that8TB destination, verifies/unpacks it there, and mirrors
only bounded summary/exclusion later. Do not use shell redirection to a
Windows file. Stderr contains technical failure diagnostics only. Normal
`remote_history` uses real original-disk Paths unchanged. The two additional
controls check exact file/hash bytes and POSIX labelling/no local filesystem
writes; they are not corpus scans.

Final frozen selection (only after both phases' immutable ledgers exist):

```
python -B freeze_candidates.py --manifest COMPLETE_SOURCE.json \
  --rule SELECTION_RULE.json --catalog ARCHIVE_ENTRIES_0.json \
  --census LOCAL_CENSUS_COPY AUTHORITATIVE_CENSUS --out NEW_METADATA_SELECTION
```

The split is the original provided `StreamCorrect/aishell1_testset` at its
fixed public revision. Use 8–9 s complete original utterances, one per unused
speaker. 12 is a maximum budget, not a success gate: take all strict eligible
speakers when fewer than12 exist; do not silently widen duration or borrow
train/dev/new clips from used speakers. Speaker and utterance sampling is fixed
PRNG metadata-only selection. Freeze every same-speaker technical-header
fallback before reading new audio/transcripts. Network/CRC failures retry the
same member or stop. Only CRC-valid but technically invalid audio/header or
out-of-band true duration permits the next frozen same-speaker candidate.
If all that speaker's frozen candidates are invalid, STOP; any smallerN must
be separately frozen by Root before models, never silently shrunk.

`METADATA_SELECTION.json` is deliberately PENDING_AUDIO, with WAV/PCM hashes
and actual frames unset. It must never be accepted by the service/reference
drivers as a data-ready receipt. A separately frozen acquisition gate must:

1. acquire precisely the fixed ZIP member/CRC, with no response-based reselection;
2. verify original PCM16 mono16kHz complete WAV and true duration8≤frames/16000≤9;
3. preserve no trim, concatenation, padding, resampling or inserted silence;
4. compute WAV and PCM hashes; reject an exact historical audio/hash collision;
5. read matching original reference text only after metadata selection is locked;
6. emit the agreed `DATA_RECEIPT_CONTRACT.json` fields and raw SHA gate before
   reference inference, model calls or service execution.

The old four-speaker acquisition script cannot be used unchanged: its actual
header guard allowed8–15s and its terminal count was hardcoded4. A new frozen
acquisition source must enforce this 8–9s band and the actual selectedN.

“Unused” means no implicated source/speaker in the recorded RevTrace experiment
history. It is not a claim about the ASR/corrector's pretraining corpus.

## V2 correction before any historical census execution

V1 (`99a8b7f59ebe1bed5937d4f4c2b27a9516de350d`) and its 15 passing controls
remain preserved. Root found that the boolean `stream` was later shadowed by
the OBSERVATIONS file handle, making an ordinary disk run try ZIP streaming.
V1 had not run either historical census. V2 uses immutable-purpose boolean
`stream_bundle` and file handle `observations_stream`, without changing census
rules or weakening any gate. The added full ordinary-disk metadata fixture
uses the actual clean frozen source and complete source manifest, not a mock
identity check, and requires normal JSON stdout plus real output files.
