# Context/recovery analysis source v1

Baseline archive4af44aac707ba84119ea13f05f6a9130c869dec4, runtimev7e1511deb6766ce68084128436907b8e2b8e3d417.
This source performs CPU validation of completed real GPU recovery records.
It loads the exact native tokenizer/processor/parser without loading model
weights or executing generation. Recorded Z is used only with its actual job
and input parent. No certificate admission or production transition gate is
invoked as proof of correctness.

For each complete physical batch observed in a Worker receipt, reconstruct
the actual processor inputs from the original audio and jobs in original order;
require exact tensor identities and full same-job P/text/Stop reconstruction.
Keep abandoned work as unobserved, not successful or free. Reconstruct every
durable text binding and directly recount the three recovery clocks from
precrash WAL/accepted frontiers and real Consumer receipts.

Freeze the analysis commit, full source/config/environment and original runtime
manifest before running. Failure retains STOP and completed records; diagnose
it before changing source or starting a new output directory. A CPU mismatch
does not by itself identify a serving violation or a neural model error.

R7/R8/R9 contract comparisons, input/quality causality and fresh holdout
construction will receive their own frozen source revisions and records.
Old FAST_COMMIT, current exact selection and preprocessing/layout differences
remain explicit. No new context mechanism is declared by this audit.

The next source revision prospectively freezes24 previously unrecorded speakers
from the first two content-hashed public LibriSpeech train.100 parquet files,
two chronological same-chapter90s reconstructed sessions each. Whole utterances
retain their order with0.1s separators, and neither ASR outcomes nor reference
quality choose membership. Model-pretraining novelty is not claimed. Each
speaker/chapter is a statistical cluster; two sessions do not double its count.
Original shard identities are verified against the public dataset maintainer's
commit before source audio is accepted. No model runs on this holdout until the
mechanism and evaluation gates are separately frozen.
