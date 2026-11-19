# One unchanged official public archive, multiple official mirrors

This CPU-only transport addresses a slow single public HTTP connection. It does
not alter dataset selection, references, models, runtime or manuscript. Before
transport it checks each frozen official mirror's 65,536-byte prefix, HTTP206
range total, ETag and SHA256. It then uses one aria2 input entry with three URIs,
16 total splits and at most six connections per host. No login or access control
is bypassed. HTTP headers are restricted to public identity fields.
The input entry includes its own indented dir/out options. Before real transport,
smoke_aria2.py exercises the installed aria2 binary against a tiny localhost-only
synthetic HTTP fixture and verifies exit0, exact bytes and the different part name.

The independent source and config are frozen before launch. Existing complete
assets are never overwritten. The prior single-connection partial is untouched.
The distinct test_set.tar.gz.multi.part and its aria2 state/log survive errors.
Progress parses aria2's human-readable=false exact-byte completed/speed lines,
never allocated file size. RPC is disabled so the process exits on completion.

Only aria2 exit0 plus exact final byte size and full SHA256 authorizes atomic
same-disk no-clobber hard-link publication. The part remains preserved. This is
transport evidence only: the original CPU preparer must still validate full
gzip/tar integrity and all original WAV headers before metadata-only selection.
No model/GPU call is made here.

Required CLI: transport.py --config CONFIG --manifest MANIFEST --out NEW_OUT
with CUDA_VISIBLE_DEVICES empty. Config keys: experiment_id, source_commit,
source_manifest_sha256, experiment_disk, archive_path, archive_bytes, urls,
ETag, prefix_sha256, aria2_path. Every run records CONFIG/ENVIRONMENT/RUN_RECORD,
per-mirror probe, command, owned aria2 generation, progress, final summary/gate.
