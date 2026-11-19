# Native lineage audit

V2 adds the explicit distinction between a surviving physical/ready record and
the original job's retention-policy eligibility. V1 remains separately frozen
and its old80 result is preserved. Neither version changes neural execution.

Read CONTRACT.md before interpretation. `lineage.py` compares complete JSON
states and explicit actual Owner event order. `run_lineage.py` verifies source,
campaign/cell/gate identities and raw evidence, executes constructive controls,
and recounts every dispatch. Run only from the clean manifest-matched checkout
with CUDA_VISIBLE_DEVICES empty. Required CLI: `--manifest`, `--config`, `--out`.
The config fixes runtime parser identity, complete campaign plans/summaries,
expected trial count, new-bank pending/completed scope and 8TB output. No
neural imports or model invocations are permitted.

The first configured execution covers old80 only while naming new6*N as
pending. A later complete-bank config is a new experiment record, not a
replacement of old80 results. Positive witnesses contain raw full state and
stay on the 8TB disk; per-cell summaries preserve counts and metadata.
