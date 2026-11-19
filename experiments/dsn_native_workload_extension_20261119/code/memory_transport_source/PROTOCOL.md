# Optional Windows-memory original-asset transport

One official public trmal URL, exact4MiB HTTP ranges, four threads. Each response
must match HTTP206, complete Content-Range, ETag and exact length; first64KiB hash
is pinned. Data is held in RAM and directly written through an already authorized
SSH client's SFTP channel into its own8TB directory, exclusive per-piece files.
No corpus byte is written to local disk. Credentials remain in the existing
approved connector, outside this source and all records.

Every piece has a locally computed SHA. Remote Python independently reads each
piece and verifies length/SHA. A full run assembles exact ordered coverage into
a new8TB part, fsyncs, computes full SHA and publishes the original archive using
atomic no-clobber hardlink. An existing archive is accepted only if identical.
All partial/pieces stay preserved. No source/data selection, model or GPU change.

First run only4pieces (16MiB) and freeze a minimum end-to-end verified rate before
measurement. Below threshold yields NO-GO and leaves the existing aria transport
untouched. A canary cannot publish an archive. Actual full transport still needs
the original preparer's gzip/tar/header gate before selection/reference/models.
