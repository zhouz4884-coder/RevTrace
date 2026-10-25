# Prepared packaging/publication interfaces

Status: scripts prepared and ten synthetic CPU safety tests passed. No real
delivery has been built or pushed by this preparation task. Runtime, controller
and active GPU experiment are untouched.

After the full frozen campaign, collection, independent local event review and
final reports exist:

```text
python make_delivery.py --stage <this-stage> --collected <this-stage>/collected --analysis <this-stage>/local_review --output <this-stage>/delivery
```

The packer fails closed unless all 72 formal + 4 smoke + 2 Oracle audits pass,
the original smoke failure/corrected same-raw record remain, all owned Workers
are released, the independent local event/quality/energy review passes, final
decision/coverage/mathematical documentation exists, both profile fits match,
and all 140 tracked Runtime files equal the frozen e45 commit/manifest bytes.
Historical CPU gates (including early failures) remain individually archived;
their overlapping test counts are not added.

Required final documents: `RESEARCH_REPORT.zh.md`,
`CONTRIBUTION_EVIDENCE_MATRIX.md`, `DECISION.json`, `README.md`,
`IMPLEMENTATION_COVERAGE.md`, `ALGORITHM_EXPLANATION.zh.md`, `PROTOCOL.md`,
`FORMAL_REVIEW_BOUNDARIES.md`, and `AUDIT_V2_CORRECTION.md`.
The decision accepts GO or NO-GO; a positive performance finding is not a
packaging prerequisite. The final independent local summary status is
`PASS_SEPARATE_LOCAL_EVENT_QUALITY_ENERGY_RECOMPUTATION`.

The collector's byte-exact manifest/raw index, bounded compressed event/WAL
payloads, all negative results, source reference text, two fit directories,
historical CPU reviews and exact Runtime source are included. Models/audio,
Git metadata, temporary test trees, SSH transport/credential-routing files and
operations payloads are not copied. Full raw tensor arrays remain on indexed
8 TB paths. Source `.gitattributes` disables newline normalization.

Recognized-secret scanning inspects ordinary files, decoded gzip/tar members,
and reconstructed ordered multipart logical streams. It does not claim to
detect every possible secret. Each published file must remain below 40 MB;
larger logical data retain their indexed parts rather than being silently
dropped. A failed preparation leaves its partial output and requires a new
output directory, not an in-place overwrite.

Local-only verification (no network or Git write):

```text
python publish_closed.py --stage <this-stage> --delivery <this-stage>/delivery
```

Only a later explicit invocation publishes:

```text
python publish_closed.py --stage <this-stage> --delivery <this-stage>/delivery --publish
```

Default Git directory is the existing isolated partial delivery clone at
`experiments/online_admission_20261022/git_delivery_stage_v1`; the dirty root
checkout is never staged/reset. Expected remote base is
`d0529564935b4a045960645d3a00a2740c4bbaf4` and the only allowed new prefix is
`experiments/ces_v5_closed_loop_20261025/`. The publisher verifies the intended
repository, all prior blob identities, exact new raw-byte blob OIDs, fresh
remote ref and parent/tree. It uses normal push, stops if remote advanced, and
never force-pushes. Verification is content-addressed native Git verification,
not a claim that every remote blob was independently downloaded or that an
anonymous mirror refreshed.

An interrupted network publication may use `--publish --resume-push` only for
the exact saved prepared commit. It cannot silently rebase onto a new remote
history or change the artifact. Native credential-manager authentication is
used without printing or persisting credentials; expired authorization fails
instead of opening an unrequested credential flow.
