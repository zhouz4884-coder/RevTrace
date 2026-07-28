# Diagnostic-only Whisper feedback runs

The JSON files in this directory are retained only as protocol-debugging
evidence. Their session builder rotated through source utterances, so nominal
90-second sessions could reuse overlapping audio and were not a valid
independent-session population.

These runs are excluded from every paper-facing Phase 4 result, aggregate, and
artifact manifest. The corrected experiment uses disjoint source audio and is
stored in:

`results/phase4/whisper_feedback_expanded/`

The corrected protocol constructs exactly 100 disjoint 90-second streams per
model and never reuses an audio sample across sessions.
