# Isolated loader observer candidate

Not integrated, frozen or executed. Root may copy into a distinct shared v2
source after the loader contract is accepted. Do not edit baseline v1.

`loader_observer.py` uses only the standard library until a caller passes its
already-imported torch/model. CUDA queries run only after the context exists.
No weights are read or tensors moved for phase metadata. Optional Linux mincore
reads page residency through a private mapping without indexing file bytes.
It never drops caches, evicts pages, resets allocator peaks or signals workers.

Record probe duration and keep matching observation schedules in controlled
fault/no-fault cells. Full tensor hashes, copy profiling with synchronizations,
and optional mincore scans are separate diagnostic/correctness work. Do not put
their costs outside an E2E clock or claim the host observations establish UIR.
