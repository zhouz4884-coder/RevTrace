# RevTrace: public scalar evidence for the original MAGICDATA68 workload

This is a derived public evidence packet for the completed 24-trial extension.
It contains no original audio, official transcripts, human references, model
output text, token sequences, complete states/cuts or encoded waveform buffers.
The complete private originals remain unchanged on the designated8TB experiment
disk and private local mirror. A `.json` extension is never treated as proof that
a private file is safe to publish.

Start with [the public research report](REPORT_PUBLIC.zh.md),
[the executed-plan descriptor](protocol/EXECUTED_PLAN_PUBLIC_DESCRIPTOR.json),
[the 718 scalar derivative](public_scalars/FINAL_718_PUBLIC.json), and
[the 24-cell index](public_scalars/CELLS_INDEX_PUBLIC.json).
Every derivative identifies its private original by size and SHA256. Public
descriptors are labelled `DERIVED_PUBLIC_NOT_EXECUTED_CONFIG`; they are not the
actual execution configurations. Their original configuration SHA values remain
available for binding. The report is a public derivative of the local report,
with its original SHA and replacement links; the original report is unchanged.

## Recompute from this public packet

```
python -B rebuild_public_scalars.py
```

This reads only files below this directory. It recomputes every original offered
D/C endpoint from the ordered actual Consumer frontier rows; the all-offered
credit and quantile tests; per-job worker sums and job-partition conservation;
two-board energy sums; actual high-water gaps; support-classified window union
geometry; and D2 reads of previously credited original intervals. Its independent
result is compared with the already extracted 718 aggregate, without modifying
the expected values. `PUBLIC_REBUILD_RESULT.json` records the input SHA values.

The public quality counts permit checking CER arithmetic and pooling. Computing
edit distances or rechecking full-state support/refinement requires the private
licensed text/state originals, or a new execution reconstructed from the public
code and official data. The public projection preserves the checked support
classification, state fingerprints and event clocks, without distributing the
states behind those fingerprints. The published three-condition extension does
not estimate a complete R×S interaction.

## Reconstruct the private workload using original official data

1. Obtain the unchanged official MAGICDATA68 `metadata.tar.gz` and test archive
   from [OpenSLR68](https://www.openslr.org/68/). Archive SHA256 is
   `dbd69d0cac4023341ca38a9251aec7983c3837b8e0a488b36b686726bb3c377f`.
   The code in `code/prep_source/` validates the complete gzip/tar and all24,279
   original WAV headers. Its frozen metadata-only rule picks the first four
   eligible speakers lexicographically, nearest16s then source ID, within12–20s,
   mono16kHz PCM16. It writes IDs before selected official labels. WAV bytes are
   copied unchanged on the experiment disk; no trim, concatenation or resampling.
2. Reconstruct the selection receipt privately; the public descriptor provides
   source IDs, original frames, WAV/PCM hashes and the original config SHA.
   The official text is obtained from the original release, not this repository.
3. Import the complete source-only Git bundles from `source_bundles/`, and the
   exact already-public dependencies in [DEPENDENCIES.json](DEPENDENCIES.json).
   Source manifests identify actual execution commits separately from the GitHub
   evidence-archive commit. `code/driver_source/` contains the reference and
   workload-plan builders, strict corpus validator and campaign controller.
   Use the original model sources/assets identified by the readiness code and
   existing dependency package; weights and environments are not distributed.
   The fixed warmup uses unchanged AISHELL source BAC009S0764W0209 (129088
   frames, WAV SHA in the plan descriptor). Reconstruct its original prefix to
   frame24000 before the declared24000→32000 warmup step; its complete state is
   intentionally not distributed. Obtain that original asset from the existing
   official AISHELL/StreamCorrect setup identified by the dependency code.
4. Freeze a machine-specific environment and config, build original continuous
   and restored-input references, then run the three policies with the declared
   seeded/reversed order, two fresh repeats, unchanged500ms cadence and D2/C8.
   Keep all planned outcomes. Re-running wall-clock experiments creates new
   measurements; it does not recreate the historical event schedule bytewise.

`code/analysis_source/` is the full private-input718 recount source. The additional
`code/independent_review/` script is the second private-input interpretation,
separate from the public-only reconstruction above. Neither silently substitutes
public projections for complete private states. Source-only history bundles were
independently unpacked and scanned in memory before publication.

## Exact publication boundary

[EXCLUDED_PRIVATE_INPUTS.json](EXCLUDED_PRIVATE_INPUTS.json) lists categories and
SHA identities of omitted inputs, including full reference details/genesis,
complete execution configs and raw Consumer records. It is not a download list.
The public packet contains explicitly extracted numeric/event projections,
source code, source manifests/bundles and protocol descriptors. It contains no
PDF, manuscript, model, environment/cache, WAV, official TRANS, human reference,
recognition text, token IDs, audio sample array, complete cut/state or raw WAL.
No private original has been deleted or rewritten.

`PUBLICATION_MANIFEST.json` inventories candidate bytes. The independent privacy
review and public-only recomputation are separate checks; source-code references
to fields such as `audio_buffer` describe how private data is processed and do
not distribute those payloads.
